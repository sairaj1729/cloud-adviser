import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.rule_engine.engine import RuleEngine

logger = logging.getLogger(__name__)

DATASET_REGISTRY = {
    "bank_balanced": {
        "id": "bank_balanced",
        "name": "Global Bank Multi-Cloud",
        "domain": "Banking & FinTech",
        "description": "Tier-1 Global Bank (10,000 balanced assets across AWS, Azure, GCP)",
        "file": "bank_resources_aws_azure_gcp_balanced.json",
        "item_count": 10000,
        "icon": "Building2"
    },
    "retail_balanced": {
        "id": "retail_balanced",
        "name": "Enterprise Retail Fleet",
        "domain": "Retail & E-Commerce",
        "description": "Enterprise Retail & Supply Chain (10,000 balanced assets across AWS, Azure, GCP)",
        "file": "retail_resources_aws_azure_gcp_balanced.json",
        "item_count": 10000,
        "icon": "ShoppingBag"
    },
    "retail_2900": {
        "id": "retail_2900",
        "name": "Mid-Market Retail Fleet",
        "domain": "Retail Operations",
        "description": "Mid-Market Omnichannel Retail (2,900 assets from data.json)",
        "file": "data.json",
        "item_count": 2900,
        "icon": "Store"
    }
}

class DatasetService:

    @classmethod
    def get_registered_datasets(cls) -> List[Dict[str, Any]]:
        return list(DATASET_REGISTRY.values())

    @classmethod
    async def get_active_dataset_id(cls, db: AsyncIOMotorDatabase, user_id: str) -> str:
        """Fetches active dataset preference from MongoDB, defaults to bank_balanced."""
        record = await db.active_datasets.find_one({"user_id": user_id})
        if record and record.get("dataset_id") in DATASET_REGISTRY:
            return record["dataset_id"]
        # Default to bank_balanced
        return "bank_balanced"

    @classmethod
    async def set_active_dataset_id(cls, db: AsyncIOMotorDatabase, user_id: str, dataset_id: str) -> None:
        if dataset_id not in DATASET_REGISTRY:
            raise ValueError(f"Unknown dataset_id: {dataset_id}")
        await db.active_datasets.update_one(
            {"user_id": user_id},
            {"$set": {"dataset_id": dataset_id, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

    @classmethod
    async def list_datasets_with_status(cls, db: AsyncIOMotorDatabase, user_id: str) -> List[Dict[str, Any]]:
        active_id = await cls.get_active_dataset_id(db, user_id)
        result = []
        for ds_id, ds in DATASET_REGISTRY.items():
            loaded_count = await db.resources.count_documents({"dataset_id": ds_id})
            findings_count = await db.findings.count_documents({"dataset_id": ds_id})
            result.append({
                **ds,
                "is_active": (ds_id == active_id),
                "loaded_resources": loaded_count,
                "generated_findings": findings_count
            })
        return result

    @classmethod
    async def ensure_dataset_seeded(cls, db: AsyncIOMotorDatabase, dataset_id: str, user_id: str) -> Dict[str, Any]:
        """
        Ensures that the given dataset is populated into db.resources and that
        the RuleEngine has evaluated rules and populated db.findings.
        """
        if dataset_id not in DATASET_REGISTRY:
            dataset_id = "bank_balanced"

        spec = DATASET_REGISTRY[dataset_id]
        now = datetime.now(timezone.utc)

        # 1. Check if resources are already seeded in MongoDB
        existing_res_count = await db.resources.count_documents({"dataset_id": dataset_id})
        if existing_res_count == 0:
            logger.info(f"Seeding dataset '{dataset_id}' from {spec['file']} into db.resources...")

            env_dir = os.environ.get("SYNTHETIC_DATA_DIR")
            possible_paths = [
                os.path.join(env_dir, spec["file"]) if env_dir else None,
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "synthetic data", spec["file"])),
                os.path.join("/app", "synthetic data", spec["file"]),
                os.path.join("/synthetic data", spec["file"]),
                os.path.join("synthetic data", spec["file"]),
                os.path.join("..", "synthetic data", spec["file"]),
                os.path.join(os.getcwd(), "synthetic data", spec["file"]),
            ]
            file_path = None
            for p in possible_paths:
                if p and os.path.exists(p):
                    file_path = p
                    break

            if not file_path:
                raise FileNotFoundError(f"Dataset file not found: {spec['file']}")

            with open(file_path, "r", encoding="utf-8") as fp:
                raw_resources = json.load(fp)

            # Ensure accounts exist in cloud_accounts
            providers = set(r.get("provider", "aws").lower() for r in raw_resources)
            acc_ids = {}
            for prov in providers:
                acc_doc = await db.cloud_accounts.find_one({"user_id": user_id, "provider": prov})
                if not acc_doc:
                    new_acc = {
                        "user_id": user_id,
                        "provider": prov,
                        "display_name": f"{spec['name']} ({prov.upper()})",
                        "status": "connected",
                        "account_identifier": f"acc-{dataset_id}-{prov}",
                        "region": "us-east-1" if prov == "aws" else "eastus2" if prov == "azure" else "us-central1",
                        "credential_type": "managed_dataset",
                        "provider_config": {},
                        "created_at": now,
                        "updated_at": now
                    }
                    res = await db.cloud_accounts.insert_one(new_acc)
                    acc_ids[prov] = str(res.inserted_id)
                else:
                    acc_ids[prov] = str(acc_doc["_id"])

            # Prepare documents to insert
            docs = []
            for item in raw_resources:
                prov = item.get("provider", "aws").lower()
                doc = {
                    "user_id": user_id,
                    "dataset_id": dataset_id,
                    "cloud_account_id": item.get("cloud_account_id") or acc_ids.get(prov, "acc-default"),
                    "provider": prov,
                    "account_id": item.get("account_id") or f"{dataset_id}-{prov}",
                    "resource_type": item.get("resource_type", "compute_instance"),
                    "resource_id": item.get("resource_id") or f"res-{dataset_id}-{len(docs)}",
                    "region": item.get("region") or "us-east-1",
                    "name": item.get("name") or item.get("resource_id", "unnamed"),
                    "configuration": item.get("configuration") or {},
                    "tags": item.get("tags") or {},
                    "metrics": item.get("metrics") or {},
                    "cost": item.get("cost") or {"monthly": 0.0, "currency": "USD"},
                    "last_synced_at": item.get("last_synced_at") or now.isoformat()
                }
                docs.append(doc)

            # Insert in chunks of 1000
            for i in range(0, len(docs), 1000):
                chunk = docs[i:i + 1000]
                await db.resources.insert_many(chunk)

            logger.info(f"Inserted {len(docs)} resources for dataset '{dataset_id}'.")

        # 2. Check if findings are already generated in db.findings
        existing_findings_count = await db.findings.count_documents({"dataset_id": dataset_id})
        if existing_findings_count == 0:
            logger.info(f"Evaluating Rule Engine for dataset '{dataset_id}'...")
            engine = RuleEngine(db)
            await engine.evaluate_all_for_user(user_id, dataset_id=dataset_id)
            findings_created = await db.findings.count_documents({"dataset_id": dataset_id})
            logger.info(f"Rule Engine generated {findings_created} findings for dataset '{dataset_id}'.")

        return {
            "dataset_id": dataset_id,
            "status": "ready",
            "name": spec["name"],
            "domain": spec["domain"],
            "resources_count": await db.resources.count_documents({"dataset_id": dataset_id}),
            "findings_count": await db.findings.count_documents({"dataset_id": dataset_id})
        }
