import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.context_builder import ContextBuilder
from app.ai.validator import RecommendationValidator
from app.ai.providers.factory import LLMProviderFactory
from app.ai.prompt_library.base import SYSTEM_FINOPS_INSTRUCTION
from app.schemas.ai_recommendation import AIRecommendationResponse, AIBatchRecommendationResponse

logger = logging.getLogger(__name__)

class AIRecommendationService:
    """
    Core AI Recommendation Orchestration Service.
    Connects Context Builder, Pluggable LLM Provider, Validator, and MongoDB storage.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.context_builder = ContextBuilder(db)

    async def generate_for_resource(
        self,
        resource_id: str,
        finding_id: Optional[str] = None,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> AIRecommendationResponse:
        # 1. Build Context and Hydrate Prompt from Prompt Library
        prompt, context_data = await self.context_builder.build_context(
            resource_id=resource_id,
            finding_id=finding_id
        )

        # 2. Call LLM with Automatic Active Provider Selection & Failover
        raw_output, llm = await LLMProviderFactory.generate_with_failover(
            prompt=prompt,
            system_instruction=SYSTEM_FINOPS_INSTRUCTION,
            preferred_provider=provider_override,
            preferred_model=model_override
        )

        # 4. Enforce Deterministic Guardrails
        validated = RecommendationValidator.validate_and_sanitize(raw_output, context_data)
        validated["dataset_id"] = context_data.get("dataset_id")
        validated["llm_provider_used"] = llm.provider_name
        validated["llm_model_used"] = llm.model_name
        validated["created_at"] = datetime.now(timezone.utc)
        validated["status"] = "PENDING_APPROVAL"

        # 5. Persist to MongoDB (both dedicated collection and embedded into findings)
        await self.db.ai_recommendations.update_one(
            {"resource_id": resource_id},
            {"$set": validated},
            upsert=True
        )

        # Also update all finding records for this resource
        await self.db.findings.update_many(
            {"resource_id": resource_id},
            {"$set": {"ai_recommendation": validated, "updated_at": datetime.now(timezone.utc)}}
        )

        return AIRecommendationResponse(**validated)

    async def batch_generate_for_open_findings(
        self,
        user_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        limit: int = 15,
        force_refresh: bool = False,
        provider_override: Optional[str] = None
    ) -> AIBatchRecommendationResponse:
        """
        Runs AI recommendation generation across prioritized open findings.
        Prioritizes highest-savings findings first, leverages parallel async execution,
        and reuses cached recommendations to ensure fast response times.
        """
        import asyncio

        query: Dict[str, Any] = {"status": {"$in": ["open", "pending", "ACTIVE"]}}
        if user_id:
            query["user_id"] = user_id
        if dataset_id:
            query["dataset_id"] = dataset_id
        if cloud_provider and cloud_provider.lower() not in ["all", ""]:
            query["provider"] = cloud_provider.lower()

        # Sort by savings.monthly descending and deduplicate by resource_id so distinct resources are analyzed
        cursor = self.db.findings.find(query).sort("savings.monthly", -1).limit(limit * 3)
        candidates = await cursor.to_list(length=limit * 3)

        seen_res = set()
        findings: List[Dict[str, Any]] = []
        for f in candidates:
            res_id = f.get("resource_id")
            if not res_id or res_id in seen_res:
                continue
            seen_res.add(res_id)
            findings.append(f)
            if len(findings) >= limit:
                break

        # Pre-fetch existing ai_recommendations to avoid redundant LLM calls if not forced
        ai_cached_by_res: Dict[str, Any] = {}
        if not force_refresh:
            try:
                res_ids = [f.get("resource_id") for f in findings if f.get("resource_id")]
                if res_ids:
                    cached_docs = await self.db.ai_recommendations.find({"resource_id": {"$in": res_ids}}).to_list(length=len(res_ids))
                    for c in cached_docs:
                        c["_id"] = str(c.get("_id", ""))
                        ai_cached_by_res[c["resource_id"]] = c
            except Exception as e:
                logger.debug(f"Cache check skipped: {e}")

        sem = asyncio.Semaphore(3)

        async def _process_finding(f: Dict[str, Any]) -> Optional[AIRecommendationResponse]:
            res_id = f.get("resource_id")
            if not res_id:
                return None

            # Check cache in finding or in db.ai_recommendations
            if not force_refresh:
                cached = f.get("ai_recommendation") or ai_cached_by_res.get(res_id)
                if cached and isinstance(cached, dict):
                    try:
                        cached_rec = dict(cached)
                        cached_rec["resource_id"] = res_id
                        if f.get("dataset_id") and not cached_rec.get("dataset_id"):
                            cached_rec["dataset_id"] = f.get("dataset_id")
                        if not cached_rec.get("provider"):
                            cached_rec["provider"] = f.get("provider", "AWS").upper()
                        else:
                            cached_rec["provider"] = str(cached_rec["provider"]).upper()
                        if not cached_rec.get("status"):
                            cached_rec["status"] = "PENDING_APPROVAL"
                        if not cached_rec.get("resource_type"):
                            cached_rec["resource_type"] = f.get("resource_type", "compute_instance")
                        if not cached_rec.get("service") or not cached_rec.get("category"):
                            from app.services.analytics_service import get_service_name, get_category_name
                            cached_rec["service"] = get_service_name(cached_rec["resource_type"], cached_rec["provider"])
                            cached_rec["category"] = get_category_name(cached_rec["resource_type"])

                        # Ensure cached recommendation is persisted in db.ai_recommendations!
                        await self.db.ai_recommendations.update_one(
                            {"resource_id": res_id},
                            {"$set": cached_rec},
                            upsert=True
                        )
                        return AIRecommendationResponse(**cached_rec)
                    except Exception as e:
                        logger.warning(f"Error restoring cached recommendation for {res_id}: {e}")

            async with sem:
                try:
                    return await self.generate_for_resource(
                        resource_id=res_id,
                        finding_id=str(f.get("_id", "")),
                        provider_override=provider_override
                    )
                except Exception as e:
                    logger.error(f"Error generating AI recommendation for resource {res_id}: {e}")
                    return None

        tasks = [_process_finding(f) for f in findings]
        raw_results = await asyncio.gather(*tasks)

        results: List[AIRecommendationResponse] = [r for r in raw_results if r is not None]
        total_savings = sum(r.estimated_monthly_savings for r in results)

        return AIBatchRecommendationResponse(
            total_findings_analyzed=len(findings),
            recommendations_generated=len(results),
            total_estimated_monthly_savings=round(total_savings, 2),
            items=results
        )

    async def sync_findings_to_recommendations(self):
        """Ensure open findings with embedded ai_recommendation are synced into ai_recommendations collection."""
        try:
            cursor = self.db.findings.find({"ai_recommendation": {"$exists": True, "$ne": None}})
            findings = await cursor.to_list(length=500)
            for f in findings:
                rec = f.get("ai_recommendation")
                if not rec or not isinstance(rec, dict):
                    continue
                res_id = f.get("resource_id") or rec.get("resource_id")
                if not res_id:
                    continue
                rec_to_save = dict(rec)
                rec_to_save["resource_id"] = res_id
                if f.get("dataset_id") and not rec_to_save.get("dataset_id"):
                    rec_to_save["dataset_id"] = f.get("dataset_id")
                rec_to_save["provider"] = str(rec_to_save.get("provider") or f.get("provider", "AWS")).upper()
                if not rec_to_save.get("status"):
                    rec_to_save["status"] = "PENDING_APPROVAL"
                if not rec_to_save.get("resource_name"):
                    rec_to_save["resource_name"] = f.get("resource_name", res_id)
                if not rec_to_save.get("service") or not rec_to_save.get("category"):
                    from app.services.analytics_service import get_service_name, get_category_name
                    rtype = rec_to_save.get("resource_type") or f.get("resource_type", "compute_instance")
                    rec_to_save["resource_type"] = rtype
                    rec_to_save["service"] = get_service_name(rtype, rec_to_save["provider"])
                    rec_to_save["category"] = get_category_name(rtype)
                await self.db.ai_recommendations.update_one(
                    {"resource_id": res_id},
                    {"$set": rec_to_save},
                    upsert=True
                )
        except Exception as e:
            logger.warning(f"Findings to ai_recommendations sync failed: {e}")

    async def list_recommendations(
        self,
        provider: Optional[str] = None,
        action: Optional[str] = None,
        dataset_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List stored AI recommendations from MongoDB, sorted by highest potential savings."""
        query: Dict[str, Any] = {}
        if provider and provider.lower() not in ["all", ""]:
            query["provider"] = {"$regex": f"^{provider}$", "$options": "i"}
        if action and action.lower() not in ["all", ""]:
            query["action"] = action.upper()
        if dataset_id and dataset_id.lower() not in ["all", ""]:
            query["$or"] = [
                {"dataset_id": dataset_id},
                {"dataset_id": {"$exists": False}},
                {"dataset_id": None}
            ]

        cursor = self.db.ai_recommendations.find(query).sort("estimated_monthly_savings", -1).limit(limit)
        records = await cursor.to_list(length=limit)

        # If zero records found and filtering by provider, sync from findings and re-query
        if len(records) == 0:
            await self.sync_findings_to_recommendations()
            cursor = self.db.ai_recommendations.find(query).sort("estimated_monthly_savings", -1).limit(limit)
            records = await cursor.to_list(length=limit)

        for r in records:
            r["_id"] = str(r["_id"])
            if not r.get("service") or not r.get("category"):
                from app.services.analytics_service import get_service_name, get_category_name
                rtype = r.get("resource_type") or "compute_instance"
                prov = str(r.get("provider") or "AWS").upper()
                if not r.get("service"):
                    r["service"] = get_service_name(rtype, prov)
                if not r.get("category"):
                    r["category"] = get_category_name(rtype)
        return records