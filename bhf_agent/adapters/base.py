"""Adapter interface for local and future model runtimes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from bhf_agent.models import ChatRequest, ChatResponse


class ChatAdapterError(RuntimeError):
    """Raised for adapter construction/configuration errors."""


class ChatAdapter(ABC):
    """Abstract chat interface.

    The core agent depends only on this interface, not on HTTP, OpenAI response
    shapes, or any specific model runtime. Future adapters can implement local
    native bindings, mobile bridges, or streaming extensions alongside this API.
    """

    @abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    def health_check(self, model: Optional[str] = None) -> dict[str, Any]:
        return {
            "ok": False,
            "provider": self.__class__.__name__,
            "model": model,
            "error": "health check not implemented",
        }
