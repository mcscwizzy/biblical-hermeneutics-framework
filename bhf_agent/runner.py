"""Reusable BHF agent runner."""

from __future__ import annotations

from typing import Any, Optional

from .adapters import ChatAdapter, OpenAICompatibleAdapter
from .config import AgentConfig, ConfigError
from .genre import classify_genre
from .models import AgentResult, ChatRequest
from .profiles import ProfileLoader
from .prompts import build_prompt
from .references import detect_reference
from .validation import validate_response


class BHFAgent:
    def __init__(
        self,
        config: AgentConfig,
        adapter: Optional[ChatAdapter] = None,
        profile_loader: Optional[ProfileLoader] = None,
    ) -> None:
        config.validate()
        self.config = config
        self.profile_loader = profile_loader or ProfileLoader()
        self.adapter = adapter or self._build_adapter(config)

    def ask(self, question: str) -> AgentResult:
        reference_context = detect_reference(question)
        genre_context = classify_genre(reference_context)
        profile = self.profile_loader.load(self.config.profile)
        system_prompt, user_prompt = build_prompt(
            profile.name,
            profile.content,
            reference_context,
            genre_context,
            question,
            show_method_notes=self.config.show_method_notes,
        )
        chat_request = ChatRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.config.model or "",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            metadata={
                "profile": profile.name,
                "reference_context": reference_context.to_dict(),
                "genre_context": genre_context.to_dict(),
            },
        )
        chat_response = self.adapter.chat(chat_request)
        validation_result = validate_response(chat_response.text)
        model_metadata: dict[str, Any] = {
            "model": chat_response.model,
            "usage": chat_response.usage,
        }
        if self.config.debug:
            model_metadata["raw_provider_response"] = chat_response.raw_provider_response

        return AgentResult(
            answer_text=chat_response.text,
            reference_context=reference_context,
            genre_context=genre_context,
            profile_used=profile.name,
            validation_result=validation_result,
            model_metadata=model_metadata,
            warnings=chat_response.warnings,
            errors=chat_response.errors,
        )

    def _build_adapter(self, config: AgentConfig) -> ChatAdapter:
        if config.adapter == "openai_compatible":
            if not config.base_url:
                raise ConfigError("base_url is required for openai_compatible adapter")
            return OpenAICompatibleAdapter(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout_seconds=config.timeout_seconds,
            )
        raise ConfigError(f"unsupported adapter: {config.adapter}")
