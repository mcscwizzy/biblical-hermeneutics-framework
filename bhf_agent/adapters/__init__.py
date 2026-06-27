"""Chat adapter implementations."""

from .base import ChatAdapter, ChatAdapterError
from .openai_compatible import OpenAICompatibleAdapter

__all__ = ["ChatAdapter", "ChatAdapterError", "OpenAICompatibleAdapter"]
