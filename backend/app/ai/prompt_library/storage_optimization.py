STORAGE_OPTIMIZATION_PROMPT = """
Analyze the following block/managed storage volume with low IOPS or throughput to recommend storage tier optimization.

### RESOURCE CONTEXT:
- Volume ID: {resource_id}
- Volume Name: {resource_name}
- Provider: {provider}
- Current Storage Type: {current_sku}
- Size (GB): {storage_gb}
- Current Monthly Cost: ${monthly_cost:.2f}
- Telemetry:
  * Read IOPS: {read_iops}
  * Write IOPS: {write_iops}
  * Total IOPS: {total_iops}
- Environment / Tags: {tags}

### RULE ENGINE FINDING:
- Rule Triggered: {rule_id}
- Finding Description: {finding_title}
- Violation Evidence: {evidence}
- Baseline Formula Savings: ${baseline_savings:.2f}/month

### REQUIREMENTS:
1. Recommend migration from high-cost provisioned IOPS (e.g. io1/io2, Premium SSD) to cost-effective standard tiers (e.g. gp3, Standard SSD) which easily satisfy the observed IOPS.
2. Estimated savings typically 20% to 40% on storage costs.
3. Provide the exact volume modification command.

### JSON OUTPUT SCHEMA:
{{
  "action": "STORAGE_DOWNGRADE",
  "target_sku": "<target storage tier, e.g. gp3 or StandardSSD_LRS>",
  "estimated_monthly_savings": <float>,
  "risk_level": "LOW",
  "justification": "<explanation comparing observed IOPS vs provisioned tier capability>",
  "remediation_steps": [
    "<step 1: verify peak IOPS does not exceed target tier>",
    "<step 2: execute online volume tier modification without downtime>"
  ],
  "remediation_command": "<exact CLI command to modify storage tier>"
}}
"""

