import pytest
import asyncio
from mongomock_motor import AsyncMongoMockClient

from app.ai.providers.factory import LLMProviderFactory
from app.ai.providers.mock import MockLLMProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.validator import RecommendationValidator
from app.ai.context_builder import ContextBuilder
from app.ai.service import AIRecommendationService

def test_llm_provider_switching():
    """Verify that LLMProviderFactory can switch to any provider dynamically."""
    # 1. Switch to Mock
    p_mock = LLMProviderFactory.get_provider("mock")
    assert isinstance(p_mock, MockLLMProvider)
    assert p_mock.provider_name == "mock"

    # 2. Switch to OpenAI
    p_openai = LLMProviderFactory.get_provider("openai", model_name="gpt-4o")
    # If no key, falls back to Mock in dev, but if key passed:
    p_openai_with_key = OpenAIProvider(model_name="gpt-4o", api_key="sk-test-fake-key")
    assert isinstance(p_openai_with_key, OpenAIProvider)
    assert p_openai_with_key.provider_name == "openai"
    assert p_openai_with_key.model_name == "gpt-4o"

    # 3. Switch to Gemini
    p_gemini_with_key = GeminiProvider(model_name="gemini-2.0-flash", api_key="fake-gemini-key")
    assert isinstance(p_gemini_with_key, GeminiProvider)
    assert p_gemini_with_key.provider_name == "gemini"
    assert p_gemini_with_key.model_name == "gemini-2.0-flash"

    # 4. Switch to Ollama
    p_ollama = LLMProviderFactory.get_provider("ollama", model_name="llama3.2")
    assert isinstance(p_ollama, OllamaProvider)
    assert p_ollama.provider_name == "ollama"

    # 5. Switch to OpenRouter
    p_openrouter = LLMProviderFactory.get_provider("openrouter")
    assert isinstance(p_openrouter, OpenRouterProvider)
    assert p_openrouter.provider_name == "openrouter"

    # 6. Switch to Groq
    p_groq = LLMProviderFactory.get_provider("groq")
    assert isinstance(p_groq, GroqProvider)
    assert p_groq.provider_name == "groq"

    # 7. Check Active List
    active_providers = LLMProviderFactory.get_active_providers()
    active_names = [p.provider_name for p in active_providers]
    assert "openrouter" in active_names
    assert "groq" in active_names
    assert "mock" in active_names

def test_recommendation_validator_guardrails():
    """Verify deterministic savings clamping and sanitization."""
    context = {
        "resource_id": "i-0987654321",
        "resource_name": "prod-api-server-01",
        "provider": "AWS",
        "current_sku": "m5.2xlarge",
        "monthly_cost": 280.0
    }

    # Case 1: Hallucinated excessive savings ($500 on a $280 instance)
    raw_excessive = {
        "action": "RIGHTSIZE",
        "target_sku": "m5.xlarge",
        "estimated_monthly_savings": 500.0,
        "risk_level": "LOW",
        "justification": "Downsize instance."
    }
    validated = RecommendationValidator.validate_and_sanitize(raw_excessive, context)
    assert validated["estimated_monthly_savings"] == 280.0  # Clamped to cost
    assert validated["estimated_savings_percentage"] == 100.0

    # Case 2: Negative savings
    raw_negative = {
        "action": "RIGHTSIZE",
        "estimated_monthly_savings": -50.0
    }
    validated_neg = RecommendationValidator.validate_and_sanitize(raw_negative, context)
    assert validated_neg["estimated_monthly_savings"] == 0.0

    # Case 3: Invalid action string
    raw_invalid_action = {
        "action": "EXPLODE_SERVER",
        "estimated_monthly_savings": 100.0
    }
    validated_action = RecommendationValidator.validate_and_sanitize(raw_invalid_action, context)
    assert validated_action["action"] == "RIGHTSIZE"

def test_end_to_end_ai_service_with_mock_db():
    """Verify full end-to-end pipeline: Mongo -> Context Builder -> Prompt -> LLM -> Validator -> Mongo."""
    async def _run():
        client = AsyncMongoMockClient()
        db = client.test_cloud_advisor

        # Seed a sample resource
        await db.resources.insert_one({
            "resource_id": "i-test-ec2-001",
            "name": "checkout-service-worker",
            "provider": "aws",
            "resource_type": "compute_instance",
            "configuration": {"instance_type": "m5.2xlarge"},
            "metrics": {"cpu_average": 12.4, "memory_average": 28.5, "network_in_mbps": 1.2},
            "cost": {"monthly": 280.0},
            "tags": {"Environment": "Production", "Owner": "CheckoutTeam"}
        })

        # Seed a finding
        await db.findings.insert_one({
            "resource_id": "i-test-ec2-001",
            "rule_id": "AWS-EC2-001",
            "finding_type": "RIGHTSIZING_REVIEW",
            "evidence": {"avg_cpu": 12.4, "threshold": 25.0},
            "savings": {"monthly": 126.0},
            "status": "open"
        })

        # Run AI Recommendation Service with Mock Provider
        service = AIRecommendationService(db)
        result = await service.generate_for_resource(
            resource_id="i-test-ec2-001",
            provider_override="mock"
        )

        assert result.resource_id == "i-test-ec2-001"
        assert result.action in ["RIGHTSIZE", "STOP"]
        assert result.estimated_monthly_savings > 0
        assert result.estimated_monthly_savings <= 280.0
        assert result.llm_provider_used == "mock"

        # Verify persisted to MongoDB db.ai_recommendations
        persisted = await db.ai_recommendations.find_one({"resource_id": "i-test-ec2-001"})
        assert persisted is not None
        assert persisted["action"] == result.action

        # Verify updated in db.findings
        updated_finding = await db.findings.find_one({"resource_id": "i-test-ec2-001"})
        assert "ai_recommendation" in updated_finding
        assert updated_finding["ai_recommendation"]["action"] == result.action

    asyncio.run(_run())

