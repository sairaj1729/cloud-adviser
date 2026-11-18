import os
import logging
from typing import Optional, List, Dict, Any, Tuple

from app.core.config import settings
from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.mock import MockLLMProvider

logger = logging.getLogger(__name__)

class LLMProviderFactory:
    """
    Factory to instantiate, auto-detect, and failover across configured LLM Providers.
    Supports OpenRouter, Groq, Gemini, OpenAI, Ollama, and Mock.
    """

    @staticmethod
    def get_active_providers() -> List[BaseLLMProvider]:
        """
        Inspects environment and settings, returning all currently configured and active providers
        in priority order.
        """
        providers: List[BaseLLMProvider] = []

        # 1. OpenRouter (Multi-model access including google/gemini-2.5-flash)
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
        if openrouter_key:
            model = os.getenv("OPENROUTER_MODEL") or settings.OPENROUTER_MODEL or "google/gemini-2.5-flash"
            base_url = os.getenv("OPENROUTER_BASE_URL") or settings.OPENROUTER_BASE_URL
            providers.append(OpenRouterProvider(model_name=model, api_key=openrouter_key, base_url=base_url))

        # 2. Groq (High-speed LPU inference)
        groq_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
        if groq_key:
            model = os.getenv("GROQ_MODEL") or settings.GROQ_MODEL or "qwen/qwen3.8-27b"
            base_url = os.getenv("GROQ_BASE_URL") or settings.GROQ_BASE_URL
            providers.append(GroqProvider(model_name=model, api_key=groq_key, base_url=base_url))

        # 3. Google Gemini Direct API
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if gemini_key:
            model = os.getenv("GEMINI_MODEL") or settings.GEMINI_MODEL or "gemini-2.5-flash"
            providers.append(GeminiProvider(model_name=model, api_key=gemini_key))

        # 4. OpenAI Direct API
        openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        if openai_key:
            model = os.getenv("OPENAI_MODEL") or settings.OPENAI_MODEL or "gpt-4o-mini"
            base_url = os.getenv("OPENAI_BASE_URL") or settings.OPENAI_BASE_URL
            providers.append(OpenAIProvider(model_name=model, api_key=openai_key, base_url=base_url))

        # 5. Always include Mock as safety fallback
        providers.append(MockLLMProvider())

        return providers

    @classmethod
    def get_provider(
        cls,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Instantiate a specific provider by name or auto-select the highest priority active provider.
        """
        resolved_provider = (
            provider_name or 
            os.getenv("LLM_PROVIDER") or 
            settings.LLM_PROVIDER or 
            "auto"
        ).lower()

        # If 'auto', select the first active provider with an available API key
        if resolved_provider == "auto":
            active_list = cls.get_active_providers()
            chosen = active_list[0]
            logger.info(f"Auto-selected active LLM provider: {chosen.provider_name} ({chosen.model_name})")
            return chosen

        resolved_model = model_name or os.getenv("LLM_MODEL") or settings.LLM_MODEL

        if resolved_provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
            model = resolved_model or os.getenv("OPENROUTER_MODEL") or settings.OPENROUTER_MODEL or "google/gemini-2.5-flash"
            base_url = os.getenv("OPENROUTER_BASE_URL") or settings.OPENROUTER_BASE_URL
            if not key:
                logger.warning("OPENROUTER_API_KEY is not set. Falling back to Mock.")
                return MockLLMProvider()
            return OpenRouterProvider(model_name=model, api_key=key, base_url=base_url)

        elif resolved_provider == "groq":
            key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
            model = resolved_model or os.getenv("GROQ_MODEL") or settings.GROQ_MODEL or "qwen/qwen3.8-27b"
            base_url = os.getenv("GROQ_BASE_URL") or settings.GROQ_BASE_URL
            if not key:
                logger.warning("GROQ_API_KEY is not set. Falling back to Mock.")
                return MockLLMProvider()
            return GroqProvider(model_name=model, api_key=key, base_url=base_url)

        elif resolved_provider == "gemini":
            key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
            model = resolved_model or os.getenv("GEMINI_MODEL") or settings.GEMINI_MODEL or "gemini-2.5-flash"
            if not key:
                logger.warning("GEMINI_API_KEY is not set. Falling back to Mock.")
                return MockLLMProvider()
            return GeminiProvider(model_name=model, api_key=key)

        elif resolved_provider in ["openai", "together", "deepseek"]:
            key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            base_url = os.getenv("OPENAI_BASE_URL") or settings.OPENAI_BASE_URL
            model = resolved_model or os.getenv("OPENAI_MODEL") or settings.OPENAI_MODEL or "gpt-4o-mini"
            if not key:
                logger.warning("OPENAI_API_KEY is not set. Falling back to Mock.")
                return MockLLMProvider()
            return OpenAIProvider(model_name=model, api_key=key, base_url=base_url)

        elif resolved_provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL") or settings.OLLAMA_BASE_URL
            model = resolved_model or os.getenv("OLLAMA_MODEL") or settings.OLLAMA_MODEL or "llama3.2"
            return OllamaProvider(model_name=model, base_url=base_url)

        elif resolved_provider == "mock":
            return MockLLMProvider(model_name=resolved_model or "mock-finops-v1")

        else:
            logger.warning(f"Unknown provider '{resolved_provider}'. Defaulting to auto-selection.")
            return cls.get_active_providers()[0]

    @classmethod
    async def generate_with_failover(
        cls,
        prompt: str,
        system_instruction: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[Dict[str, Any], BaseLLMProvider]:
        """
        Executes prompt across active providers with automatic failover.
        If preferred provider fails (e.g. rate limit, quota, network error),
        it seamlessly tries the next active provider in the chain.
        """
        # Determine candidate list
        candidate_providers: List[BaseLLMProvider] = []
        if preferred_provider and preferred_provider.lower() != "auto":
            try:
                candidate_providers.append(cls.get_provider(preferred_provider, preferred_model))
            except Exception as e:
                logger.warning(f"Failed to initialize preferred provider '{preferred_provider}': {e}")

        # Add remaining active providers as fallbacks
        for active in cls.get_active_providers():
            if not any(cp.provider_name == active.provider_name for cp in candidate_providers):
                candidate_providers.append(active)

        last_error = None
        for provider in candidate_providers:
            try:
                logger.info(f"Attempting recommendation generation with: {provider.provider_name} ({provider.model_name})")
                result = await provider.generate_json(prompt, system_instruction)
                logger.info(f"Successfully generated recommendation via: {provider.provider_name} ({provider.model_name})")
                return result, provider
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed: {e}. Trying next active fallback provider...")
                last_error = e

        # Final safety fallback to Mock
        mock_provider = MockLLMProvider()
        logger.warning(f"All active providers exhausted. Falling back to Mock provider. Last error: {last_error}")
        result = await mock_provider.generate_json(prompt, system_instruction)
        return result, mock_provider
