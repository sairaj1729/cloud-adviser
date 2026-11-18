import json
import logging
import httpx
from typing import Dict, Any, Optional

from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM Provider using direct REST API.
    Supports native JSON output schema.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None, base_url: Optional[str] = None):
        clean_model = (model_name or "gemini-2.5-flash").replace("models/", "")
        super().__init__(model_name=clean_model, api_key=api_key, base_url=base_url)
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please set GEMINI_API_KEY in environment or .env.")

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self.api_url,
                params={"key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code != 200:
                logger.error(f"Gemini API returned error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Gemini API Error: {resp.status_code} - {resp.text}")

            result = resp.json()
            try:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Gemini JSON output: {e}, Raw: {result}")
                raise ValueError(f"Invalid JSON returned from Gemini: {e}")

