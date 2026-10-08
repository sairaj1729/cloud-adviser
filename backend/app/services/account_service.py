from datetime import datetime
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Any

from app.schemas.account import CloudAccountCreateSchema, CloudAccountOutSchema
from app.providers.factory import ProviderFactory

class AccountService:

    @staticmethod
    async def create_account(
        db: AsyncIOMotorDatabase,
        user_id: str,
        acc_in: CloudAccountCreateSchema
    ) -> CloudAccountOutSchema:
        provider_config = acc_in.provider_config or {}
        if acc_in.role_arn:
            provider_config["role_arn"] = acc_in.role_arn
        if acc_in.external_id:
            provider_config["external_id"] = acc_in.external_id
        if acc_in.azure_tenant_id:
            provider_config["azure_tenant_id"] = acc_in.azure_tenant_id
        if acc_in.azure_client_id:
            provider_config["azure_client_id"] = acc_in.azure_client_id
        if acc_in.azure_client_secret:
            provider_config["azure_client_secret"] = acc_in.azure_client_secret
        if acc_in.gcp_project_id:
            provider_config["gcp_project_id"] = acc_in.gcp_project_id

        doc = {
            "user_id": user_id,
            "provider": acc_in.provider.lower(),
            "display_name": acc_in.display_name,
            "status": "connected",
            "account_identifier": acc_in.account_identifier,
            "region": acc_in.region or "us-east-1",
            "credential_type": acc_in.credential_type,
            "provider_config": provider_config,
            "last_verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Verify connection
        connector = ProviderFactory.get_connector(doc)
        verified = await connector.verify_connection()
        if not verified:
            doc["status"] = "error"

        res = await db.cloud_accounts.insert_one(doc)
        doc["id"] = str(res.inserted_id)

        # Sanitize sensitive keys for response DTO
        sanitized_config = {k: v for k, v in provider_config.items() if "secret" not in k.lower()}

        return CloudAccountOutSchema(
            id=doc["id"],
            user_id=user_id,
            provider=doc["provider"],
            display_name=doc["display_name"],
            status=doc["status"],
            account_identifier=doc["account_identifier"],
            region=doc["region"],
            credential_type=doc["credential_type"],
            provider_config=sanitized_config,
            last_verified_at=doc["last_verified_at"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    @staticmethod
    async def list_accounts(db: AsyncIOMotorDatabase, user_id: str) -> List[CloudAccountOutSchema]:
        cursor = db.cloud_accounts.find({"user_id": user_id})
        accounts = await cursor.to_list(length=100)
        out = []
        for acc in accounts:
            sanitized_config = {k: v for k, v in acc.get("provider_config", {}).items() if "secret" not in k.lower()}
            out.append(CloudAccountOutSchema(
                id=str(acc["_id"]),
                user_id=user_id,
                provider=acc["provider"],
                display_name=acc["display_name"],
                status=acc["status"],
                account_identifier=acc["account_identifier"],
                region=acc.get("region", "us-east-1"),
                credential_type=acc["credential_type"],
                provider_config=sanitized_config,
                last_verified_at=acc.get("last_verified_at"),
                created_at=acc.get("created_at", datetime.utcnow()),
                updated_at=acc.get("updated_at")
            ))
        return out
