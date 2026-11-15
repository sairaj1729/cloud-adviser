from typing import Dict, Any, List
from app.rule_engine.operators import RuleOperators

def get_nested_field(doc: Dict[str, Any], field_path: str) -> Any:
    """Extract nested dictionary values using dot notation (e.g. 'metrics.cpu_average')."""
    keys = field_path.split(".")
    val = doc
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return None
    return val

class RuleEvaluator:

    @staticmethod
    def evaluate_conditions(resource: Dict[str, Any], conditions: Dict[str, Any]) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Evaluates a rule's conditions against a normalized resource document.
        Returns (is_match, evidence_items).
        """
        logic = conditions.get("logic", "AND").upper()
        items = conditions.get("items", [])

        results = []
        evidence_items = []

        for item in items:
            field_path = item.get("field")
            operator = item.get("operator")
            threshold = item.get("threshold")

            actual_val = get_nested_field(resource, field_path)
            passed = RuleOperators.evaluate(operator, actual_val, threshold)
            results.append(passed)

            evidence_items.append({
                "field": field_path,
                "actual_value": actual_val,
                "operator": operator,
                "threshold": threshold,
                "passed": passed
            })

        if logic == "AND":
            is_match = all(results) if results else False
        elif logic == "OR":
            is_match = any(results) if results else False
        else:
            is_match = False

        return is_match, evidence_items
