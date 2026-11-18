import json
import logging
import httpx
from typing import Dict, Any, Optional

from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class GroqProvider(BaseLLMProvider):
    """
    Groq High-Speed LPUs Inference Provider.
    Ultra-low latency inference using OpenAI-compatible chat completions API.
    """
    def __init__(
        self,
        model_name: str = "qwen/qwen3.8-27b",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.groq.com/openai/v1"
        )
        self.endpoint = f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set.")

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
                logger.error(f"Groq API Error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Groq API Error {resp.status_code}: {resp.text}")

            result = resp.json()
            try:
                raw_text = result["choices"][0]["message"]["content"]
                return json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Groq JSON output: {e}, Raw: {result}")
                raise ValueError(f"Invalid JSON returned from Groq: {e}")
