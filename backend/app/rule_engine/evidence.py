from typing import Dict, Any, List

class EvidenceGenerator:

    @staticmethod
    def build_evidence(
        rule: Dict[str, Any],
        resource: Dict[str, Any],
        evaluated_conditions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates evidence explaining why a rule fired."""
        lookback_window = rule.get("lookback_window", {"value": 14, "unit": "days"})
        
        evidence_summary = {
            "rule_id": rule.get("rule_id"),
            "rule_name": rule.get("name"),
            "lookback_period": f"{lookback_window.get('value', 14)} {lookback_window.get('unit', 'days')}",
            "monthly_cost": resource.get("cost", {}).get("monthly", 0.0),
            "currency": resource.get("cost", {}).get("currency", "USD"),
            "condition_evaluations": evaluated_conditions,
            "explanation": f"Resource '{resource.get('name')}' satisfied rule criteria: {rule.get('description')}"
        }
        return evidence_summary
