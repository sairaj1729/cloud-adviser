from typing import Dict, Any
from datetime import datetime

class ResourceNormalizer:

    @staticmethod
    def normalize_resource(
        raw_resource: Dict[str, Any],
        user_id: str,
        cloud_account_id: str,
        provider: str,
        account_id: str,
        metrics: Dict[str, Any],
        cost: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transforms provider-specific API payloads into the Normalized Common Resource Model."""
        return {
            "user_id": user_id,
            "cloud_account_id": cloud_account_id,
            "provider": provider.lower(),
            "account_id": account_id,
            "resource_type": raw_resource.get("resource_type", "compute_instance"),
            "resource_id": raw_resource.get("resource_id"),
            "region": raw_resource.get("region", "us-east-1"),
            "name": raw_resource.get("name", raw_resource.get("resource_id")),
            "configuration": raw_resource.get("configuration", {}),
            "tags": raw_resource.get("tags", {}),
            "metrics": {
                "cpu_average": float(metrics.get("cpu_average", 0.0)),
                "cpu_p95": float(metrics.get("cpu_p95", 0.0)),
                "memory_average": float(metrics.get("memory_average", 0.0)),
                "memory_p95": float(metrics.get("memory_p95", 0.0))
            },
            "cost": {
                "monthly": float(cost.get("monthly", 0.0)),
                "currency": cost.get("currency", "USD")
            },
            "last_synced_at": datetime.utcnow()
        }
