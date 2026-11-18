COMPUTE_RIGHTSIZING_PROMPT = """
Analyze the following compute resource (Virtual Machine / EC2 / Compute Engine) and Rule Engine finding to produce an optimal rightsizing recommendation.

### RESOURCE CONTEXT:
- Resource ID: {resource_id}
- Resource Name: {resource_name}
- Provider: {provider}
- Current Instance Type: {current_sku}
- Current Monthly Cost: ${monthly_cost:.2f}
- Telemetry (30-day window):
  * Average CPU: {cpu_avg:.1f}%
  * Peak CPU: {cpu_peak:.1f}%
  * Average Memory: {memory_avg:.1f}%
  * Peak Memory: {memory_peak:.1f}%
  * Network I/O: {network_mbps:.2f} Mbps
- Environment / Tags: {tags}

### RULE ENGINE FINDING:
- Rule Triggered: {rule_id}
- Finding Description: {finding_title}
- Violation Evidence: {evidence}
- Baseline Formula Savings: ${baseline_savings:.2f}/month

### REQUIREMENTS:
1. Select a safe target instance type (e.g. if m5.2xlarge is low utilized, consider m5.xlarge or modern generation m6i.xlarge).
2. Calculate estimated monthly savings (typically 30% - 50% for one size down).
3. Specify risk level (LOW if staging/dev or high headroom, MEDIUM/HIGH if production).
4. Provide the exact cloud CLI command to execute the resize.

### JSON OUTPUT SCHEMA:
{{
  "action": "RIGHTSIZE",
  "target_sku": "<target instance type>",
  "estimated_monthly_savings": <float>,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "justification": "<2-3 sentence technical justification referencing CPU and RAM metrics>",
  "remediation_steps": [
    "<step 1>",
    "<step 2>",
    "<step 3>"
  ],
  "remediation_command": "<exact CLI command, e.g. aws ec2 modify-instance-attribute...>"
}}
"""

