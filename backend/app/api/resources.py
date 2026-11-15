from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user
from app.schemas.resource import NormalizedResourceSchema

router = APIRouter(prefix="/resources", tags=["Normalized Resources"])

@router.get("", response_model=List[NormalizedResourceSchema])
async def list_resources(
    provider: Optional[str] = Query(None, description="aws, azure, gcp"),
    resource_type: Optional[str] = Query(None, description="compute_instance, storage_bucket, etc."),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List normalized resources for the authenticated user."""
    query = {"user_id": current_user["id"]}
    if provider:
        query["provider"] = provider.lower()
    if resource_type:
        query["resource_type"] = resource_type

    cursor = db.resources.find(query)
    resources = await cursor.to_list(length=500)
    out = []
    for r in resources:
        r["id"] = str(r["_id"])
        out.append(NormalizedResourceSchema(**r))
    return out
