"""Generate BHF chapter commentary from evidence."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
import inspect
from typing import Any

from bhf_agent import bible
from bhf_agent.config import AgentConfig
from bhf_agent.models import ChatRequest

from .evidence_bundling import get_chapter_evidence_bundle
from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryGenerationRequest,
    CommentaryGenerationResult,
    CommentaryStatus,
)
from .prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT,
    build_user_prompt,
)
from .validation import validate_chapter_commentary
from .availability import classify_evidence_availability


LOGGER = logging.getLogger(__name__)
DEFAULT_COMMENTARY_MAX_TOKENS = 4500


class CommentaryGenerator:
    """Generate commentary for a canonical chapter."""

    def __init__(self, config: AgentConfig | None = None):
        """Initialize with optional agent config."""
        self.config = config or AgentConfig()

    def generate(self, request: CommentaryGenerationRequest) -> CommentaryGenerationResult:
        """Generate commentary for a chapter."""
        try:
            bundle = get_chapter_evidence_bundle(request.book, request.chapter)
            if bundle is None:
                commentary = self._failure_commentary(
                    request,
                    None,
                    CommentaryStatus.FAILED.value,
                    "Unable to load chapter evidence bundle",
                )
                return CommentaryGenerationResult(
                    reference=request.reference,
                    status=CommentaryStatus.FAILED.value,
                    commentary=commentary,
                    error="Unable to load chapter evidence bundle",
                )

            if bundle.evidence_hash != request.evidence_hash and not request.force_regenerate:
                return CommentaryGenerationResult(
                    reference=request.reference,
                    status=CommentaryStatus.STALE.value,
                    error="Evidence hash mismatch - commentary is stale",
                )

            # Generate using AI model
            try:
                chapter_data = bible.resolve_chapter(request.book, request.chapter)
                canonical_text = bible.passage_text(chapter_data.get("verses", []))
            except bible.BibleError:
                canonical_text = ""

            user_prompt = build_user_prompt(
                request.reference,
                request.book,
                request.chapter,
                canonical_text,
                bundle,
                classify_evidence_availability(bundle).value,
            )

            response_text = self._call_model(user_prompt)
            commentary_dict = self._parse_response(response_text)

            if not commentary_dict:
                # Model failed to generate valid JSON
                LOGGER.error(f"Model response for {request.reference}: {response_text[:500]}")
                commentary = self._failure_commentary(
                    request,
                    bundle,
                    CommentaryStatus.NEEDS_REVIEW.value,
                    "Model did not generate valid JSON response",
                )
                return CommentaryGenerationResult(
                    reference=request.reference,
                    status=CommentaryStatus.NEEDS_REVIEW.value,
                    commentary=commentary,
                    error="Model did not generate valid JSON response",
                )

            # Provenance is application-owned. Ignore all model-supplied metadata
            # and stamp the configured model and generation time here.
            commentary_dict["generated_metadata"] = self._authoritative_metadata(
                request, bundle
            ).to_dict()
            commentary_dict["evidence_availability"] = classify_evidence_availability(bundle).value
            commentary_dict["status"] = CommentaryStatus.PENDING.value

            validation_result = validate_chapter_commentary(
                commentary_dict,
                bundle,
                expected_evidence_hash=bundle.evidence_hash,
                expected_prompt_version=COMMENTARY_PROMPT_VERSION,
                expected_reference=request.reference,
                expected_book=request.book,
                expected_chapter=request.chapter,
            )

            if validation_result.valid:
                status = CommentaryStatus.VALIDATED.value
            elif validation_result.partial:
                status = CommentaryStatus.PARTIAL.value
            else:
                status = CommentaryStatus.NEEDS_REVIEW.value

            if validation_result.commentary:
                final_commentary = ChapterCommentary(
                    reference=validation_result.commentary.reference,
                    book=validation_result.commentary.book,
                    chapter=validation_result.commentary.chapter,
                    status=status,
                    evidence_availability=validation_result.commentary.evidence_availability,
                    sections=validation_result.accepted_sections,
                    generated_metadata=validation_result.commentary.generated_metadata,
                    failure_reason=None if validation_result.valid else "Some generated material was rejected",
                    validation_errors=list(validation_result.errors),
                )
            else:
                final_commentary = self._failure_commentary(
                    request,
                    bundle,
                    CommentaryStatus.NEEDS_REVIEW.value,
                    "Validation failed with no salvageable sections",
                )
                final_commentary = ChapterCommentary(
                    reference=final_commentary.reference,
                    book=final_commentary.book,
                    chapter=final_commentary.chapter,
                    status=final_commentary.status,
                    evidence_availability=classify_evidence_availability(bundle).value if bundle else None,
                    sections=[],
                    generated_metadata=final_commentary.generated_metadata,
                    failure_reason=final_commentary.failure_reason,
                    validation_errors=list(validation_result.errors),
                )

            return CommentaryGenerationResult(
                reference=request.reference,
                status=status,
                commentary=final_commentary,
                error=None if validation_result.valid else "Validation failed with no salvageable sections",
            )

        except Exception as exc:
            LOGGER.exception(f"Error generating commentary for {request.reference}")
            bundle = locals().get("bundle")
            commentary = self._failure_commentary(
                request,
                bundle,
                CommentaryStatus.FAILED.value,
                f"Generation failed: {exc}",
            )
            return CommentaryGenerationResult(
                reference=request.reference,
                status=CommentaryStatus.FAILED.value,
                commentary=commentary,
                error=f"Generation failed: {str(exc)}",
            )

    def _call_model(self, user_prompt: str) -> str:
        """Call configured AI model to generate commentary."""
        from bhf_agent.adapters.factory import build_chat_adapter

        try:
            adapter = build_chat_adapter(self.config)
            max_tokens = self._commentary_max_tokens()
            request = ChatRequest(
                system_prompt=CHAPTER_COMMENTARY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=self.config.model or "unknown",
                temperature=self.config.temperature,
                max_tokens=max_tokens,
                context_window=self.config.context_window,
                metadata={"commentary_prompt_version": COMMENTARY_PROMPT_VERSION},
            )
            parameters = inspect.signature(adapter.chat).parameters
            if "request" in parameters:
                response = adapter.chat(request)
                if getattr(response, "errors", None) or getattr(response, "error_category", None):
                    raise RuntimeError(
                        "; ".join(getattr(response, "errors", None) or [])
                        or str(getattr(response, "error_category", "model adapter error"))
                    )
                return str(getattr(response, "text", "") or "")

            # Compatibility with the two legacy adapters while the shared adapter
            # interface is being migrated.
            response = adapter.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system=CHAPTER_COMMENTARY_SYSTEM_PROMPT,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
            )
            return str(response.get("content", "") if isinstance(response, dict) else "")
        except Exception as exc:
            LOGGER.error(f"Model call failed: {exc}")
            raise

    def _parse_response(self, response_text: str) -> dict[str, Any] | None:
        """Parse JSON response from model."""
        if not response_text:
            return None

        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end > start:
                    response_text = response_text[start:end]

            return json.loads(response_text.strip())
        except (json.JSONDecodeError, ValueError) as exc:
            LOGGER.error(f"Failed to parse response JSON: {exc}")
            return None

    def _generate_minimal_commentary(
        self, request: CommentaryGenerationRequest, bundle: Any
    ) -> ChapterCommentary:
        """Generate minimal valid commentary structure (placeholder)."""
        from .models import CommentaryBlock, CommentarySection, GeneratedMetadata

        try:
            chapter_data = bible.resolve_chapter(request.book, request.chapter)
            chapter_text = bible.passage_text(chapter_data.get("verses", []))
        except bible.BibleError:
            chapter_text = ""

        generated_metadata = self._authoritative_metadata(request, bundle)

        overview_block = CommentaryBlock(
            id="overview_1",
            text=f"This is {request.reference}.",
            verse_refs=[request.reference],
            evidence_ids=[],
            confidence="medium",
            interpretation_level="fact",
        )

        overview_section = CommentarySection(
            kind="chapter_overview",
            title="Chapter Overview",
            blocks=[overview_block],
        )

        return ChapterCommentary(
            reference=request.reference,
            book=request.book,
            chapter=request.chapter,
            status=CommentaryStatus.PENDING.value,
            sections=[overview_section],
            generated_metadata=generated_metadata,
        )

    def _commentary_max_tokens(self) -> int:
        """Return the configurable output ceiling for commentary generation."""
        configured = os.environ.get("BHF_COMMENTARY_MAX_TOKENS")
        if configured:
            try:
                value = int(configured)
                if value > 0:
                    return value
            except ValueError:
                LOGGER.warning("Ignoring invalid BHF_COMMENTARY_MAX_TOKENS=%r", configured)
        return DEFAULT_COMMENTARY_MAX_TOKENS

    def _authoritative_metadata(self, request, bundle) -> Any:
        from .models import GeneratedMetadata

        return GeneratedMetadata(
            evidence_hash=bundle.evidence_hash if bundle is not None else request.evidence_hash,
            evidence_bundle_version=bundle.version if bundle is not None else "1.0",
            commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
            commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
            model=self.config.model or "unknown",
            generated_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _failure_commentary(
        self, request, bundle, status: str, reason: str
    ) -> ChapterCommentary:
        from .models import GeneratedMetadata

        metadata = self._authoritative_metadata(request, bundle)
        return ChapterCommentary(
            reference=request.reference,
            book=request.book,
            chapter=request.chapter,
            status=status,
            sections=[],
            generated_metadata=metadata,
            failure_reason=reason,
            validation_errors=[reason],
        )
