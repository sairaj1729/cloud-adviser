import uuid
from datetime import datetime
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Any

from app.schemas.account import (
    CloudAccountCreateSchema,
    CloudAccountOutSchema,
    AwsVerifyRequestSchema
)
from app.providers.factory import ProviderFactory
from app.core.config import settings

class AccountService:

    @staticmethod
    async def generate_aws_initiate_payload(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Step 1 & 2 of AWS Cross-Account Role Assumption:
        Creates a pending connection record, generates unique External ID and AWS Trust Relationship policy template.
        """
        ext_id = f"ca-ext-{uuid.uuid4().hex[:12]}"
        platform_arn = settings.PLATFORM_AWS_IAM_ROLE_ARN
        platform_acc = settings.PLATFORM_AWS_ACCOUNT_ID

        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": platform_arn
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "sts:ExternalId": ext_id
                        }
                    }
                }
            ]
        }

        recommended_permissions = [
            "arn:aws:iam::aws:policy/SecurityAudit",
            "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"
        ]

        # Record pending connection in db.pending_connections
        pending_doc = {
            "user_id": user_id,
            "provider": "aws",
            "external_id": ext_id,
            "platform_role_arn": platform_arn,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        res = await db.pending_connections.insert_one(pending_doc)

        return {
            "connection_id": str(res.inserted_id),
            "external_id": ext_id,
            "platform_aws_account_id": platform_acc,
            "platform_role_arn": platform_arn,
            "trust_policy": trust_policy,
            "recommended_permissions": recommended_permissions
        }

    @staticmethod
    async def verify_and_connect_aws(
        db: AsyncIOMotorDatabase,
        user_id: str,
        verify_in: AwsVerifyRequestSchema
    ) -> Dict[str, Any]:
        """
        Step 4 & 5 of AWS Cross-Account Role Assumption:
        1. Calls AWS STS to assume the customer role using the stored External ID.
        2. If verified, upserts the account in db.cloud_accounts with status='connected'.
        3. Begins fetching permitted resources and billing info in background.
        4. Returns verified account details and STS temporary session info.
        """
        doc = {
            "user_id": user_id,
            "provider": "aws",
            "display_name": verify_in.display_name,
            "status": "connected",
            "account_identifier": verify_in.account_id,
            "region": verify_in.region or "ap-south-1",
            "credential_type": "assume_role",
            "provider_config": {
                "role_arn": verify_in.role_arn,
                "external_id": verify_in.external_id,
                "platform_role_arn": settings.PLATFORM_AWS_IAM_ROLE_ARN
            },
            "last_verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Verify role assumption via AWS STS
        connector = ProviderFactory.get_connector(doc)
        verified = await connector.verify_connection()

        if not verified:
            doc["status"] = "error"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AWS STS AssumeRole verification failed. Ensure your IAM role trust policy matches the exact External ID and authorizes our platform ARN."
            )

        # Mark pending connection as verified
        try:
            await db.pending_connections.update_many(
                {"user_id": user_id, "external_id": verify_in.external_id},
                {"$set": {"status": "verified", "verified_at": datetime.utcnow()}}
            )
        except Exception:
            pass

        # Upsert account in MongoDB
        existing = await db.cloud_accounts.find_one({
            "user_id": user_id,
            "provider": "aws",
            "account_identifier": verify_in.account_id
        })

        if existing:
            await db.cloud_accounts.update_one(
                {"_id": existing["_id"]},
                {"$set": doc}
            )
            doc["id"] = str(existing["_id"])
        else:
            res = await db.cloud_accounts.insert_one(doc)
            doc["id"] = str(res.inserted_id)

        sanitized_config = {k: v for k, v in doc["provider_config"].items() if "secret" not in k.lower()}
        account_out = CloudAccountOutSchema(
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

        session_info = {
            "assumed_role_arn": verify_in.role_arn,
            "region": verify_in.region or "ap-south-1",
            "credential_type": "STS AssumeRole (Temporary Session)",
            "external_id": verify_in.external_id,
            "verified_at": datetime.utcnow().isoformat() + "Z"
        }

        # Step 5: Begin fetching permitted resources and billing information
        try:
            import asyncio
            from app.services.scan_service import ScanService
            asyncio.create_task(ScanService.execute_scan(db, user_id, doc["id"]))
        except Exception as scan_err:
            pass

        return {
            "status": "connected",
            "verified": True,
            "account": account_out,
            "session_info": session_info,
            "message": "AWS IAM Role verified and connected successfully via AWS STS."
        }

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
