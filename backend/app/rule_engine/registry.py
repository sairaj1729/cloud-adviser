from typing import List, Dict, Any

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "AWS-EC2-001",
        "name": "Underutilized EC2 Instance",
        "description": "EC2 instance average CPU utilization is below 20% over 14 days.",
        "provider": "aws",
        "resource_type": "compute_instance",
        "required_data": ["metrics.cpu_average", "cost.monthly"],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 20.0}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Downsize EC2 instance to a smaller SKU or enable autoscaling."
        },
        "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 50.0},
        "severity": "high",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AWS-EC2-002",
        "name": "Idle EC2 Instance",
        "description": "EC2 instance has minimal or zero cost / near zero CPU activity.",
        "provider": "aws",
        "resource_type": "compute_instance",
        "required_data": ["metrics.cpu_average"],
        "lookback_window": {"value": 30, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 5.0}
            ]
        },
        "recommendation": {
            "type": "STOP_INSTANCE",
            "action_template": "Stop or terminate instance after confirming ownership."
        },
        "savings_calculation": {"type": "ZERO_UTILIZATION"},
        "severity": "high",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AZURE-VM-001",
        "name": "Underutilized Azure Virtual Machine",
        "description": "Azure VM CPU utilization is below 15% over 14 days.",
        "provider": "azure",
        "resource_type": "compute_instance",
        "required_data": ["metrics.cpu_average"],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 15.0}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Resize Azure Virtual Machine to a lower SKU."
        },
        "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 45.0},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "GCP-GCE-001",
        "name": "Underutilized Compute Engine Instance",
        "description": "GCP Compute Engine instance average CPU is below 10%.",
        "provider": "gcp",
        "resource_type": "compute_instance",
        "required_data": ["metrics.cpu_average"],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 10.0}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Adjust machine type to smaller SKU."
        },
        "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 40.0},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    }
]

class RuleRegistry:

    @staticmethod
    async def seed_rules(db):
        """Seed default rules into MongoDB if empty."""
        existing_count = await db.rules.count_documents({})
        if existing_count == 0:
            for rule in DEFAULT_RULES:
                await db.rules.update_one(
                    {"rule_id": rule["rule_id"]},
                    {"$set": rule},
                    upsert=True
                )
