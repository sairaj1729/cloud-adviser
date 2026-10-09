from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard"])

@router.get("/analytics", response_model=Dict[str, Any])
async def get_dashboard_analytics(
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
    return await AnalyticsService.get_dashboard_analytics(db, current_user["id"])

@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Returns executive summary metrics:
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

    total_accounts = await db.cloud_accounts.count_documents({"user_id": user_id})
    total_resources = await db.resources.count_documents({"user_id": user_id})
    total_findings = await db.findings.count_documents({"user_id": user_id})
    open_findings = await db.findings.count_documents({"user_id": user_id, "status": "open"})
    high_severity = await db.findings.count_documents({"user_id": user_id, "severity": "high", "status": "open"})

    # 1. Aggregate Savings by Provider
    savings_pipeline = [
        {"$match": {"user_id": user_id, "status": "open"}},
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
        {"$match": {"user_id": user_id}},
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
        {"$match": {"user_id": user_id}},
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
    recent_cursor = db.findings.find({"user_id": user_id, "status": "open"}).sort("created_at", -1).limit(5)
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
