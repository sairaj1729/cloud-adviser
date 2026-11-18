import abc
from typing import Dict, Any, Optional

class BaseLLMProvider(abc.ABC):
    """
    Abstract Base Class for all LLM Providers.
    Any provider (Gemini, OpenAI, Ollama, Anthropic, etc.) must implement `generate_json`.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url

    @abc.abstractmethod
    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends prompt to LLM and returns parsed JSON dictionary.
        Must raise an exception or handle errors gracefully if JSON cannot be parsed.
        """
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the provider (e.g. 'gemini', 'openai', 'ollama')."""
        pass

