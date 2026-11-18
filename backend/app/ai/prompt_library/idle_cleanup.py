IDLE_CLEANUP_PROMPT = """
Analyze the following idle or orphaned cloud resource and Rule Engine finding to produce a safe decommission recommendation.

### RESOURCE CONTEXT:
- Resource ID: {resource_id}
- Resource Name: {resource_name}
- Provider: {provider}
- Resource Type: {resource_type}
- Current Configuration: {current_sku}
- Current Monthly Cost: ${monthly_cost:.2f}
- Telemetry:
  * Average CPU: {cpu_avg:.1f}%
  * Disk / Network Activity: {network_mbps:.2f}
- Environment / Tags: {tags}

### RULE ENGINE FINDING:
- Rule Triggered: {rule_id}
- Finding Description: {finding_title}
- Violation Evidence: {evidence}
- Baseline Formula Savings: ${baseline_savings:.2f}/month

### REQUIREMENTS:
1. Determine if the action should be "STOP" (for idle VMs that may be needed later) or "TERMINATE" (for orphaned disks/snapshots).
2. Savings for idle resources equals up to 100% of current monthly compute/storage cost.
3. Recommend taking a snapshot backup prior to termination as a safety step.

### JSON OUTPUT SCHEMA:
{{
  "action": "STOP" | "TERMINATE",
  "target_sku": null,
  "estimated_monthly_savings": <float>,
  "risk_level": "LOW" | "MEDIUM",
  "justification": "<concise justification explaining zero usage evidence and savings>",
  "remediation_steps": [
    "<step 1: verify non-production usage>",
    "<step 2: take snapshot backup>",
    "<step 3: stop or terminate resource>"
  ],
  "remediation_command": "<exact CLI command to stop/delete the resource>"
}}
"""

