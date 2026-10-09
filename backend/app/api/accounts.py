from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user
from app.schemas.account import CloudAccountCreateSchema, CloudAccountOutSchema, ScanSummarySchema
from app.services.account_service import AccountService
from app.services.scan_service import ScanService
from app.providers.factory import ProviderFactory

router = APIRouter(prefix="/accounts", tags=["Cloud Accounts"])

@router.get("", response_model=List[CloudAccountOutSchema])
async def list_accounts(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List connected cloud accounts for the current user."""
    return await AccountService.list_accounts(db, current_user["id"])

@router.post("", response_model=CloudAccountOutSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    acc_in: CloudAccountCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Connect a new cloud account (AWS AssumeRole, Azure, or GCP)."""
    return await AccountService.create_account(db, current_user["id"], acc_in)

@router.get("/{account_id}", response_model=CloudAccountOutSchema)
async def get_account_detail(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get cloud account connection details."""
    try:
        acc = await db.cloud_accounts.find_one({
            "_id": ObjectId(account_id),
            "user_id": current_user["id"]
        })
    except Exception:
        acc = await db.cloud_accounts.find_one({
            "_id": account_id,
            "user_id": current_user["id"]
        })

    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    sanitized_config = {k: v for k, v in acc.get("provider_config", {}).items() if "secret" not in k.lower()}
    return CloudAccountOutSchema(
        id=str(acc["_id"]),
        user_id=current_user["id"],
        provider=acc["provider"],
        display_name=acc["display_name"],
        status=acc["status"],
        account_identifier=acc["account_identifier"],
        region=acc.get("region", "us-east-1"),
        credential_type=acc["credential_type"],
        provider_config=sanitized_config,
        last_verified_at=acc.get("last_verified_at"),
        created_at=acc.get("created_at"),
        updated_at=acc.get("updated_at")
    )

@router.post("/{account_id}/verify")
async def verify_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Verify credentials & permissions for a cloud account."""
    try:
        acc = await db.cloud_accounts.find_one({
            "_id": ObjectId(account_id),
            "user_id": current_user["id"]
        })
    except Exception:
        acc = await db.cloud_accounts.find_one({
            "_id": account_id,
            "user_id": current_user["id"]
        })

    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    connector = ProviderFactory.get_connector(acc)
    verified = await connector.verify_connection()
    new_status = "connected" if verified else "error"

    await db.cloud_accounts.update_one(
        {"_id": acc["_id"]},
        {"$set": {"status": new_status, "last_verified_at": datetime.utcnow()}}
    )

    return {"status": new_status, "verified": verified}

@router.post("/{account_id}/scan", response_model=ScanSummarySchema)
async def scan_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Synchronously scan account resources, normalize data, and run Rule Engine."""
    return await ScanService.execute_scan(db, current_user["id"], account_id)

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Disconnect and remove a cloud account."""
    try:
        res = await db.cloud_accounts.delete_one({
            "_id": ObjectId(account_id),
            "user_id": current_user["id"]
        })
    except Exception:
        res = await db.cloud_accounts.delete_one({
            "_id": account_id,
            "user_id": current_user["id"]
        })

    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
