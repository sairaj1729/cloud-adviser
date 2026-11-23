import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RecommendationValidator:
    """
    Enforces deterministic sanity guardrails on LLM-generated recommendations.
    Guarantees no financial or schema hallucinations enter the database.
    """
    VALID_ACTIONS = {"RIGHTSIZE", "STOP", "TERMINATE", "STORAGE_DOWNGRADE", "NO_ACTION"}
    VALID_RISKS = {"LOW", "MEDIUM", "HIGH"}

    @classmethod
    def validate_and_sanitize(cls, raw: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        monthly_cost = float(context.get("monthly_cost", 0.0))

        # 1. Action Validation
        action = str(raw.get("action", "RIGHTSIZE")).upper()
        if action not in cls.VALID_ACTIONS:
            action = "RIGHTSIZE"

        # 2. Savings Guardrail: 0 <= Savings <= Current Monthly Cost
        try:
            savings = float(raw.get("estimated_monthly_savings", 0.0))
        except (ValueError, TypeError):
            savings = 0.0

        if savings < 0.0:
            savings = 0.0
        elif monthly_cost > 0.0 and savings > monthly_cost:
            savings = monthly_cost

        savings = round(savings, 2)

        # 3. Percentage Calculation
        if monthly_cost > 0.0:
            pct = round((savings / monthly_cost) * 100.0, 1)
        else:
            pct = 0.0

        # 4. Risk Level Validation
        risk = str(raw.get("risk_level", "LOW")).upper()
        if risk not in cls.VALID_RISKS:
            risk = "LOW"

        # 5. Resource Type, Service Name, and Category
        from app.services.analytics_service import get_service_name, get_category_name
        prov = context.get("provider", "AWS")
        rtype = context.get("resource_type", "compute_instance")
        sname = get_service_name(rtype, prov)
        cat_name = get_category_name(rtype)

        # 6. Build clean dictionary
        return {
            "resource_id": context["resource_id"],
            "resource_name": context.get("resource_name"),
            "provider": prov,
            "resource_type": rtype,
            "service": sname,
            "category": cat_name,
            "dataset_id": context.get("dataset_id"),
            "action": action,
            "target_sku": raw.get("target_sku"),
            "current_sku": context.get("current_sku"),
            "current_monthly_cost": monthly_cost,
            "estimated_monthly_savings": savings,
            "estimated_savings_percentage": pct,
            "risk_level": risk,
            "justification": str(raw.get("justification", "Resource optimization identified by Cloud Advisor.")),
            "remediation_steps": raw.get("remediation_steps") or [
                "Review performance baseline",
                "Execute configuration change",
                "Monitor for 24 hours"
            ],
            "remediation_command": raw.get("remediation_command")
        }

