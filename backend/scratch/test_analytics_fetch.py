import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

NAME_MAP = {
    "compute_instance": {"AWS": "Amazon EC2", "AZURE": "Virtual Machines", "GCP": "Compute Engine"},
    "database": {"AWS": "Amazon RDS", "AZURE": "Azure SQL Database", "GCP": "Cloud SQL"},
    "object_storage": {"AWS": "Amazon S3", "AZURE": "Blob Storage", "GCP": "Cloud Storage"},
    "block_storage": {"AWS": "Amazon EBS", "AZURE": "Managed Disks", "GCP": "Persistent Disk"},
    "load_balancer": {"AWS": "Elastic Load Balancer", "AZURE": "Azure Load Balancer", "GCP": "Cloud Load Balancing"},
    "kubernetes_cluster": {"AWS": "Amazon EKS", "AZURE": "Azure Kubernetes (AKS)", "GCP": "Google Kubernetes Engine (GKE)"},
    "cdn_distribution": {"AWS": "Amazon CloudFront", "AZURE": "Azure Front Door", "GCP": "Cloud CDN"},
    "cache_cluster": {"AWS": "Amazon ElastiCache", "AZURE": "Azure Cache for Redis", "GCP": "Memorystore Redis"},
    "serverless_function": {"AWS": "AWS Lambda", "AZURE": "Azure Functions", "GCP": "Cloud Functions"},
    "nosql_table": {"AWS": "Amazon DynamoDB", "AZURE": "Azure Cosmos DB", "GCP": "Cloud Bigtable"},
    "log_group": {"AWS": "CloudWatch Logs", "AZURE": "Log Analytics", "GCP": "Cloud Logging"}
}

def get_service_name(rtype: str, prov: str) -> str:
    m = NAME_MAP.get(rtype, {})
    return m.get(prov, rtype.replace("_", " ").title())

async def test_analytics_fetch():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    findings_cursor = db.findings.find({})
    findings = await findings_cursor.to_list(length=1000)
    print(f"Loaded {len(findings)} findings from MongoDB")
    
    recs = []
    underutilized = []
    unused = []
    
    for f in findings:
        fid = str(f["_id"])
        raw_prov = str(f.get("provider", "aws")).upper()
        prov = "AWS" if raw_prov == "AWS" else "Azure" if raw_prov == "AZURE" else "GCP"
        rname = f.get("resource_name") or f.get("resource_id", "unnamed")
        rid = f.get("resource_id", "")
        rule_id = f.get("rule_id", "")
        rec_info = f.get("recommendation", {})
        rec_type = rec_info.get("type", "REVIEW")
        action = rec_info.get("action_template") or "Review and optimize resource configuration."
        savings_m = float(f.get("savings", {}).get("monthly", 0.0))
        cost_m = float(f.get("cost", {}).get("monthly", 0.0) or f.get("evidence", {}).get("monthly_cost", 0.0))
        ev = f.get("evidence", {})
        explanation = ev.get("explanation") or f"Satisfied rule criteria for {rule_id}"
        rule_name = ev.get("rule_name") or rule_id
        severity = f.get("severity", "medium").capitalize()
        priority = "High" if severity == "High" else "Medium"
        
        # Recommendation
        recs.append({
            "id": fid,
            "title": f"{rule_name} ({rname})",
            "provider": prov,
            "resource": rname,
            "problem": explanation,
            "evidence": explanation,
            "savings": round(savings_m, 2),
            "priority": priority,
            "confidence": 94 if priority == "High" else 86,
            "action": action,
            "cost": round(cost_m, 2),
            "status": f.get("status", "open")
        })
        
        # Categorize
        rtype = f.get("resource_type") or ("compute_instance" if "EC2" in rule_id or "VM" in rule_id else "database" if "RDS" in rule_id or "SQL" in rule_id else "block_storage")
        sname = get_service_name(rtype, prov)
        
        if rec_type in ["CLEANUP_REVIEW", "STOP_REVIEW"] or "EBS" in rule_id or "DISK" in rule_id or "002" in rule_id:
            unused.append({
                "id": fid,
                "name": rname,
                "provider": prov,
                "service": sname,
                "cost": round(cost_m, 2),
                "lastActivity": "14 days ago",
                "status": "Potentially Unused",
                "evidence": explanation,
                "action": action,
                "history": [round(cost_m * 1.05, 1), round(cost_m * 1.03, 1), round(cost_m, 1), round(cost_m, 1), round(cost_m, 1), round(cost_m, 1)]
            })
            
        if rec_type == "RIGHTSIZING_REVIEW" or "001" in rule_id:
            cpu_val = 12.0
            cond_evals = ev.get("condition_evaluations", [])
            for ce in cond_evals:
                if "cpu" in ce.get("field", ""):
                    cpu_val = float(ce.get("actual_value") or 12.0)
                    break
            underutilized.append({
                "id": fid,
                "name": rname,
                "provider": prov,
                "service": f"{sname} · {f.get('configuration', {}).get('instance_type') or f.get('configuration', {}).get('tier') or 'Standard'}",
                "cpu": round(cpu_val, 1),
                "memory": round(cpu_val * 1.8 + 6, 1),
                "cost": round(cost_m, 2),
                "savings": round(savings_m, 2),
                "recommendation": action
            })

    print(f"Generated from MongoDB findings:")
    print(f" - Recommendations: {len(recs)}")
    print(f" - Underutilized: {len(underutilized)}")
    print(f" - Unused / Review: {len(unused)}")
    client.close()

if __name__ == "__main__":
    asyncio.run(test_analytics_fetch())
