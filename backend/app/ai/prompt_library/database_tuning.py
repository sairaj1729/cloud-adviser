DATABASE_TUNING_PROMPT = """
Analyze the following managed database instance (RDS / Azure SQL / Cloud SQL) and Rule Engine finding to recommend database rightsizing or tier optimization.

### RESOURCE CONTEXT:
- Database ID: {resource_id}
- Database Name: {resource_name}
- Provider: {provider}
- Database Engine: {db_engine}
- Current Instance Class: {current_sku}
- Current Monthly Cost: ${monthly_cost:.2f}
- Telemetry:
  * Average CPU: {cpu_avg:.1f}%
  * Peak CPU: {cpu_peak:.1f}%
  * Average Memory: {memory_avg:.1f}%
  * Active Connections: {active_connections}
- Environment / Tags: {tags}

### RULE ENGINE FINDING:
- Rule Triggered: {rule_id}
- Finding Description: {finding_title}
- Violation Evidence: {evidence}
- Baseline Formula Savings: ${baseline_savings:.2f}/month

### REQUIREMENTS:
1. Recommend rightsizing to a smaller database tier while preserving memory needed for query caches.
2. If in Production, flag risk as MEDIUM and recommend scheduling during a maintenance window.
3. Provide the exact CLI command to modify instance class.

### JSON OUTPUT SCHEMA:
{{
  "action": "RIGHTSIZE",
  "target_sku": "<target db instance class, e.g. db.r6g.xlarge or db.m5.large>",
  "estimated_monthly_savings": <float>,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "justification": "<technical reason balancing CPU, memory cache, and connection pools>",
  "remediation_steps": [
    "<step 1: schedule maintenance window for brief failover>",
    "<step 2: modify db instance class>",
    "<step 3: verify application health and query latency>"
  ],
  "remediation_command": "<exact CLI command to modify db instance>"
}}
"""

