from typing import Dict, Any

class SavingsCalculator:

    @staticmethod
    def calculate_savings(
        rule: Dict[str, Any],
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates estimated monthly & annual savings based on rule configuration.
        Distinguishes ESTIMATED savings from PROVIDER_REPORTED savings.
        """
        savings_config = rule.get("savings_calculation", {})
        calc_type = savings_config.get("type", "ESTIMATED")
        monthly_cost = float(resource.get("cost", {}).get("monthly", 0.0))
        currency = resource.get("cost", {}).get("currency", "USD")

        if calc_type == "ZERO_UTILIZATION":
            monthly_savings = monthly_cost
        elif calc_type == "ESTIMATED_PERCENTAGE":
            percentage = float(savings_config.get("percentage", 50.0))
            monthly_savings = round(monthly_cost * (percentage / 100.0), 2)
        elif calc_type == "FIXED_AMOUNT":
            monthly_savings = float(savings_config.get("amount", 50.0))
        else:
            # Default to 50% estimation
            monthly_savings = round(monthly_cost * 0.5, 2)

        annual_savings = round(monthly_savings * 12.0, 2)

        return {
            "monthly": monthly_savings,
            "annual": annual_savings,
            "currency": currency,
            "type": calc_type
        }
