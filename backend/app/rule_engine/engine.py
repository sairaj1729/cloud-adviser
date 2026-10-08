import logging
from typing import Dict, List, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.rule_engine.evaluator import RuleEvaluator
from app.rule_engine.evidence import EvidenceGenerator
from app.rule_engine.savings import SavingsCalculator

logger = logging.getLogger(__name__)

class RuleEngine:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def evaluate_account(self, user_id: str, cloud_account_id: str) -> Dict[str, Any]:
        """
        Master evaluation pipeline:
        1. Fetch active rules from MongoDB `rules` collection.
        2. Query normalized resources matching user_id & cloud_account_id.
        3. Evaluate conditions for matching resource types.
        4. Generate Evidence & calculate Savings.
        5. Upsert Finding in MongoDB `findings` collection.
        """
        # Fetch active rules
        cursor = self.db.rules.find({"status": "active"})
        rules = await cursor.to_list(length=100)

        # Fetch resources
        res_cursor = self.db.resources.find({
            "user_id": user_id,
            "cloud_account_id": cloud_account_id
        })
        resources = await res_cursor.to_list(length=1000)

        rules_evaluated_count = 0
        findings_created_count = 0
        total_monthly_savings = 0.0

        for resource in resources:
            for rule in rules:
                # Match provider and resource_type
                if rule.get("provider", "").lower() != resource.get("provider", "").lower():
                    continue
                if rule.get("resource_type") != resource.get("resource_type"):
                    continue

                rules_evaluated_count += 1

                # Evaluate conditions
                is_match, evidence_items = RuleEvaluator.evaluate_conditions(
                    resource, rule.get("conditions", {})
                )

                if is_match:
                    # Generate Evidence
                    evidence = EvidenceGenerator.build_evidence(rule, resource, evidence_items)
                    # Calculate Savings
                    savings = SavingsCalculator.calculate_savings(rule, resource)

                    # Build Finding Document
                    finding_doc = {
                        "user_id": user_id,
                        "cloud_account_id": cloud_account_id,
                        "rule_id": rule.get("rule_id"),
                        "resource_id": resource.get("resource_id"),
                        "resource_name": resource.get("name"),
                        "provider": resource.get("provider"),
                        "severity": rule.get("severity", "medium"),
                        "status": "open",
                        "evidence": evidence,
                        "recommendation": rule.get("recommendation", {}),
                        "savings": savings,
                        "source": "Cloud Advisor Rule Engine",
                        "updated_at": datetime.utcnow()
                    }

                    # Upsert Finding
                    await self.db.findings.update_one(
                        {
                            "user_id": user_id,
                            "resource_id": resource.get("resource_id"),
                            "rule_id": rule.get("rule_id")
                        },
                        {
                            "$set": finding_doc,
                            "$setOnInsert": {"created_at": datetime.utcnow()}
                        },
                        upsert=True
                    )

                    findings_created_count += 1
                    total_monthly_savings += savings.get("monthly", 0.0)

        return {
            "status": "completed",
            "resources_scanned": len(resources),
            "rules_evaluated": rules_evaluated_count,
            "findings_created": findings_created_count,
            "estimated_monthly_savings": round(total_monthly_savings, 2)
        }
