from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user
from app.schemas.rule import RuleSchema
from app.rule_engine.registry import RuleRegistry

router = APIRouter(prefix="/rules", tags=["Rule Registry"])

@router.get("", response_model=List[RuleSchema])
async def list_rules(
    provider: Optional[str] = Query(None, description="aws, azure, gcp"),
    resource_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List data-driven rules from the Rule Registry."""
    await RuleRegistry.seed_rules(db)

    query = {}
    if provider:
        query["provider"] = provider.lower()
    if resource_type:
        query["resource_type"] = resource_type
    if severity:
        query["severity"] = severity
    if status_filter:
        query["status"] = status_filter

    cursor = db.rules.find(query)
    rules = await cursor.to_list(length=200)
    return [RuleSchema(**r) for r in rules]

@router.get("/{rule_id}", response_model=RuleSchema)
async def get_rule_by_id(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Fetch rule definition by rule_id."""
    rule = await db.rules.find_one({"rule_id": rule_id})
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return RuleSchema(**rule)
