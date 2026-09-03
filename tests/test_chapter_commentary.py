"""Tests for BHF chapter commentary generation system."""

import json
import tempfile
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryBlock,
    CommentaryBuilder,
    CommentaryGenerator,
    CommentaryProgress,
    CommentaryStatus,
    delete_commentary,
    load_commentary,
    save_commentary,
    validate_chapter_commentary,
)
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.presentation.models import EvidenceBundle


def test_chapter_discovery():
    """Test discovering all canonical chapters."""
    builder = CommentaryBuilder(Path(tempfile.mkdtemp()))
    chapters = builder.discover_canonical_chapters()
    assert len(chapters) == 1189
    assert ("Genesis", 1) in chapters
    assert ("Revelation", 22) in chapters


def test_generate_minimal_commentary():
    """Test generating a minimal commentary for a chapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        result = builder.build_chapter("Genesis", 1)
        assert result.reference == "Genesis 1"
        assert result.status in {
            CommentaryStatus.VALIDATED.value,
            CommentaryStatus.PARTIAL.value,
            CommentaryStatus.NEEDS_REVIEW.value,
        }


def test_save_and_load_commentary():
    """Test saving and loading commentary from storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        commentary = ChapterCommentary(
            reference="Genesis 1",
            book="Genesis",
            chapter=1,
            status=CommentaryStatus.VALIDATED.value,
            sections=[],
        )

        path = save_commentary(commentary, tmpdir)
        assert path.exists()

        loaded = load_commentary(tmpdir, "Genesis", 1)
        assert loaded is not None
        assert loaded.reference == "Genesis 1"
        assert loaded.book == "Genesis"
        assert loaded.chapter == 1


def test_delete_commentary():
    """Test deleting a commentary file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        commentary = ChapterCommentary(
            reference="Genesis 1",
            book="Genesis",
            chapter=1,
            status=CommentaryStatus.VALIDATED.value,
        )
        save_commentary(commentary, tmpdir)
        assert delete_commentary(tmpdir, "Genesis", 1)
        assert load_commentary(tmpdir, "Genesis", 1) is None


def test_progress_tracking():
    """Test progress tracking across multiple chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)

        progress = builder.initialize_progress(1189)
        assert progress.total_chapters == 1189
        assert progress.completed == 0

        builder.build_chapter("Genesis", 1)
        progress = builder.get_progress()
        assert progress.completed > 0


def test_resume_support():
    """Test that build can resume from previous progress."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)

        # Build first two chapters
        builder.build_chapter("Genesis", 1)
        builder.build_chapter("Genesis", 2)

        initial_progress = builder.get_progress()
        initial_completed = initial_progress.completed

        # Resume and build a few more
        progress = builder.build_all(resume=True, limit=5)

        # Should not re-generate Genesis 1-2
        assert progress.completed >= initial_completed


def test_validate_chapter_commentary_with_no_sections():
    """Test validation of commentary with no sections."""
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    bundle = get_chapter_evidence_bundle("Genesis", 1)
    assert bundle is not None

    commentary_dict = {
        "reference": "Genesis 1",
        "book": "Genesis",
        "chapter": 1,
        "status": CommentaryStatus.NEEDS_REVIEW.value,
        "sections": [],
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": "1.0",
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": "test",
        },
    }

    result = validate_chapter_commentary(commentary_dict, bundle)
    assert result.valid is False


def test_validate_commentary_rejects_unknown_evidence():
    """Test that validation rejects unknown evidence IDs."""
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    bundle = get_chapter_evidence_bundle("Genesis", 1)
    assert bundle is not None

    commentary_dict = {
        "reference": "Genesis 1",
        "book": "Genesis",
        "chapter": 1,
        "status": CommentaryStatus.NEEDS_REVIEW.value,
        "sections": [
            {
                "kind": "chapter_overview",
                "title": "Overview",
                "blocks": [
                    {
                        "id": "block_1",
                        "text": "This chapter starts creation.",
                        "verse_refs": ["Genesis 1:1"],
                        "evidence_ids": ["unknown_evidence"],
                        "confidence": "high",
                        "interpretation_level": "fact",
                    }
                ],
            }
        ],
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": "1.0",
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": "test",
        },
    }

    result = validate_chapter_commentary(commentary_dict, bundle)
    assert result.valid is False
    assert any("unknown" in error.lower() for error in result.errors)


def test_builder_status_reporting():
    """Test progress reporting from builder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        chapters = builder.discover_canonical_chapters()
        assert len(chapters) > 0

        progress = CommentaryProgress(total_chapters=len(chapters))
        builder.save_progress(progress)

        loaded_progress = builder.get_progress()
        assert loaded_progress is not None
        assert loaded_progress.total_chapters == len(chapters)


def test_evidence_bundle_for_chapter():
    """Test getting evidence bundle for a chapter."""
    bundle = get_chapter_evidence_bundle("Genesis", 1)
    assert bundle is not None
    assert bundle.passage_ref == "Genesis 1"
    assert bundle.evidence_hash is not None
    assert len(bundle.evidence_hash) == 64  # SHA256 hex


def test_evidence_bundle_for_invalid_chapter():
    """Test that invalid chapters return None."""
    bundle = get_chapter_evidence_bundle("NotABook", 1)
    assert bundle is None
