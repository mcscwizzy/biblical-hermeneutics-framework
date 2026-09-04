"""Coordinate full-Bible commentary generation with resumable progress."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from bhf_agent import bible
from bhf_agent.config import AgentConfig

from .evidence_bundling import get_chapter_evidence_bundle
from .generator import CommentaryGenerator
from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryGenerationRequest,
    CommentaryProgress,
    CommentaryStatus,
)
from .storage import load_commentary, save_commentary


PROGRESS_FILE = ".bhf-commentary-progress.json"


class CommentaryBuilder:
    """Build full-Bible commentary while treating chapter files as the source of truth."""

    def __init__(
        self,
        storage_dir: str | Path,
        config: AgentConfig | None = None,
    ):
        self.storage_dir = Path(storage_dir)
        if config is None:
            config_path = Path(".bhf/config.json")
            if config_path.exists():
                config = AgentConfig.from_json_file(config_path)
            else:
                # Commentary is another BHF model consumer. When no explicit
                # agent config is present, use the same environment-backed web
                # defaults that configure the rest of the application rather
                # than falling back to the unconfigured AgentConfig defaults.
                from bhf_web.forms import load_web_defaults

                config = load_web_defaults().config
        self.config = config
        self.generator = CommentaryGenerator(config)
        self.progress_file = self.storage_dir / PROGRESS_FILE

    def discover_canonical_chapters(self) -> list[tuple[str, int]]:
        """Discover all canonical chapters from Bible data."""
        chapters: list[tuple[str, int]] = []
        try:
            for book in bible.list_books():
                book_name = book.get("name")
                for chapter_num in range(1, book.get("chapters", 0) + 1):
                    chapters.append((book_name, chapter_num))
        except Exception:
            return []
        return sorted(chapters)

    def get_progress(self, *, rescan: bool = False) -> CommentaryProgress | None:
        """Load cached progress, or reconstruct it from chapter files when requested."""
        if rescan:
            return self.rescan_progress()
        if not self.progress_file.exists():
            return None
        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            return CommentaryProgress(
                total_chapters=int(data.get("total_chapters", 0)),
                validated=int(data.get("validated", 0)),
                partial=int(data.get("partial", 0)),
                needs_review=int(data.get("needs_review", 0)),
                failed=int(data.get("failed", 0)),
                stale=int(data.get("stale", 0)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def save_progress(self, progress: CommentaryProgress) -> None:
        """Save the progress cache atomically; its counters remain rebuildable."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(progress.to_dict(), indent=2)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.storage_dir,
                prefix=f".{PROGRESS_FILE}.", suffix=".tmp", delete=False
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.progress_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def initialize_progress(self, total_chapters: int) -> CommentaryProgress:
        """Initialize an empty progress cache for a canonical set."""
        progress = CommentaryProgress(total_chapters=total_chapters)
        self.save_progress(progress)
        return progress

    def rescan_progress(
        self,
        chapters: Iterable[tuple[str, int]] | None = None,
        *,
        check_evidence: bool = True,
    ) -> CommentaryProgress:
        """Rebuild counts from canonical chapter files, not historical counters.

        Prompt/schema mismatches are always stale. Evidence hashes are checked when
        requested; callers running a long build can disable that extra retrieval after
        the initial scan and still retain deterministic file-based counts.
        """
        canonical = list(chapters or self.discover_canonical_chapters())
        counts = {status.value: 0 for status in CommentaryStatus}
        for book, chapter in canonical:
            commentary = load_commentary(self.storage_dir, book, chapter)
            if commentary is None:
                counts[CommentaryStatus.PENDING.value] += 1
                continue
            bundle = None
            if (
                check_evidence
                and commentary.generated_metadata
                and commentary.generated_metadata.commentary_prompt_version == COMMENTARY_PROMPT_VERSION
                and commentary.generated_metadata.commentary_schema_version == COMMENTARY_SCHEMA_VERSION
            ):
                bundle = get_chapter_evidence_bundle(book, chapter)
            status = self._effective_status(commentary, book, chapter, bundle)
            if status not in counts or status in {CommentaryStatus.PENDING.value, CommentaryStatus.GENERATING.value}:
                status = CommentaryStatus.PENDING.value
            counts[status] += 1

        progress = CommentaryProgress(
            total_chapters=len(canonical),
            validated=counts[CommentaryStatus.VALIDATED.value],
            partial=counts[CommentaryStatus.PARTIAL.value],
            needs_review=counts[CommentaryStatus.NEEDS_REVIEW.value],
            failed=counts[CommentaryStatus.FAILED.value],
            stale=counts[CommentaryStatus.STALE.value],
        )
        self.save_progress(progress)
        return progress

    def build_all(
        self,
        resume: bool = True,
        stale_only: bool = False,
        failed_only: bool = False,
        partial_only: bool = False,
        needs_review_only: bool = False,
        force: bool = False,
        limit: int | None = None,
    ) -> CommentaryProgress:
        """Build selected canonical chapters without skipping non-validated output."""
        chapters = self.discover_canonical_chapters()
        selected_modes = [stale_only, failed_only, partial_only, needs_review_only]
        if sum(selected_modes) > 1:
            raise ValueError("generation status filters are mutually exclusive")

        progress = self.rescan_progress(chapters, check_evidence=True)
        processed = 0
        for idx, (book, chapter_num) in enumerate(chapters, start=1):
            if limit is not None and processed >= limit:
                break
            existing = load_commentary(self.storage_dir, book, chapter_num)
            bundle = (
                get_chapter_evidence_bundle(book, chapter_num)
                if self._metadata_can_have_hash_drift(existing)
                else None
            )
            effective_status = self._effective_status(existing, book, chapter_num, bundle)

            if not force and not self._should_generate(
                effective_status,
                resume=resume,
                stale_only=stale_only,
                failed_only=failed_only,
                partial_only=partial_only,
                needs_review_only=needs_review_only,
            ):
                continue

            result = self._generate_and_save(book, chapter_num, bible.verse_range_reference(book, chapter_num), bundle=bundle)
            if result.commentary:
                save_commentary(result.commentary, self.storage_dir)
            progress = self.rescan_progress(chapters, check_evidence=False)
            self.save_progress(progress)
            processed += 1
            if idx % 50 == 0:
                print(f"Progress: {idx}/{len(chapters)} chapters")
        return progress

    def build_book(self, book: str) -> CommentaryProgress:
        """Build all chapters in one book using normal current-output resume rules."""
        try:
            book_name = bible.resolve_chapter(book, 1)["book"]
        except bible.BibleError as exc:
            raise ValueError(f"Unknown book: {book}") from exc
        chapters = [item for item in self.discover_canonical_chapters() if item[0] == book_name]
        return self._build_selected(chapters)

    def _build_selected(self, chapters: list[tuple[str, int]]) -> CommentaryProgress:
        """Build a subset while keeping progress relative to all canonical chapters."""
        progress = self.rescan_progress(check_evidence=True)
        for book, chapter_num in chapters:
            existing = load_commentary(self.storage_dir, book, chapter_num)
            bundle = (
                get_chapter_evidence_bundle(book, chapter_num)
                if self._metadata_can_have_hash_drift(existing)
                else None
            )
            status = self._effective_status(existing, book, chapter_num, bundle)
            if existing and status == CommentaryStatus.VALIDATED.value:
                continue
            result = self._generate_and_save(book, chapter_num, bible.verse_range_reference(book, chapter_num), bundle=bundle)
            if result.commentary:
                save_commentary(result.commentary, self.storage_dir)
            progress = self.rescan_progress(check_evidence=False)
        return progress

    def build_chapter(self, book: str, chapter: int, force: bool = False) -> ChapterCommentary:
        """Build one chapter; current validated output is the only default skip."""
        try:
            chapter_data = bible.resolve_chapter(book, chapter)
            book_name = chapter_data["book"]
            reference = bible.verse_range_reference(book_name, chapter)
        except bible.BibleError as exc:
            raise ValueError(f"Invalid chapter: {book} {chapter}") from exc

        existing = load_commentary(self.storage_dir, book_name, chapter)
        bundle = get_chapter_evidence_bundle(book_name, chapter)
        if not force and existing and self._effective_status(existing, book_name, chapter, bundle) == CommentaryStatus.VALIDATED.value:
            return existing

        result = self._generate_and_save(book_name, chapter, reference, bundle=bundle)
        if not result.commentary:
            raise ValueError(f"Generation failed for {reference}: {result.error}")
        save_commentary(result.commentary, self.storage_dir)
        self.rescan_progress(check_evidence=False)
        return result.commentary

    def _generate_and_save(self, book: str, chapter: int, reference: str, *, bundle=None) -> Any:
        """Generate one chapter using an already loaded bundle when available."""
        bundle = bundle or get_chapter_evidence_bundle(book, chapter)
        request = CommentaryGenerationRequest(
            book=book,
            chapter=chapter,
            reference=reference,
            evidence_hash=bundle.evidence_hash if bundle else "",
        )
        return self.generator.generate(request)

    def _effective_status(self, commentary, book: str, chapter: int, bundle=None) -> str:
        if commentary is None:
            return CommentaryStatus.PENDING.value
        metadata = commentary.generated_metadata
        if (
            metadata is None
            or metadata.commentary_prompt_version != COMMENTARY_PROMPT_VERSION
            or metadata.commentary_schema_version != COMMENTARY_SCHEMA_VERSION
            or commentary.book != book
            or commentary.chapter != chapter
        ):
            return CommentaryStatus.STALE.value
        if bundle is not None and metadata.evidence_hash != bundle.evidence_hash:
            return CommentaryStatus.STALE.value
        return commentary.status

    @staticmethod
    def _metadata_can_have_hash_drift(commentary) -> bool:
        metadata = commentary.generated_metadata if commentary else None
        return bool(
            metadata
            and metadata.commentary_prompt_version == COMMENTARY_PROMPT_VERSION
            and metadata.commentary_schema_version == COMMENTARY_SCHEMA_VERSION
        )

    @staticmethod
    def _should_generate(
        status: str,
        *,
        resume: bool,
        stale_only: bool,
        failed_only: bool,
        partial_only: bool,
        needs_review_only: bool,
    ) -> bool:
        selected = {
            "stale_only": (stale_only, CommentaryStatus.STALE.value),
            "failed_only": (failed_only, CommentaryStatus.FAILED.value),
            "partial_only": (partial_only, CommentaryStatus.PARTIAL.value),
            "needs_review_only": (needs_review_only, CommentaryStatus.NEEDS_REVIEW.value),
        }
        for enabled, wanted in selected.values():
            if enabled:
                return status == wanted
        if not resume:
            return True
        return status != CommentaryStatus.VALIDATED.value
