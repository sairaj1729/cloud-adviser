from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any

from app.db.mongodb import get_database
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard"])

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
    - estimated_monthly_savings
    - estimated_annual_savings
    - savings_by_provider
    """
    user_id = current_user["id"]

    total_accounts = await db.cloud_accounts.count_documents({"user_id": user_id})
    total_resources = await db.resources.count_documents({"user_id": user_id})
    total_findings = await db.findings.count_documents({"user_id": user_id})
    open_findings = await db.findings.count_documents({"user_id": user_id, "status": "open"})
    high_severity = await db.findings.count_documents({"user_id": user_id, "severity": "high", "status": "open"})

    # Aggregate Savings
    pipeline = [
        {"$match": {"user_id": user_id, "status": "open"}},
        {"$group": {
            "_id": "$provider",
            "provider_monthly": {"$sum": "$savings.monthly"}
        }}
    ]

    savings_by_provider = {"aws": 0.0, "azure": 0.0, "gcp": 0.0}
    total_monthly_savings = 0.0

    async for doc in db.findings.aggregate(pipeline):
        provider = doc["_id"].lower()
        amount = round(float(doc.get("provider_monthly", 0.0)), 2)
        savings_by_provider[provider] = amount
        total_monthly_savings += amount

    total_annual_savings = round(total_monthly_savings * 12.0, 2)

    return {
        "total_cloud_accounts": total_accounts,
        "total_resources": total_resources,
        "total_findings": total_findings,
        "open_findings": open_findings,
        "high_severity_findings": high_severity,
        "estimated_monthly_savings": round(total_monthly_savings, 2),
        "estimated_annual_savings": total_annual_savings,
        "savings_by_provider": savings_by_provider
    }
