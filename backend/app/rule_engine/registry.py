import json
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RULES_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "rules.json")
)

def load_rules_from_file() -> List[Dict[str, Any]]:
    """Loads rules from backend/rules.json if it exists."""
    if os.path.exists(RULES_FILE_PATH):
        try:
            with open(RULES_FILE_PATH, "r", encoding="utf-8") as f:
                rules = json.load(f)
                logger.info(f"Loaded {len(rules)} rules from {RULES_FILE_PATH}")
                return rules
        except Exception as e:
            logger.error(f"Error reading rules.json from {RULES_FILE_PATH}: {e}")
    return DEFAULT_RULES

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "AWS-EC2-001",
        "name": "Underutilized AWS EC2 Instance",
        "description": "Identify EC2 instances with low average CPU utilization over 14 days, with sufficient historical observations.",
        "provider": "aws",
        "resource_type": "compute_instance",
        "required_data": [
            "metrics.cpu_average_14d_pct",
            "metrics.cpu_observation_count_14d"
        ],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average_14d_pct", "operator": "lt", "threshold": 20},
                {"field": "metrics.cpu_observation_count_14d", "operator": "gte", "threshold": 303}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Review instance utilization and consider downsizing the instance if its workload requirements allow."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AZURE-VM-001",
        "name": "Underutilized Azure Virtual Machine",
        "description": "Identify Azure virtual machines with low average CPU utilization over 14 days and sufficient historical observations.",
        "provider": "azure",
        "resource_type": "compute_instance",
        "required_data": [
            "metrics.cpu_average_14d_pct",
            "metrics.cpu_observation_count_14d"
        ],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average_14d_pct", "operator": "lt", "threshold": 15},
                {"field": "metrics.cpu_observation_count_14d", "operator": "gte", "threshold": 303}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Review VM utilization and consider resizing to a smaller suitable VM SKU."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "GCP-GCE-001",
        "name": "Underutilized GCP Compute Engine Instance",
        "description": "Identify Compute Engine instances with low average CPU utilization over 14 days and sufficient historical observations.",
        "provider": "gcp",
        "resource_type": "compute_instance",
        "required_data": [
            "metrics.cpu_average_14d_pct",
            "metrics.cpu_observation_count_14d"
        ],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average_14d_pct", "operator": "lt", "threshold": 10},
                {"field": "metrics.cpu_observation_count_14d", "operator": "gte", "threshold": 303}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Review instance utilization and consider selecting a smaller suitable machine type."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AWS-EC2-002",
        "name": "High CPU Utilization on AWS EC2",
        "description": "Identify EC2 instances with sustained high average CPU utilization and a high 95th-percentile CPU utilization over 14 days.",
        "provider": "aws",
        "resource_type": "compute_instance",
        "required_data": [
            "metrics.cpu_average_14d_pct",
            "metrics.cpu_p95_14d_pct",
            "metrics.cpu_observation_count_14d"
        ],
        "lookback_window": {"value": 14, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average_14d_pct", "operator": "gte", "threshold": 70},
                {"field": "metrics.cpu_p95_14d_pct", "operator": "gte", "threshold": 85},
                {"field": "metrics.cpu_observation_count_14d", "operator": "gte", "threshold": 303}
            ]
        },
        "recommendation": {
            "type": "RIGHTSIZING_REVIEW",
            "action_template": "Investigate workload pressure and consider resizing or scaling the instance to meet demand."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "high",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AZURE-DISK-001",
        "name": "Unattached Azure Managed Disk",
        "description": "Identify Azure managed disks that have remained unattached for at least 30 days.",
        "provider": "azure",
        "resource_type": "storage_volume",
        "required_data": [
            "configuration.state",
            "configuration.unattached_days"
        ],
        "lookback_window": {"value": 30, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "configuration.state", "operator": "eq", "threshold": "unattached"},
                {"field": "configuration.unattached_days", "operator": "gte", "threshold": 30}
            ]
        },
        "recommendation": {
            "type": "CLEANUP_REVIEW",
            "action_template": "Verify that the disk is no longer needed, then consider deleting it after confirming backup and retention requirements."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AZURE-DISK-002",
        "name": "Low-I/O Attached Azure Managed Disk",
        "description": "Identify attached Azure managed disks with low read and write operation counts over 30 days, provided the full observation period is available.",
        "provider": "azure",
        "resource_type": "storage_volume",
        "required_data": [
            "configuration.state",
            "metrics.storage_read_ops_30d",
            "metrics.storage_write_ops_30d",
            "metrics.storage_io_days_observed_30d"
        ],
        "lookback_window": {"value": 30, "unit": "days"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "configuration.state", "operator": "eq", "threshold": "attached"},
                {"field": "metrics.storage_read_ops_30d", "operator": "lte", "threshold": 100},
                {"field": "metrics.storage_write_ops_30d", "operator": "lte", "threshold": 100},
                {"field": "metrics.storage_io_days_observed_30d", "operator": "gte", "threshold": 30}
            ]
        },
        "recommendation": {
            "type": "CLEANUP_REVIEW",
            "action_template": "Verify whether the disk is required by the workload and consider a lower-cost storage configuration if appropriate."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "low",
        "status": "active",
        "provenance": "DERIVED"
    },
    {
        "rule_id": "AWS-EC2-003",
        "name": "High Monthly Cost AWS EC2 Instance",
        "description": "Flag EC2 instances whose verified monthly cost exceeds 500 USD for cost optimization review.",
        "provider": "aws",
        "resource_type": "compute_instance",
        "required_data": [
            "cost.monthly",
            "cost.currency",
            "cost.period",
            "cost.verified"
        ],
        "lookback_window": {"value": 1, "unit": "months"},
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "cost.monthly", "operator": "gt", "threshold": 500},
                {"field": "cost.currency", "operator": "eq", "threshold": "USD"},
                {"field": "cost.period", "operator": "eq", "threshold": "month"},
                {"field": "cost.verified", "operator": "eq", "threshold": True}
            ]
        },
        "recommendation": {
            "type": "COST_REVIEW",
            "action_template": "Review the instance's cost, utilization, and workload requirements to identify possible optimization opportunities."
        },
        "savings_calculation": {"type": "UNAVAILABLE", "percentage": None},
        "severity": "medium",
        "status": "active",
        "provenance": "DERIVED"
    }
]

class RuleRegistry:

    @staticmethod
    async def seed_rules(db, replace_existing: bool = True):
        """
        Clears old rules and loads new rules defined in backend/rules.json into MongoDB.
        """
        rules_to_seed = load_rules_from_file()

        if replace_existing:
            # Remove old rules
            deleted = await db.rules.delete_many({})
            logger.info(f"Removed {deleted.deleted_count} old rules from MongoDB 'rules' collection.")

        for rule in rules_to_seed:
            await db.rules.update_one(
                {"rule_id": rule["rule_id"]},
                {"$set": rule},
                upsert=True
            )

        seeded_ids = [r["rule_id"] for r in rules_to_seed]
        logger.info(f"Successfully seeded {len(seeded_ids)} rules into MongoDB: {seeded_ids}")
