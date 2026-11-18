import json
import logging
import httpx
from typing import Dict, Any, Optional

from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI and OpenAI-compatible LLM Provider (Groq, Together AI, DeepSeek, vLLM).
    Uses /chat/completions endpoint with response_format={"type": "json_object"}.
    """
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model_name=model_name, api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
        self.endpoint = f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please set OPENAI_API_KEY in environment or .env.")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error(f"OpenAI API Error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"OpenAI API Error: {resp.status_code} - {resp.text}")

            result = resp.json()
            try:
                raw_text = result["choices"][0]["message"]["content"]
                return json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse OpenAI JSON output: {e}, Raw: {result}")
                raise ValueError(f"Invalid JSON returned from OpenAI: {e}")

