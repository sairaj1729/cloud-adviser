import logging
from datetime import datetime
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.providers.factory import ProviderFactory
from app.normalization.resource import ResourceNormalizer
from app.normalization.metrics import MetricsNormalizer
from app.normalization.cost import CostNormalizer
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RuleRegistry
from app.schemas.account import ScanSummarySchema

logger = logging.getLogger(__name__)

class ScanService:

    @staticmethod
    async def execute_scan(
        db: AsyncIOMotorDatabase,
        user_id: str,
        cloud_account_id: str
    ) -> ScanSummarySchema:
        # 1. Fetch Cloud Account
        try:
            account = await db.cloud_accounts.find_one({
                "_id": ObjectId(cloud_account_id),
                "user_id": user_id
            })
        except Exception:
            account = await db.cloud_accounts.find_one({
                "_id": cloud_account_id,
                "user_id": user_id
            })

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud account not found or access denied."
            )

        # 2. Get Connector & Verify
        connector = ProviderFactory.get_connector(account)
        verified = await connector.verify_connection()
        if not verified:
            await db.cloud_accounts.update_one(
                {"_id": account["_id"]},
                {"$set": {"status": "error", "updated_at": datetime.utcnow()}}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cloud account verification failed. Check credentials/roles."
            )

        # 3. Fetch Resources, Metrics, and Costs
        raw_resources = await connector.get_resources()
        normalized_count = 0

        for raw_res in raw_resources:
            res_id = raw_res.get("resource_id")
            raw_metrics = await connector.get_metrics(res_id)
            raw_cost = await connector.get_costs(res_id)

            norm_metrics = MetricsNormalizer.normalize_metrics(raw_metrics)
            norm_cost = CostNormalizer.normalize_cost(raw_cost)

            normalized_doc = ResourceNormalizer.normalize_resource(
                raw_resource=raw_res,
                user_id=user_id,
                cloud_account_id=str(account["_id"]),
                provider=account["provider"],
                account_id=account["account_identifier"],
                metrics=norm_metrics,
                cost=norm_cost
            )

            # Upsert into MongoDB `resources`
            await db.resources.update_one(
                {
                    "user_id": user_id,
                    "provider": normalized_doc["provider"],
                    "resource_id": normalized_doc["resource_id"]
                },
                {"$set": normalized_doc},
                upsert=True
            )
            normalized_count += 1

        # 4. Seed Rules if empty & Run Rule Engine
        await RuleRegistry.seed_rules(db)
        rule_engine = RuleEngine(db)
        scan_results = await rule_engine.evaluate_account(user_id, str(account["_id"]))

        # Update last_verified_at
        await db.cloud_accounts.update_one(
            {"_id": account["_id"]},
            {"$set": {"status": "connected", "last_verified_at": datetime.utcnow()}}
        )

        return ScanSummarySchema(
            status="completed",
            resources_scanned=normalized_count,
            rules_evaluated=scan_results.get("rules_evaluated", 0),
            findings_created=scan_results.get("findings_created", 0),
            estimated_monthly_savings=scan_results.get("estimated_monthly_savings", 0.0)
        )
