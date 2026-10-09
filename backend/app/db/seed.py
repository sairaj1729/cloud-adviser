import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import get_password_hash
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RuleRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_seed")

async def seed_database_instance(db):
    logger.info("Seeding database collections from synthetic data/data.json...")

    now = datetime.now(timezone.utc)

    # 1. Seed Users
    demo_user = {
        "email": "jordan@acme.io",
        "password_hash": get_password_hash("password123"),
        "name": "Jordan Davis",
        "created_at": now,
        "updated_at": now
    }
    admin_user = {
        "email": "achal@acme.io",
        "password_hash": get_password_hash("achal"),
        "name": "Achal",
        "created_at": now,
        "updated_at": now
    }

    await db.users.update_one(
        {"email": demo_user["email"]},
        {"$set": demo_user},
        upsert=True
    )
    await db.users.update_one(
        {"email": admin_user["email"]},
        {"$set": admin_user},
        upsert=True
    )

    user_doc = await db.users.find_one({"email": "jordan@acme.io"})
    user_id = str(user_doc["_id"])
    logger.info(f"Seeded users. Demo User ID: {user_id}")

    # 2. Seed Cloud Accounts
    accounts = [
        {
            "user_id": user_id,
            "provider": "aws",
            "display_name": "Production AWS Account",
            "status": "connected",
            "account_identifier": "412907386215",
            "region": "us-east-1",
            "credential_type": "assume_role",
            "provider_config": {
                "role_arn": "arn:aws:iam::412907386215:role/CloudAdvisorReadOnly",
                "external_id": "ca-ext-9988"
            },
            "last_verified_at": now,
            "created_at": now,
            "updated_at": now
        },
        {
            "user_id": user_id,
            "provider": "azure",
            "display_name": "Analytics Azure Subscription",
            "status": "connected",
            "account_identifier": "e2d4fb8a-81d4-487a-931a-11735b292cfe",
            "region": "westeurope",
            "credential_type": "client_secret",
            "provider_config": {
                "azure_tenant_id": "fbb80e19-01a7-4f1f-8319-f8cac7947548",
                "azure_client_id": "23ad0e53-21e0-4753-984e-e5993b118691"
            },
            "last_verified_at": now,
            "created_at": now,
            "updated_at": now
        },
        {
            "user_id": user_id,
            "provider": "gcp",
            "display_name": "Data Platform GCP Project",
            "status": "connected",
            "account_identifier": "acme-data-prod",
            "region": "us-central1",
            "credential_type": "service_account",
            "provider_config": {
                "gcp_project_id": "acme-data-prod"
            },
            "last_verified_at": now,
            "created_at": now,
            "updated_at": now
        }
    ]

    account_ids = {}
    for acc in accounts:
        res = await db.cloud_accounts.update_one(
            {"user_id": user_id, "provider": acc["provider"], "account_identifier": acc["account_identifier"]},
            {"$set": acc},
            upsert=True
        )
        saved = await db.cloud_accounts.find_one({
            "user_id": user_id,
            "provider": acc["provider"],
            "account_identifier": acc["account_identifier"]
        })
        account_ids[acc["provider"]] = str(saved["_id"])

    logger.info(f"Seeded cloud accounts: {list(account_ids.keys())}")

    # 3. Seed Rules into Registry
    await RuleRegistry.seed_rules(db)
    logger.info("Seeded default rules into Rule Registry.")

    # 4. Load synthetic data from data.json
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "synthetic data", "data.json")),
        r"d:\Internship\Cloud\synthetic data\data.json"
    ]
    data_file = None
    for p in possible_paths:
        if os.path.exists(p):
            data_file = p
            break

    if data_file:
        with open(data_file, "r", encoding="utf-8") as f:
            raw_resources = json.load(f)

        logger.info(f"Loading {len(raw_resources)} resources from {data_file}...")

        # Batch insert into MongoDB resources
        docs_to_insert = []
        for r in raw_resources:
            prov = r.get("provider", "aws").lower()
            acc_id = account_ids.get(prov, list(account_ids.values())[0] if account_ids else "default")

            doc = {
                "user_id": user_id,
                "cloud_account_id": acc_id,
                "provider": prov,
                "account_id": r.get("account_id") or "default",
                "resource_type": r.get("resource_type", "compute_instance"),
                "resource_id": r.get("resource_id", "res-unknown"),
                "region": r.get("region", "us-east-1"),
                "name": r.get("name") or r.get("resource_id", "unnamed"),
                "configuration": r.get("configuration") or {},
                "tags": r.get("tags") or {},
                "metrics": r.get("metrics") or {},
                "cost": r.get("cost") or {"monthly": 0.0, "currency": "USD"},
                "last_synced_at": now
            }
            docs_to_insert.append(doc)

        # Clear old and insert
        await db.resources.delete_many({"user_id": user_id})
        if docs_to_insert:
            # Insert in chunks of 500
            for i in range(0, len(docs_to_insert), 500):
                chunk = docs_to_insert[i:i+500]
                await db.resources.insert_many(chunk)
            logger.info(f"Seeded {len(docs_to_insert)} resources into collection.")

        # 5. Run Rule Engine across all 3 accounts
        rule_engine = RuleEngine(db)
        total_findings = 0
        total_savings = 0.0
        for prov, a_id in account_ids.items():
            res = await rule_engine.evaluate_account(user_id, a_id)
            total_findings += res.get("findings_created", 0)
            total_savings += res.get("estimated_monthly_savings", 0.0)

        logger.info(f"Rule Engine scan generated {total_findings} findings (${total_savings:.2f}/mo potential savings).")
    else:
        logger.warning("synthetic data/data.json file not found; skipped full dataset seeding.")

    logger.info("Database seeding completed successfully!")

if __name__ == "__main__":
    async def main():
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_DATABASE]
        await seed_database_instance(db)
        client.close()
    asyncio.run(main())
