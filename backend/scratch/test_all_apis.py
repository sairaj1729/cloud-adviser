import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8000"

def request(method, path, data=None, token=None, is_form=False):
    url = f"{BASE_URL}{path}"
    headers = {}
    body = None
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    if is_form and data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(data).encode("utf-8")
    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                res_json = json.loads(content)
            except Exception:
                res_json = content
            return status, res_json
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            res_json = json.loads(content)
        except Exception:
            res_json = content
        return e.code, res_json
    except Exception as e:
        return 500, {"error": str(e)}

def run_tests():
    print("==================================================")
    print("       STARTING COMPREHENSIVE SWAGGER API AUDIT   ")
    print("==================================================")
    results = []

    def record(name, method, path, status, ok, detail=""):
        res = "PASS" if ok else "FAIL"
        results.append((name, method, path, status, ok, detail))
        print(f"[{res}] {method:6} {path:35} -> HTTP {status} | {detail}")

    # 1. Root & Health
    status, res = request("GET", "/")
    record("Root endpoint", "GET", "/", status, status == 200, res.get("message", ""))

    # 2. Auth: Register
    import uuid
    rand_suffix = uuid.uuid4().hex[:6]
    test_email = f"user_{rand_suffix}@cloudadvisor.io"
    status, res = request("POST", "/api/auth/register", {
        "email": test_email,
        "password": "Password123!",
        "name": f"Test User {rand_suffix}"
    })
    record("Auth Register", "POST", "/api/auth/register", status, status == 201, f"Token obtained for {test_email}")

    # 3. Auth: Login (using registered user)
    status, res = request("POST", "/api/auth/login", {
        "username": test_email,
        "password": "Password123!"
    }, is_form=True)
    temp_token = res.get("access_token") if status == 200 else None
    record("Auth Login (New User)", "POST", "/api/auth/login", status, status == 200 and temp_token is not None, "Login successful")

    # 4. Auth: Login with Seeded Jordan User
    status, res = request("POST", "/api/auth/login", {
        "username": "jordan@acme.io",
        "password": "password123"
    }, is_form=True)
    token = res.get("access_token") if status == 200 else None
    record("Auth Login (Jordan)", "POST", "/api/auth/login", status, status == 200 and token is not None, "Jordan token obtained")

    if not token:
        print("FATAL: Could not log in as jordan@acme.io, cannot continue protected endpoint tests!")
        return

    # 5. Auth: Get Me
    status, res = request("GET", "/api/auth/me", token=token)
    record("Auth Me", "GET", "/api/auth/me", status, status == 200, f"Logged in as: {res.get('email')}")

    # 6. Accounts: Initiate AWS Connection
    status, res = request("POST", "/api/accounts/aws/initiate", token=token)
    ext_id = res.get("external_id") if status == 200 else None
    conn_id = res.get("connection_id") if status == 200 else None
    record("AWS Initiate", "POST", "/api/accounts/aws/initiate", status, status == 200 and ext_id is not None, f"External ID: {ext_id}")

    # 7. Accounts: Verify AWS Connection
    if ext_id:
        status, res = request("POST", "/api/accounts/aws/verify", data={
            "connection_id": conn_id,
            "display_name": f"Audit AWS {rand_suffix}",
            "account_id": "123456789012",
            "role_arn": "arn:aws:iam::123456789012:role/CloudAdvisorReadOnlyRole",
            "external_id": ext_id,
            "region": "ap-south-1"
        }, token=token)
        record("AWS Verify STS", "POST", "/api/accounts/aws/verify", status, status == 200 and res.get("verified") is True, f"Verified: {res.get('verified')}")

    # 8. Accounts: List Accounts
    status, res = request("GET", "/api/accounts", token=token)
    accounts = res if isinstance(res, list) else []
    record("Accounts List", "GET", "/api/accounts", status, status == 200, f"{len(accounts)} accounts returned")

    test_account_id = accounts[0]["id"] if accounts else None

    # 9. Accounts: Create Manual Account
    new_acc_payload = {
        "provider": "azure",
        "display_name": f"Audit Azure Sub {rand_suffix}",
        "account_identifier": "00000000-0000-0000-0000-000000000001",
        "region": "eastus",
        "credential_type": "client_secret",
        "azure_tenant_id": "00000000-0000-0000-0000-000000000002",
        "azure_client_id": "00000000-0000-0000-0000-000000000003",
        "azure_client_secret": "test_secret_value_123"
    }
    status, res = request("POST", "/api/accounts", data=new_acc_payload, token=token)
    created_acc_id = res.get("id") if status == 201 else None
    record("Accounts Create", "POST", "/api/accounts", status, status == 201, f"Created account ID: {created_acc_id}")

    # 10. Accounts: Detail
    target_acc_id = created_acc_id or test_account_id
    if target_acc_id:
        status, res = request("GET", f"/api/accounts/{target_acc_id}", token=token)
        record("Accounts Detail", "GET", f"/api/accounts/{{id}}", status, status == 200, f"Account: {res.get('display_name')}")

    # 11. Accounts: Delete Account (Clean up the created one)
    if created_acc_id:
        status, res = request("DELETE", f"/api/accounts/{created_acc_id}", token=token)
        record("Accounts Delete", "DELETE", f"/api/accounts/{{id}}", status, status == 204, "Deleted created test account")

    # 12. Resources: List Resources (all)
    status, res = request("GET", "/api/resources", token=token)
    res_count = len(res) if isinstance(res, list) else 0
    record("Resources List", "GET", "/api/resources", status, status == 200, f"{res_count} resources returned")

    # 13. Resources: List with Provider Filter
    status, res = request("GET", "/api/resources?provider=aws", token=token)
    aws_res_count = len(res) if isinstance(res, list) else 0
    record("Resources Filtered (AWS)", "GET", "/api/resources?provider=aws", status, status == 200, f"{aws_res_count} AWS resources")

    # 14. Rules: List Rules
    status, res = request("GET", "/api/rules", token=token)
    rules_list = res if isinstance(res, list) else []
    record("Rules List", "GET", "/api/rules", status, status == 200, f"{len(rules_list)} rules in registry")

    # 15. Rules: Get Rule by ID
    sample_rule_id = rules_list[0]["rule_id"] if rules_list else "AWS-EC2-001"
    status, res = request("GET", f"/api/rules/{sample_rule_id}", token=token)
    record("Rules Detail", "GET", f"/api/rules/{{rule_id}}", status, status == 200, f"Rule: {res.get('name')}")

    # 16. Findings: Generate Findings via Rule Engine
    status, res = request("POST", "/api/findings/generate", token=token)
    record("Findings Generate", "POST", "/api/findings/generate", status, status == 200, f"Findings stored: {res.get('findings_stored', 0)}, Savings: ${res.get('estimated_monthly_savings', 0)}/mo")

    # 17. Findings: List Findings
    status, res = request("GET", "/api/findings", token=token)
    findings_list = res if isinstance(res, list) else []
    record("Findings List", "GET", "/api/findings", status, status == 200, f"{len(findings_list)} findings returned")

    # 18. Findings: Detail
    sample_finding_id = findings_list[0]["id"] if findings_list else None
    if sample_finding_id:
        status, res = request("GET", f"/api/findings/{sample_finding_id}", token=token)
        record("Findings Detail", "GET", f"/api/findings/{{id}}", status, status == 200, f"Finding for: {res.get('resource_name')}")

        # 19. Findings: Patch Status
        status, res = request("PATCH", f"/api/findings/{sample_finding_id}", data={
            "status": "snoozed",
            "notes": "Audited in automated swagger test"
        }, token=token)
        record("Findings Status Patch", "PATCH", f"/api/findings/{{id}}", status, status == 200, f"Updated status: {res.get('status')}")

    # 20. Dashboard: Analytics
    status, res = request("GET", "/api/dashboard/analytics?refresh=false", token=token)
    recs_count = len(res.get("recommendations", [])) if isinstance(res, dict) else 0
    record("Dashboard Analytics", "GET", "/api/dashboard/analytics", status, status == 200, f"{recs_count} recommendations")

    # 21. Dashboard: Refresh
    status, res = request("POST", "/api/dashboard/refresh", token=token)
    record("Dashboard Refresh", "POST", "/api/dashboard/refresh", status, status == 200, "Refreshed analytics successfully")

    # 22. Dashboard: Summary
    status, res = request("GET", "/api/dashboard/summary", token=token)
    record("Dashboard Summary", "GET", "/api/dashboard/summary", status, status == 200, f"Total Accounts: {res.get('total_cloud_accounts')}, Total Cost: ${res.get('total_monthly_cost')}")

    print("\n==================================================")
    pass_count = sum(1 for r in results if r[4])
    fail_count = sum(1 for r in results if not r[4])
    print(f"AUDIT SUMMARY: {pass_count} PASSED, {fail_count} FAILED out of {len(results)} tests.")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
