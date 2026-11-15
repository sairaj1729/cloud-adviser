import asyncio
import json

import httpx

from app.api import ai_recommendations
from app.schemas.ai_recommendation import AiRecommendationRequestSchema


def build_payload():
    return AiRecommendationRequestSchema(
        recommendations=[
            {
                "id": "rec-1",
                "provider": "AWS",
                "resource_id": "resource-1",
                "resource_name": "api-worker",
                "title": "Right-size API worker",
                "problem": "Average CPU utilization is 12%.",
                "evidence": "CPU 12% over 30 days.",
                "savings": 45,
                "priority": "High",
                "confidence": 92,
                "action": "Move to a smaller instance.",
                "current_monthly_cost": 150,
            }
        ]
    )


def clear_provider_keys(monkeypatch):
    for setting in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
    ):
        monkeypatch.setattr(ai_recommendations.settings, setting, "")


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class FakeClient:
    def __init__(self, post):
        self._post = post

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        return await self._post(url, **kwargs)


def model_text():
    return json.dumps(
        {
            "recommendations": [
                {"id": "rec-1", "reason": "Low CPU utilization supports right-sizing."},
                {"id": "fabricated", "reason": "This candidate was not submitted."},
            ]
        }
    )


def openai_response():
    return FakeResponse(
        {"choices": [{"message": {"content": model_text()}}]}
    )


def test_generate_recommendations_falls_back_without_provider_keys(monkeypatch):
    clear_provider_keys(monkeypatch)

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["model"] == "Rule Engine (fallback)"
    assert result["source"] == "rule_engine"
    assert result["recommendations"][0]["id"] == "rec-1"
    assert "CPU 12% over 30 days" in result["recommendations"][0]["reason"]


def test_anthropic_success_returns_only_known_candidates(monkeypatch):
    clear_provider_keys(monkeypatch)
    monkeypatch.setattr(ai_recommendations.settings, "ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setattr(ai_recommendations.settings, "ANTHROPIC_MODEL", "claude-test")

    async def post(url, **kwargs):
        assert url == ai_recommendations.ANTHROPIC_MESSAGES_URL
        assert kwargs["headers"]["x-api-key"] == "claude-key"
        assert kwargs["json"]["model"] == "claude-test"
        return FakeResponse({"content": [{"type": "text", "text": model_text()}]})

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["model"] == "claude-test"
    assert result["source"] == "claude"
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["id"] == "rec-1"
    assert result["recommendations"][0]["reason"] == "Low CPU utilization supports right-sizing."


def test_gemini_is_used_when_claude_is_unconfigured(monkeypatch):
    clear_provider_keys(monkeypatch)
    monkeypatch.setattr(ai_recommendations.settings, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(ai_recommendations.settings, "GEMINI_MODEL", "gemini-test")

    async def post(url, **kwargs):
        assert url.endswith("/models/gemini-test:generateContent")
        assert kwargs["headers"]["x-goog-api-key"] == "gemini-key"
        return FakeResponse(
            {"candidates": [{"content": {"parts": [{"text": model_text()}]}}]}
        )

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["model"] == "gemini-test"
    assert result["source"] == "gemini"
    assert result["recommendations"][0]["id"] == "rec-1"


def test_openrouter_is_used_when_higher_priority_providers_are_unconfigured(monkeypatch):
    clear_provider_keys(monkeypatch)
    monkeypatch.setattr(ai_recommendations.settings, "OPENROUTER_API_KEY", "router-key")
    monkeypatch.setattr(ai_recommendations.settings, "OPENROUTER_MODEL", "router-test")

    async def post(url, **kwargs):
        assert url == ai_recommendations.OPENROUTER_CHAT_URL
        assert kwargs["headers"]["Authorization"] == "Bearer router-key"
        assert kwargs["json"]["model"] == "router-test"
        return openai_response()

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["model"] == "router-test"
    assert result["source"] == "openrouter"


def test_groq_is_used_when_higher_priority_providers_are_unconfigured(monkeypatch):
    clear_provider_keys(monkeypatch)
    monkeypatch.setattr(ai_recommendations.settings, "GROQ_API_KEY", "groq-key")
    monkeypatch.setattr(ai_recommendations.settings, "GROQ_MODEL", "groq-test")

    async def post(url, **kwargs):
        assert url == ai_recommendations.GROQ_CHAT_URL
        assert kwargs["headers"]["Authorization"] == "Bearer groq-key"
        assert kwargs["json"]["model"] == "groq-test"
        return openai_response()

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["model"] == "groq-test"
    assert result["source"] == "groq"


def test_failed_providers_fall_through_to_next_configured_provider(monkeypatch):
    monkeypatch.setattr(ai_recommendations.settings, "ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setattr(ai_recommendations.settings, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(ai_recommendations.settings, "OPENROUTER_API_KEY", "router-key")
    monkeypatch.setattr(ai_recommendations.settings, "GROQ_API_KEY", "groq-key")
    calls = []

    async def post(url, **_kwargs):
        calls.append(url)
        if url == ai_recommendations.GROQ_CHAT_URL:
            return openai_response()
        raise httpx.ConnectError("provider unavailable")

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["source"] == "groq"
    assert calls == [
        ai_recommendations.ANTHROPIC_MESSAGES_URL,
        ai_recommendations.GEMINI_GENERATE_URL.format(
            model=ai_recommendations.settings.GEMINI_MODEL
        ),
        ai_recommendations.OPENROUTER_CHAT_URL,
        ai_recommendations.GROQ_CHAT_URL,
    ]


def test_all_failed_providers_return_rule_engine_recommendations(monkeypatch):
    for setting in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
    ):
        monkeypatch.setattr(ai_recommendations.settings, setting, "configured-key")

    async def post(*_args, **_kwargs):
        raise httpx.ConnectError("provider unavailable")

    monkeypatch.setattr(
        ai_recommendations.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(post),
    )

    result = asyncio.run(
        ai_recommendations.generate_ai_recommendations(build_payload(), {})
    )

    assert result["source"] == "rule_engine"
    assert result["model"] == "Rule Engine (fallback)"
    assert result["recommendations"][0]["id"] == "rec-1"
