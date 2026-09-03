"""Coordinate full-Bible BHF commentary generation with resumable progress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bhf_agent import bible
from bhf_agent.config import AgentConfig

from .evidence_bundling import get_chapter_evidence_bundle
from .generator import CommentaryGenerator
from .models import (
    ChapterCommentary,
    CommentaryGenerationRequest,
    CommentaryProgress,
    CommentaryStatus,
)
from .storage import (
    delete_commentary,
    get_commentary_dir,
    list_commentaries,
    load_commentary,
    save_commentary,
)


PROGRESS_FILE = ".bhf-commentary-progress.json"


class CommentaryBuilder:
    """Build full-Bible commentary with progress tracking."""

    def __init__(
        self,
        storage_dir: str | Path,
        config: AgentConfig | None = None,
    ):
        self.storage_dir = Path(storage_dir)
        if config is None:
            # Try to load from .bhf/config.json
            config_path = Path(".bhf/config.json")
            if config_path.exists():
                config = AgentConfig.from_json_file(config_path)
            else:
                config = AgentConfig()
        self.config = config
        self.generator = CommentaryGenerator(config)
        self.progress_file = self.storage_dir / PROGRESS_FILE

    def discover_canonical_chapters(self) -> list[tuple[str, int]]:
        """Discover all canonical chapters from Bible data."""
        chapters = []
        try:
            books = bible.list_books()
            for book in books:
                book_name = book.get("name")
                num_chapters = book.get("chapters", 0)
                for chapter_num in range(1, num_chapters + 1):
                    chapters.append((book_name, chapter_num))
        except Exception:
            pass

        return sorted(chapters)

    def get_progress(self) -> CommentaryProgress | None:
        """Load current progress from disk."""
        if not self.progress_file.exists():
            return None

        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            return CommentaryProgress(
                total_chapters=data.get("total_chapters", 0),
                validated=data.get("validated", 0),
                partial=data.get("partial", 0),
                needs_review=data.get("needs_review", 0),
                failed=data.get("failed", 0),
                stale=data.get("stale", 0),
                pending=data.get("pending", 0),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def save_progress(self, progress: CommentaryProgress) -> None:
        """Save progress to disk."""
        self.progress_file.write_text(
            json.dumps(progress.to_dict(), indent=2), encoding="utf-8"
        )

    def initialize_progress(self, total_chapters: int) -> CommentaryProgress:
        """Initialize progress tracking for full build."""
        progress = CommentaryProgress(total_chapters=total_chapters)
        self.save_progress(progress)
        return progress

    def build_all(
        self,
        resume: bool = True,
        stale_only: bool = False,
        failed_only: bool = False,
        force: bool = False,
        limit: int | None = None,
    ) -> CommentaryProgress:
        """Build commentary for all canonical chapters."""
        chapters = self.discover_canonical_chapters()
        progress = self.get_progress()

        if progress is None or progress.total_chapters != len(chapters):
            progress = self.initialize_progress(len(chapters))

        processed = 0
        for idx, (book, chapter_num) in enumerate(chapters, start=1):
            if limit and processed >= limit:
                break

            reference = bible.verse_range_reference(book, chapter_num)

            # Decide whether to (re)generate
            existing = load_commentary(self.storage_dir, book, chapter_num)

            if not force and existing is not None:
                if stale_only and existing.status != CommentaryStatus.STALE.value:
                    continue
                if failed_only and existing.status != CommentaryStatus.FAILED.value:
                    continue
                if not stale_only and not failed_only and resume:
                    if existing.status in (
                        CommentaryStatus.VALIDATED.value,
                        CommentaryStatus.PARTIAL.value,
                    ):
                        continue

            # Generate or regenerate
            result = self._generate_and_save(book, chapter_num, reference)

            # Update progress immediately
            if existing:
                progress = self._decrement_old_status(progress, existing.status)

            if result.commentary:
                # Save commentary atomically
                save_commentary(result.commentary, self.storage_dir)
                # Update progress stat
                progress = self._increment_new_status(progress, result.commentary.status)

            # CRITICAL: Persist progress durably immediately after each chapter
            self.save_progress(progress)

            processed += 1
            if idx % 50 == 0:
                # Status update every 50 chapters
                print(f"Progress: {idx}/{len(chapters)} chapters")

        return progress

    def build_book(self, book: str) -> CommentaryProgress:
        """Build commentary for all chapters in a book."""
        try:
            chapter_data = bible.resolve_chapter(book, 1)
            book_name = chapter_data["book"]
        except bible.BibleError:
            raise ValueError(f"Unknown book: {book}")

        chapters = self.discover_canonical_chapters()
        book_chapters = [(b, c) for b, c in chapters if b == book_name]

        progress = self.get_progress()
        if progress is None:
            progress = self.initialize_progress(len(chapters))

        for book, chapter_num in book_chapters:
            reference = bible.verse_range_reference(book, chapter_num)
            result = self._generate_and_save(book, chapter_num, reference)

            if result.commentary:
                progress = self._increment_new_status(progress, result.commentary.status)
                save_commentary(result.commentary, self.storage_dir)

        self.save_progress(progress)
        return progress

    def build_chapter(self, book: str, chapter: int, force: bool = False) -> ChapterCommentary:
        """Build commentary for a specific chapter."""
        try:
            chapter_data = bible.resolve_chapter(book, chapter)
            book_name = chapter_data["book"]
            reference = bible.verse_range_reference(book_name, chapter)
        except bible.BibleError as exc:
            raise ValueError(f"Invalid chapter: {book} {chapter}") from exc

        existing = load_commentary(self.storage_dir, book_name, chapter)
        if not force and existing and existing.status == CommentaryStatus.VALIDATED.value:
            return existing

        result = self._generate_and_save(book_name, chapter, reference)

        if result.commentary:
            save_commentary(result.commentary, self.storage_dir)

            # Update progress
            progress = self.get_progress()
            chapters = self.discover_canonical_chapters()
            if progress is None:
                progress = self.initialize_progress(len(chapters))
            if existing:
                progress = self._decrement_old_status(progress, existing.status)
            progress = self._increment_new_status(progress, result.commentary.status)
            self.save_progress(progress)

            return result.commentary

        raise ValueError(f"Generation failed for {reference}: {result.error}")

    def _generate_and_save(
        self, book: str, chapter: int, reference: str
    ) -> Any:
        """Generate and save a single chapter."""
        bundle = get_chapter_evidence_bundle(book, chapter)
        if bundle is None:
            return CommentaryGenerationRequest(
                book=book,
                chapter=chapter,
                reference=reference,
                evidence_hash="",
            )

        request = CommentaryGenerationRequest(
            book=book,
            chapter=chapter,
            reference=reference,
            evidence_hash=bundle.evidence_hash,
        )

        return self.generator.generate(request)

    def _increment_new_status(
        self, progress: CommentaryProgress, status: str
    ) -> CommentaryProgress:
        """Increment progress counter for new status."""
        if status == CommentaryStatus.VALIDATED.value:
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated + 1,
                partial=progress.partial,
                needs_review=progress.needs_review,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.PARTIAL.value:
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=progress.partial + 1,
                needs_review=progress.needs_review,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.NEEDS_REVIEW.value:
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=progress.partial,
                needs_review=progress.needs_review + 1,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.FAILED.value:
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=progress.partial,
                needs_review=progress.needs_review,
                failed=progress.failed + 1,
                stale=progress.stale,
                pending=progress.pending,
            )
        return progress

    def _decrement_old_status(
        self, progress: CommentaryProgress, status: str
    ) -> CommentaryProgress:
        """Decrement progress counter for old status."""
        if status == CommentaryStatus.VALIDATED.value:
            validated = max(0, progress.validated - 1)
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=validated,
                partial=progress.partial,
                needs_review=progress.needs_review,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.PARTIAL.value:
            partial = max(0, progress.partial - 1)
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=partial,
                needs_review=progress.needs_review,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.NEEDS_REVIEW.value:
            needs_review = max(0, progress.needs_review - 1)
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=progress.partial,
                needs_review=needs_review,
                failed=progress.failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        elif status == CommentaryStatus.FAILED.value:
            failed = max(0, progress.failed - 1)
            return CommentaryProgress(
                total_chapters=progress.total_chapters,
                validated=progress.validated,
                partial=progress.partial,
                needs_review=progress.needs_review,
                failed=failed,
                stale=progress.stale,
                pending=progress.pending,
            )
        return progress
