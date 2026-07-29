"""Chat adapter implementations."""

from .base import ChatAdapter, ChatAdapterError
from .openai_compatible import OpenAICompatibleAdapter
from .openrouter import OpenRouterAdapter
from .ollama import OllamaAdapter

__all__ = [
    "ChatAdapter",
    "ChatAdapterError",
    "OpenAICompatibleAdapter",
    "OpenRouterAdapter",
    "OllamaAdapter",
]
