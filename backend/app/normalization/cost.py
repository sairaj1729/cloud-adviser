from typing import Dict, Any

class CostNormalizer:

    @staticmethod
    def normalize_cost(raw_cost: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "monthly": round(float(raw_cost.get("monthly", 0.0)), 2),
            "currency": str(raw_cost.get("currency", "USD")).upper()
        }
