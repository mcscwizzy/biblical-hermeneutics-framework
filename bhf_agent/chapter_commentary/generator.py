"""Generate BHF chapter commentary from evidence."""

from __future__ import annotations

import json
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
from .validation import validate_chapter_commentary


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

            # NOTE: This is a placeholder. Real implementation would call AI model
            # to generate commentary based on bundle evidence.
            # For now, return a minimal valid structure for testing.
            commentary = self._generate_minimal_commentary(request, bundle)

            validation_result = validate_chapter_commentary(
                commentary.to_dict(),
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

            final_commentary = ChapterCommentary(
                reference=commentary.reference,
                book=commentary.book,
                chapter=commentary.chapter,
                status=status,
                sections=validation_result.accepted_sections,
                generated_metadata=validation_result.commentary.generated_metadata
                if validation_result.commentary
                else None,
                validation_errors=list(validation_result.errors),
            )

            return CommentaryGenerationResult(
                reference=request.reference,
                status=status,
                commentary=final_commentary,
            )

        except Exception as exc:
            return CommentaryGenerationResult(
                reference=request.reference,
                status=CommentaryStatus.FAILED.value,
                error=f"Generation failed: {str(exc)}",
            )

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
