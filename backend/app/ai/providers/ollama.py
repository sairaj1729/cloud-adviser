import json
import logging
import httpx
from typing import Dict, Any, Optional

from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """
    Local Ollama Provider (for local open-source models like Llama 3, Mistral, Qwen).
    Runs completely offline on localhost.
    """
    def __init__(self, model_name: str = "llama3.2", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model_name=model_name, api_key=api_key, base_url=base_url or "http://localhost:11434")
        self.endpoint = f"{self.base_url.rstrip('/')}/api/chat"

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.endpoint, json=payload)
            if resp.status_code != 200:
                logger.error(f"Ollama API Error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Ollama API Error: {resp.status_code} - {resp.text}")

            result = resp.json()
            try:
                raw_text = result["message"]["content"]
                return json.loads(raw_text)
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Ollama JSON output: {e}, Raw: {result}")
                raise ValueError(f"Invalid JSON returned from Ollama: {e}")

