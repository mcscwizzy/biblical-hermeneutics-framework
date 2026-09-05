"""Direct Anthropic API adapter for chapter commentary generation."""

from __future__ import annotations

from typing import Any

from .base import ChatAdapter


class AnthropicDirectAdapter(ChatAdapter):
    """Call Anthropic API directly using the official SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022",
        timeout_seconds: int = 60,
    ):
        """Initialize with Anthropic API key."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required for AnthropicDirectAdapter. "
                "Install with: pip install anthropic"
            )

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> dict[str, str]:
        """Send messages to Claude and return response."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                temperature=temperature,
            )
            return {"content": response.content[0].text}
        except Exception as exc:
            raise RuntimeError(f"Anthropic API call failed: {exc}") from exc
