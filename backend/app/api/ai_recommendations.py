import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.ai.service import AIRecommendationService
from app.schemas.ai_recommendation import AIRecommendationResponse, AIBatchRecommendationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Recommendations"])

@router.post("/recommend/{resource_id}", response_model=AIRecommendationResponse)
async def generate_recommendation_for_resource(
    resource_id: str,
    finding_id: Optional[str] = Query(None, description="Optional associated finding ID"),
    provider: Optional[str] = Query(None, description="LLM provider override: 'gemini', 'openai', 'ollama', 'mock'"),
    model: Optional[str] = Query(None, description="LLM model override"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate or refresh an AI-enriched recommendation for a specific cloud resource.
    Extracts telemetry and findings directly from MongoDB and evaluates via Prompt Library + LLM.
    """
    service = AIRecommendationService(db)
    try:
        return await service.generate_for_resource(
            resource_id=resource_id,
            finding_id=finding_id,
            provider_override=provider,
            model_override=model
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI generation failed: {str(e)}")

@router.post("/batch-generate", response_model=AIBatchRecommendationResponse)
async def batch_generate_recommendations(
    limit: int = Query(15, ge=1, le=100),
    cloud_provider: Optional[str] = Query(None, description="Cloud provider filter: 'aws', 'azure', 'gcp'"),
    dataset_id: Optional[str] = Query(None, description="Dataset identifier filter"),
    force_refresh: bool = Query(False, description="Re-generate even if recommendation already cached"),
    provider: Optional[str] = Query(None, description="LLM provider override: 'openrouter', 'groq', 'gemini'"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Run AI recommendation analysis in batch across prioritized open Rule Engine findings in MongoDB.
    Prioritizes findings with highest potential savings.
    """
    service = AIRecommendationService(db)
    try:
        return await service.batch_generate_for_open_findings(
            cloud_provider=cloud_provider,
            dataset_id=dataset_id,
            limit=limit,
            force_refresh=force_refresh,
            provider_override=provider
        )
    except Exception as e:
        logger.error(f"Batch generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Batch generation failed: {str(e)}")

@router.get("/recommendations", response_model=List[Dict[str, Any]])
async def list_ai_recommendations(
    limit: int = Query(100, ge=1, le=200),
    provider: Optional[str] = Query(None, description="Cloud provider filter: 'aws', 'azure', 'gcp'"),
    action: Optional[str] = Query(None, description="AI action filter: 'RIGHTSIZE', 'TERMINATE', etc."),
    dataset_id: Optional[str] = Query(None, description="Dataset identifier filter"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all persisted AI recommendations from the `ai_recommendations` collection.
    """
    service = AIRecommendationService(db)
    return await service.list_recommendations(provider=provider, action=action, dataset_id=dataset_id, limit=limit)

@router.get("/recommendations/{resource_id}", response_model=Optional[Dict[str, Any]])
async def get_ai_recommendation(
    resource_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Fetch an existing AI recommendation for a specific resource from MongoDB.
    """
    rec = await db.ai_recommendations.find_one({"resource_id": resource_id})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No AI recommendation found for '{resource_id}'.")
    rec["_id"] = str(rec["_id"])
    return rec

@router.patch("/recommendations/{resource_id}/status")
async def update_recommendation_status(
    resource_id: str,
    new_status: str = Query(..., pattern="^(APPROVED|REJECTED|EXECUTED|PENDING_APPROVAL)$"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Approve, reject, or mark as executed an AI recommendation.
    """
    result = await db.ai_recommendations.update_one(
        {"resource_id": resource_id},
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource '{resource_id}' not found.")
    return {"status": "success", "resource_id": resource_id, "new_status": new_status}

