"""Chat adapter implementations."""

from .base import ChatAdapter, ChatAdapterError
from .factory import build_chat_adapter
from .openai_compatible import OpenAICompatibleAdapter
from .openrouter import OpenRouterAdapter
from .ollama import OllamaAdapter

__all__ = [
    "ChatAdapter",
    "ChatAdapterError",
    "build_chat_adapter",
    "OpenAICompatibleAdapter",
    "OpenRouterAdapter",
    "OllamaAdapter",
]
