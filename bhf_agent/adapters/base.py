"""Adapter interface for local and future model runtimes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from bhf_agent.models import ChatRequest, ChatResponse


class ResponseFormatCapability(str, Enum):
    """Structured output capability level for a model."""

    JSON_SCHEMA = "json_schema"
    JSON_OBJECT = "json_object"
    NONE = "none"


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

    def supports_json_schema_response_format(self) -> bool:
        return False

    def presentation_response_format_capability(
        self, model: Optional[str] = None
    ) -> ResponseFormatCapability:
        """Return the structured output capability for presentation generation.

        By default, uses the legacy supports_json_schema_response_format() method
        for backwards compatibility. Subclasses should override to provide
        model-aware capability detection.
        """
        if self.supports_json_schema_response_format():
            return ResponseFormatCapability.JSON_SCHEMA
        return ResponseFormatCapability.NONE

    def health_check(self, model: Optional[str] = None) -> dict[str, Any]:
        return {
            "ok": False,
            "provider": self.__class__.__name__,
            "model": model,
            "error": "health check not implemented",
        }
