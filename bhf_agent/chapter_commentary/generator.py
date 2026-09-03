"""Generate BHF chapter commentary from evidence."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from bhf_agent import bible
from bhf_agent.config import AgentConfig

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


LOGGER = logging.getLogger(__name__)


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
                return CommentaryGenerationResult(
                    reference=request.reference,
                    status=CommentaryStatus.FAILED.value,
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
            )

            response_text = self._call_model(user_prompt)
            commentary_dict = self._parse_response(response_text)

            if not commentary_dict:
                # Model failed to generate valid JSON
                LOGGER.error(f"Model response for {request.reference}: {response_text[:500]}")
                return CommentaryGenerationResult(
                    reference=request.reference,
                    status=CommentaryStatus.NEEDS_REVIEW.value,
                    error="Model did not generate valid JSON response",
                )

            validation_result = validate_chapter_commentary(
                commentary_dict,
                bundle,
                expected_evidence_hash=bundle.evidence_hash,
                expected_prompt_version=COMMENTARY_PROMPT_VERSION,
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
                    sections=validation_result.accepted_sections,
                    generated_metadata=validation_result.commentary.generated_metadata,
                    validation_errors=list(validation_result.errors),
                )
            else:
                final_commentary = None

            return CommentaryGenerationResult(
                reference=request.reference,
                status=status,
                commentary=final_commentary,
                error=None if final_commentary else "Validation failed with no salvageable sections",
            )

        except Exception as exc:
            LOGGER.exception(f"Error generating commentary for {request.reference}")
            return CommentaryGenerationResult(
                reference=request.reference,
                status=CommentaryStatus.FAILED.value,
                error=f"Generation failed: {str(exc)}",
            )

    def _call_model(self, user_prompt: str) -> str:
        """Call configured AI model to generate commentary."""
        from bhf_agent.adapters.factory import build_chat_adapter

        try:
            adapter = build_chat_adapter(self.config)
            messages = [
                {"role": "user", "content": user_prompt}
            ]
            response = adapter.chat(
                messages=messages,
                system=CHAPTER_COMMENTARY_SYSTEM_PROMPT,
                max_tokens=2000,
            )
            return response.get("content", "")
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

        generated_metadata = GeneratedMetadata(
            evidence_hash=request.evidence_hash,
            evidence_bundle_version="1.0",
            commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
            commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
            model=self.config.model or "unknown",
            generated_timestamp=datetime.utcnow().isoformat(),
        )

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
