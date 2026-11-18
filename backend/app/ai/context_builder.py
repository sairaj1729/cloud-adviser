import logging
from typing import Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.prompt_library.compute_rightsizing import COMPUTE_RIGHTSIZING_PROMPT
from app.ai.prompt_library.idle_cleanup import IDLE_CLEANUP_PROMPT
from app.ai.prompt_library.storage_optimization import STORAGE_OPTIMIZATION_PROMPT
from app.ai.prompt_library.database_tuning import DATABASE_TUNING_PROMPT

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    Extracts raw resource documents and Rule Engine findings directly from MongoDB
    and hydrates the appropriate prompt from the Prompt Library.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def build_context(self, resource_id: str, finding_id: str = None) -> Tuple[str, Dict[str, Any]]:
        # 1. Fetch Resource from MongoDB
        resource = await self.db.resources.find_one({"resource_id": resource_id})
        if not resource:
            # Fallback check on string ID match
            resource = await self.db.resources.find_one({"id": resource_id})
            if not resource:
                raise ValueError(f"Resource '{resource_id}' not found in MongoDB.")

        # 2. Fetch Finding from MongoDB (if exists)
        finding = None
        if finding_id:
            finding = await self.db.findings.find_one({"id": finding_id})
        if not finding:
            finding = await self.db.findings.find_one({"resource_id": resource_id})

        # Safe defaults if no prior finding existed
        if not finding:
            finding = {
                "rule_id": "MANUAL-REVIEW-001",
                "finding_type": "RIGHTSIZING_REVIEW",
                "severity": "medium",
                "evidence": {"note": "On-demand AI evaluation requested by user"},
                "savings": {"monthly": 0.0}
            }

        # 3. Extract and normalize fields
        config = resource.get("configuration", {})
        metrics = resource.get("metrics", {})
        cost = resource.get("cost", {})
        tags = resource.get("tags", {})
        provider = resource.get("provider", "aws").upper()
        res_type = resource.get("resource_type", "compute_instance").lower()

        current_sku = (
            config.get("instance_type") or 
            config.get("sku") or 
            config.get("machine_type") or 
            config.get("storage_type") or 
            "standard"
        )
        monthly_cost = float(cost.get("monthly", 0.0))
        baseline_savings = float(finding.get("savings", {}).get("monthly", finding.get("estimated_savings", 0.0)))
        rule_id = finding.get("rule_id", "UNKNOWN")

        context_data = {
            "resource_id": resource.get("resource_id", resource_id),
            "resource_name": resource.get("name") or resource.get("resource_name") or resource_id,
            "provider": provider,
            "resource_type": res_type,
            "current_sku": current_sku,
            "monthly_cost": monthly_cost,
            "baseline_savings": baseline_savings,
            "rule_id": rule_id,
            "finding_title": finding.get("finding_type", "Cost Optimization Review"),
            "evidence": str(finding.get("evidence", {})),
            "tags": str(tags),
            "cpu_avg": float(metrics.get("cpu_average", 0.0)),
            "cpu_peak": float(metrics.get("cpu_peak", metrics.get("cpu_average", 0.0) * 1.25)),
            "memory_avg": float(metrics.get("memory_average", 0.0)),
            "memory_peak": float(metrics.get("memory_peak", metrics.get("memory_average", 0.0) * 1.15)),
            "network_mbps": float(metrics.get("network_in_mbps", 0.0) + metrics.get("network_out_mbps", 0.0)),
            "storage_gb": float(config.get("size_gb", config.get("disk_size_gb", 100))),
            "read_iops": int(metrics.get("disk_read_ops", 0)),
            "write_iops": int(metrics.get("disk_write_ops", 0)),
            "total_iops": int(metrics.get("disk_read_ops", 0) + metrics.get("disk_write_ops", 0)),
            "db_engine": config.get("engine", "Relational Database"),
            "active_connections": int(metrics.get("active_connections", 5))
        }

        # 4. Select prompt template from library based on rule / resource type
        rule_lower = rule_id.lower()
        if "ebs-001" in rule_lower or "disk-001" in rule_lower or "ec2-002" in rule_lower or "vm-002" in rule_lower or "idle" in rule_lower:
            prompt = IDLE_CLEANUP_PROMPT.format(**context_data)
        elif "ebs-002" in rule_lower or "disk-002" in rule_lower or "storage" in res_type:
            prompt = STORAGE_OPTIMIZATION_PROMPT.format(**context_data)
        elif "rds" in rule_lower or "sql" in rule_lower or "database" in res_type:
            prompt = DATABASE_TUNING_PROMPT.format(**context_data)
        else:
            prompt = COMPUTE_RIGHTSIZING_PROMPT.format(**context_data)

        return prompt, context_data

