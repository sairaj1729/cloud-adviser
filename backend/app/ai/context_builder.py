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
        # 1. Fetch Finding from MongoDB FIRST (if exists) so we match dataset_id & exact cost snapshot
        finding = None
        if finding_id:
            try:
                from bson import ObjectId
                finding = await self.db.findings.find_one({"_id": ObjectId(finding_id)})
            except Exception:
                finding = await self.db.findings.find_one({"id": finding_id})
        if not finding:
            finding = await self.db.findings.find_one(
                {"resource_id": resource_id},
                sort=[("savings.monthly", -1), ("updated_at", -1)]
            )

        # Collect ALL violated rules for this resource in the active dataset
        all_findings_query: Dict[str, Any] = {"resource_id": resource_id}
        if finding and finding.get("dataset_id"):
            all_findings_query["dataset_id"] = finding["dataset_id"]
        all_findings = await self.db.findings.find(all_findings_query).sort("savings.monthly", -1).to_list(length=20)
        triggered_rules = [
            {
                "rule_id": af.get("rule_id", ""),
                "rule_name": af.get("evidence", {}).get("rule_name") or af.get("rule_id", ""),
                "severity": str(af.get("severity", "medium")).capitalize(),
                "savings": round(float(af.get("savings", {}).get("monthly", 0.0) or 0.0), 2),
            }
            for af in all_findings if af.get("rule_id")
        ]

        # 2. Fetch latest Resource snapshot from MongoDB matching dataset_id if available
        res_filter: Dict[str, Any] = {"resource_id": resource_id}
        if finding and finding.get("dataset_id"):
            res_filter["dataset_id"] = finding["dataset_id"]

        resource = await self.db.resources.find_one(res_filter, sort=[("last_synced_at", -1)])
        if not resource:
            resource = await self.db.resources.find_one({"resource_id": resource_id}, sort=[("last_synced_at", -1)])
        if not resource:
            resource = await self.db.resources.find_one({"id": resource_id}, sort=[("last_synced_at", -1)])
        if not resource:
            resource = await self.db.resources.find_one({"name": resource_id}, sort=[("last_synced_at", -1)])
        if not resource:
            # Fallback search matching trailing resource identifier segment
            short_id = resource_id.split("/")[-1].split(":")[-1]
            resource = await self.db.resources.find_one({"name": short_id}, sort=[("last_synced_at", -1)])
        if not resource:
            raise ValueError(f"Resource '{resource_id}' not found in MongoDB.")

        # Safe defaults if no prior finding existed
        if not finding:
            finding = {
                "rule_id": "MANUAL-REVIEW-001",
                "finding_type": "RIGHTSIZING_REVIEW",
                "severity": "medium",
                "evidence": {"note": "On-demand AI evaluation requested by user"},
                "savings": {"monthly": 0.0}
            }

        # 3. Extract and normalize fields (prefer finding's cost/metrics snapshot if present for consistency)
        config = resource.get("configuration", {})
        res_metrics = resource.get("metrics", {})
        finding_metrics = finding.get("metrics", {})
        metrics = {**res_metrics, **{k: v for k, v in finding_metrics.items() if v is not None}}
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
        finding_cost = float(finding.get("cost", {}).get("monthly", 0.0) or 0.0)
        resource_cost = float(cost.get("monthly", 0.0) or 0.0)
        monthly_cost = finding_cost if finding_cost > 0.0 else resource_cost
        baseline_savings = float(finding.get("savings", {}).get("monthly", finding.get("estimated_savings", 0.0)))
        rule_id = finding.get("rule_id", "UNKNOWN")

        context_data = {
            "resource_id": resource.get("resource_id", resource_id),
            "resource_name": resource.get("name") or resource.get("resource_name") or resource_id,
            "provider": provider,
            "dataset_id": finding.get("dataset_id") or resource.get("dataset_id"),
            "resource_type": res_type,
            "current_sku": current_sku,
            "monthly_cost": monthly_cost,
            "baseline_savings": baseline_savings,
            "rule_id": rule_id,
            "triggered_rules": triggered_rules,
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

