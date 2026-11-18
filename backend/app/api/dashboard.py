from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List, Optional

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard"])

class SwitchDatasetPayload(BaseModel):
    dataset_id: str

@router.get("/datasets", response_model=List[Dict[str, Any]])
async def list_datasets(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List available multi-cloud synthetic datasets with item count, domain, and active status."""
    return await DatasetService.list_datasets_with_status(db, current_user["id"])

@router.post("/datasets/switch", response_model=Dict[str, Any])
async def switch_dataset(
    payload: SwitchDatasetPayload,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Switch active dataset:
    1. Records active dataset choice in MongoDB.
    2. Seeds resources into db.resources if not already seeded.
    3. Evaluates Rule Engine on the dataset and persists findings in db.findings.
    4. Returns updated dashboard analytics for this dataset.
    """
    dataset_id = payload.dataset_id
    await DatasetService.set_active_dataset_id(db, current_user["id"], dataset_id)
    await DatasetService.ensure_dataset_seeded(db, dataset_id, current_user["id"])
    return await AnalyticsService.get_dashboard_analytics(db, current_user["id"], refresh=False, dataset_id=dataset_id)

@router.get("/analytics", response_model=Dict[str, Any])
async def get_dashboard_analytics(
    refresh: bool = Query(True, description="Re-evaluate active rules from db.rules and persist findings in db.findings"),
    dataset: Optional[str] = Query(None, description="bank_balanced, retail_balanced, or retail_2900"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Returns full multi-cloud dataset & analytics generated directly from MongoDB resources & findings:
    - providerMeta (AWS, Azure, GCP spend, service counts, averages)
    - services (top services with monthly trends & percentage shares)
    - unused (potentially unused services requiring review)
    - resources (low-utilization resources with rightsizing opportunities)
    - recommendations (prioritized optimization opportunities with evidence)
    - trend (12-month spend curves)
    """
    return await AnalyticsService.get_dashboard_analytics(db, current_user["id"], refresh=refresh, dataset_id=dataset)

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_dashboard_analytics(
    dataset: Optional[str] = Query(None, description="bank_balanced, retail_balanced, or retail_2900"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Explicitly regenerate findings from MongoDB rules, store in DB, and return fresh dataset."""
    return await AnalyticsService.get_dashboard_analytics(db, current_user["id"], refresh=True, dataset_id=dataset)

@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    dataset: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Returns executive summary metrics filtered for the active dataset:
    - total_cloud_accounts
    - total_resources
    - total_findings
    - open_findings
    - high_severity_findings
    - total_monthly_cost
    - estimated_monthly_savings
    - estimated_annual_savings
    - savings_by_provider
    - cost_by_provider
    - top_services
    - recent_findings
    """
    user_id = current_user["id"]
    active_dataset_id = dataset or await DatasetService.get_active_dataset_id(db, user_id)

    res_match: Dict[str, Any] = {"user_id": user_id, "dataset_id": active_dataset_id}
    if await db.resources.count_documents(res_match) == 0:
        res_match = {"dataset_id": active_dataset_id}

    find_match: Dict[str, Any] = {"user_id": user_id, "dataset_id": active_dataset_id}
    if await db.findings.count_documents(find_match) == 0:
        find_match = {"dataset_id": active_dataset_id}

    total_accounts = await db.cloud_accounts.count_documents({"user_id": user_id})
    total_resources = await db.resources.count_documents(res_match)
    total_findings = await db.findings.count_documents(find_match)
    open_findings = await db.findings.count_documents({**find_match, "status": "open"})
    high_severity = await db.findings.count_documents({**find_match, "severity": "high", "status": "open"})

    # 1. Aggregate Savings by Provider
    savings_pipeline = [
        {"$match": {**find_match, "status": "open"}},
        {"$group": {
            "_id": "$provider",
            "provider_monthly": {"$sum": "$savings.monthly"}
        }}
    ]

    savings_by_provider = {"aws": 0.0, "azure": 0.0, "gcp": 0.0}
    total_monthly_savings = 0.0

    async for doc in db.findings.aggregate(savings_pipeline):
        provider = str(doc.get("_id", "")).lower()
        amount = round(float(doc.get("provider_monthly", 0.0)), 2)
        if provider in savings_by_provider:
            savings_by_provider[provider] = amount
        total_monthly_savings += amount

    total_annual_savings = round(total_monthly_savings * 12.0, 2)

    # 2. Aggregate Resource Costs by Provider
    cost_pipeline = [
        {"$match": res_match},
        {"$group": {
            "_id": "$provider",
            "monthly_cost": {"$sum": "$cost.monthly"}
        }}
    ]

    cost_by_provider = {"aws": 0.0, "azure": 0.0, "gcp": 0.0}
    total_monthly_cost = 0.0

    async for doc in db.resources.aggregate(cost_pipeline):
        provider = str(doc.get("_id", "")).lower()
        amount = round(float(doc.get("monthly_cost", 0.0)), 2)
        if provider in cost_by_provider:
            cost_by_provider[provider] = amount
        total_monthly_cost += amount

    # 3. Top Services Spend
    services_pipeline = [
        {"$match": res_match},
        {"$group": {
            "_id": "$resource_type",
            "cost": {"$sum": "$cost.monthly"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"cost": -1}},
        {"$limit": 5}
    ]
    top_services = []
    async for s in db.resources.aggregate(services_pipeline):
        top_services.append({
            "name": s["_id"],
            "cost": round(float(s.get("cost", 0.0)), 2),
            "count": s.get("count", 0)
        })

    # 4. Recent findings snippet
    recent_cursor = db.findings.find({**find_match, "status": "open"}).sort("created_at", -1).limit(5)
    recent_findings = []
    async for f in recent_cursor:
        recent_findings.append({
            "id": str(f["_id"]),
            "rule_id": f.get("rule_id"),
            "provider": f.get("provider"),
            "resource_name": f.get("resource_name"),
            "severity": f.get("severity"),
            "savings_monthly": f.get("savings", {}).get("monthly", 0.0)
        })

    return {
        "active_dataset_id": active_dataset_id,
        "total_cloud_accounts": total_accounts,
        "total_resources": total_resources,
        "total_findings": total_findings,
        "open_findings": open_findings,
        "high_severity_findings": high_severity,
        "total_monthly_cost": round(total_monthly_cost, 2),
        "estimated_monthly_savings": round(total_monthly_savings, 2),
        "estimated_annual_savings": total_annual_savings,
        "savings_by_provider": savings_by_provider,
        "cost_by_provider": cost_by_provider,
        "top_services": top_services,
        "recent_findings": recent_findings
    }
