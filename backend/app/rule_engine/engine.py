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
        query = {"user_id": user_id}
        if cloud_account_id:
            matched = await self.db.resources.count_documents({"user_id": user_id, "cloud_account_id": cloud_account_id})
            if matched > 0:
                query["cloud_account_id"] = cloud_account_id
            else:
                try:
                    from bson import ObjectId
                    acc = await self.db.cloud_accounts.find_one({"_id": ObjectId(cloud_account_id)})
                except Exception:
                    acc = await self.db.cloud_accounts.find_one({"_id": cloud_account_id})
                if acc and acc.get("provider"):
                    query["provider"] = acc["provider"].lower()

        res_cursor = self.db.resources.find(query)
        resources = await res_cursor.to_list(length=10000)

        rules_evaluated_count = 0
        findings_created_count = 0
        total_monthly_savings = 0.0

        for resource in resources:
            for rule in rules:
                # Match provider and resource_type (with alias support)
                if rule.get("provider", "").lower() != resource.get("provider", "").lower():
                    continue
                rule_type = str(rule.get("resource_type", "")).lower()
                res_type = str(resource.get("resource_type", "")).lower()
                type_aliases = {
                    "virtual_machine": {"virtual_machine", "compute_instance"},
                    "compute_instance": {"virtual_machine", "compute_instance"},
                    "database_instance": {"database_instance", "database"},
                    "database": {"database_instance", "database"},
                    "storage_volume": {"storage_volume", "block_storage", "object_storage"},
                    "block_storage": {"storage_volume", "block_storage", "object_storage"},
                    "object_storage": {"storage_volume", "block_storage", "object_storage"}
                }
                valid_types = type_aliases.get(rule_type, {rule_type})
                if res_type not in valid_types:
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

                    # Build Finding Document (without overwriting user-decided status)
                    finding_doc = {
                        "user_id": user_id,
                        "cloud_account_id": cloud_account_id or resource.get("cloud_account_id"),
                        "rule_id": rule.get("rule_id"),
                        "resource_id": resource.get("resource_id"),
                        "resource_name": resource.get("name"),
                        "resource_type": resource.get("resource_type"),
                        "provider": resource.get("provider"),
                        "severity": rule.get("severity", "medium"),
                        "evidence": evidence,
                        "recommendation": rule.get("recommendation", {}),
                        "savings": savings,
                        "cost": resource.get("cost", {}),
                        "metrics": resource.get("metrics", {}),
                        "configuration": resource.get("configuration", {}),
                        "source": "Cloud Advisor Rule Engine",
                        "updated_at": datetime.utcnow()
                    }

                    # Upsert Finding in MongoDB (set fields, preserve existing custom status if already set)
                    await self.db.findings.update_one(
                        {
                            "user_id": user_id,
                            "resource_id": resource.get("resource_id"),
                            "rule_id": rule.get("rule_id")
                        },
                        {
                            "$set": finding_doc,
                            "$setOnInsert": {
                                "status": "open",
                                "created_at": datetime.utcnow()
                            }
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

    async def evaluate_all_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Evaluates all cloud accounts and resources for a user against active rules from db.rules:
        1. Fetch active rules from MongoDB `rules` collection.
        2. Evaluate all user resources.
        3. Remove/prune any findings whose rules were deleted or deactivated in MongoDB.
        4. Return summary metrics.
        """
        # Fetch active rules
        cursor = self.db.rules.find({"status": "active"})
        active_rules = await cursor.to_list(length=200)
        active_rule_ids = [r["rule_id"] for r in active_rules]
        logger.info(f"Evaluating {len(active_rules)} active rules from MongoDB for user {user_id}: {active_rule_ids}")

        target_user_id = user_id
        user_res_count = await self.db.resources.count_documents({"user_id": user_id})
        if user_res_count == 0:
            demo_user = await self.db.users.find_one({"email": "jordan@acme.io"})
            if demo_user:
                target_user_id = str(demo_user["_id"])

        res_cursor = self.db.resources.find({"user_id": target_user_id})
        resources = await res_cursor.to_list(length=10000)
        if not resources:
            res_cursor = self.db.resources.find({})
            resources = await res_cursor.to_list(length=10000)

        rules_evaluated_count = 0
        findings_created_count = 0
        total_monthly_savings = 0.0

        for resource in resources:
            for rule in active_rules:
                if rule.get("provider", "").lower() != resource.get("provider", "").lower():
                    continue
                rule_type = str(rule.get("resource_type", "")).lower()
                res_type = str(resource.get("resource_type", "")).lower()
                type_aliases = {
                    "virtual_machine": {"virtual_machine", "compute_instance"},
                    "compute_instance": {"virtual_machine", "compute_instance"},
                    "database_instance": {"database_instance", "database"},
                    "database": {"database_instance", "database"},
                    "storage_volume": {"storage_volume", "block_storage", "object_storage"},
                    "block_storage": {"storage_volume", "block_storage", "object_storage"},
                    "object_storage": {"storage_volume", "block_storage", "object_storage"}
                }
                valid_types = type_aliases.get(rule_type, {rule_type})
                if res_type not in valid_types:
                    continue

                rules_evaluated_count += 1

                is_match, evidence_items = RuleEvaluator.evaluate_conditions(
                    resource, rule.get("conditions", {})
                )

                if is_match:
                    evidence = EvidenceGenerator.build_evidence(rule, resource, evidence_items)
                    savings = SavingsCalculator.calculate_savings(rule, resource)

                    finding_doc = {
                        "user_id": user_id,
                        "cloud_account_id": resource.get("cloud_account_id"),
                        "rule_id": rule.get("rule_id"),
                        "resource_id": resource.get("resource_id"),
                        "resource_name": resource.get("name"),
                        "resource_type": resource.get("resource_type"),
                        "provider": resource.get("provider"),
                        "severity": rule.get("severity", "medium"),
                        "evidence": evidence,
                        "recommendation": rule.get("recommendation", {}),
                        "savings": savings,
                        "cost": resource.get("cost", {}),
                        "metrics": resource.get("metrics", {}),
                        "configuration": resource.get("configuration", {}),
                        "source": "Cloud Advisor Rule Engine",
                        "updated_at": datetime.utcnow()
                    }

                    await self.db.findings.update_one(
                        {
                            "user_id": user_id,
                            "resource_id": resource.get("resource_id"),
                            "rule_id": rule.get("rule_id")
                        },
                        {
                            "$set": finding_doc,
                            "$setOnInsert": {
                                "status": "open",
                                "created_at": datetime.utcnow()
                            }
                        },
                        upsert=True
                    )
                    findings_created_count += 1
                    total_monthly_savings += savings.get("monthly", 0.0)

        # Clean up stale findings for rules that are no longer active in MongoDB
        if active_rule_ids:
            deleted_stale = await self.db.findings.delete_many({
                "user_id": user_id,
                "rule_id": {"$nin": active_rule_ids}
            })
            if deleted_stale.deleted_count > 0:
                logger.info(f"Pruned {deleted_stale.deleted_count} stale findings from inactive/removed rules.")

        logger.info(
            f"Rule evaluation completed for user {user_id}: "
            f"{findings_created_count} findings stored in db.findings (${total_monthly_savings:.2f}/mo potential savings)"
        )

        return {
            "status": "completed",
            "active_rules_count": len(active_rules),
            "resources_scanned": len(resources),
            "rules_evaluated": rules_evaluated_count,
            "findings_stored": findings_created_count,
            "estimated_monthly_savings": round(total_monthly_savings, 2)
        }

