"""Tests for BHF chapter commentary generation system."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

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
    CommentarySectionKind,
    CommentaryGenerationRequest,
    CommentaryGenerationResult,
    delete_commentary,
    load_commentary,
    save_commentary,
    validate_chapter_commentary,
)
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.prompts import build_user_prompt
from bhf_agent.chapter_commentary.validation import CommentaryRejectionCode
from bhf_agent.config import AgentConfig
from bhf_agent.presentation.models import EvidenceBundle
from bhf_agent.presentation.models import EvidenceItem
from bhf_agent.chapter_commentary.models import GeneratedMetadata


def _bundle(
    *,
    book="Genesis",
    chapter=1,
    confidence="high",
    evidence_id="evidence-1",
    disputed=None,
    claim="A supplied historical claim.",
):
    metadata = {}
    if disputed is not None:
        metadata["dispute_status"] = disputed
    item = EvidenceItem(
        id=evidence_id,
        claim=claim,
        category="history",
        source_ids=["source-1"],
        related_entity_ids=[],
        passage_anchors=[f"{book} {chapter}:1"],
        confidence=confidence,
        relevance_metadata=metadata,
    )
    return EvidenceBundle(
        passage_ref=f"{book} {chapter}:1-3",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=[item],
        geography={},
        provenance={},
        evidence_hash="a" * 64,
    )


def _metadata(bundle, *, prompt_version=COMMENTARY_PROMPT_VERSION, model="test"):
    return {
        "evidence_hash": bundle.evidence_hash,
        "evidence_bundle_version": bundle.version,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "commentary_prompt_version": prompt_version,
        "model": model,
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _raw_commentary(bundle, sections, *, reference="Genesis 1", book="Genesis", chapter=1):
    return {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "status": "pending",
        "sections": sections,
        "generated_metadata": _metadata(bundle),
    }


def _block(bundle, *, evidence_id="evidence-1", verse_ref="Genesis 1:1", confidence="high", text="Supported prose.", interpretation="inference"):
    return {
        "id": "block-1",
        "text": text,
        "verse_refs": [verse_ref] if verse_ref is not None else [],
        "evidence_ids": [evidence_id],
        "confidence": confidence,
        "interpretation_level": interpretation,
    }


class _FakeGenerator:
    def generate(self, request):
        commentary = ChapterCommentary(
            reference=request.reference,
            book=request.book,
            chapter=request.chapter,
            status=CommentaryStatus.VALIDATED.value,
            sections=[],
            generated_metadata=GeneratedMetadata(
                evidence_hash=request.evidence_hash,
                evidence_bundle_version="1.0",
                commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
                commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
                model="test-model",
                generated_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        return CommentaryGenerationResult(
            reference=request.reference,
            status=commentary.status,
            commentary=commentary,
        )


def test_chapter_discovery():
    """Test discovering all canonical chapters."""
    builder = CommentaryBuilder(Path(tempfile.mkdtemp()))
    chapters = builder.discover_canonical_chapters()
    assert len(chapters) == 1189
    assert chapters[:3] == [("Genesis", 1), ("Genesis", 2), ("Genesis", 3)]
    assert ("Genesis", 1) in chapters
    assert ("Revelation", 22) in chapters


def test_builder_uses_shared_bhf_environment_defaults_without_explicit_config(
    monkeypatch, tmp_path
):
    """The commentary CLI must use BHF's normal provider configuration."""
    expected = AgentConfig(
        adapter="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="test/model",
    )

    monkeypatch.setattr(
        "bhf_web.forms.load_web_defaults",
        lambda: SimpleNamespace(config=expected),
    )

    builder = CommentaryBuilder(tmp_path)

    assert builder.config is expected


def test_generate_minimal_commentary(monkeypatch):
    """Test generating a minimal commentary for a chapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        builder.generator = _FakeGenerator()
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


def test_progress_tracking(monkeypatch):
    """Test progress tracking across multiple chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        builder.generator = _FakeGenerator()

        progress = builder.initialize_progress(1189)
        assert progress.total_chapters == 1189
        assert progress.completed == 0

        builder.build_chapter("Genesis", 1)
        progress = builder.get_progress()
        assert progress.completed > 0


def test_resume_support(monkeypatch):
    """Test that build can resume from previous progress."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        builder.generator = _FakeGenerator()

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


def test_unsupported_section_kind_is_rejected():
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "section", "title": "Bad", "blocks": [_block(bundle)]}]),
        bundle,
    )
    assert not result.valid
    assert result.commentary is None
    assert CommentaryRejectionCode.UNSUPPORTED_SECTION_KIND.value in result.section_results[0].reason_codes


def test_unsupported_section_is_not_included_in_salvage():
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [
            {"kind": "section", "title": "Bad", "blocks": [_block(bundle)]},
            {"kind": "chapter_overview", "title": "Good", "blocks": [_block(bundle)]},
        ]),
        bundle,
    )
    assert result.partial
    assert [section.kind for section in result.accepted_sections] == ["chapter_overview"]


def test_valid_sections_survive_when_another_section_fails():
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [
            {"kind": "chapter_overview", "title": "Good", "blocks": [_block(bundle)]},
            {"kind": "language_literary", "title": "Mixed", "blocks": [
                _block(bundle),
                _block(bundle, evidence_id="unknown"),
            ]},
        ]),
        bundle,
    )
    assert not result.valid
    assert result.partial
    assert [section.kind for section in result.accepted_sections] == [
        "chapter_overview", "language_literary"
    ]
    assert len(result.accepted_sections[1].blocks) == 1


def test_full_canonical_chapter_text_is_passed_to_prompt():
    bundle = _bundle()
    canonical_text = "BEGIN " + ("canonical chapter text " * 300) + "END OF CHAPTER"
    prompt = build_user_prompt("Genesis 1", "Genesis", 1, canonical_text, bundle)
    assert canonical_text in prompt
    assert prompt.endswith("JSON ONLY.")


def test_genesis_one_cannot_cite_genesis_two():
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [
            _block(bundle, verse_ref="Genesis 2:1")
        ]}]),
        bundle,
    )
    assert not result.valid
    assert CommentaryRejectionCode.OUT_OF_CHAPTER_VERSE_REFERENCE.value in result.section_results[0].block_results[0].reason_codes


@pytest.mark.parametrize("reference,book,chapter", [
    ("Genesis 1", "Genesis", 2),
    ("Genesis 1", "Exodus", 1),
    ("Genesis 1:1", "Genesis", 1),
])
def test_wrong_chapter_identity_is_rejected(reference, book, chapter):
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle)]}], reference=reference, book=book, chapter=chapter),
        bundle,
        expected_reference="Genesis 1",
        expected_book="Genesis",
        expected_chapter=1,
    )
    assert not result.valid
    assert result.commentary is None
    assert CommentaryRejectionCode.CHAPTER_IDENTITY_MISMATCH.value in result.errors[0]


def test_unknown_evidence_id_is_rejected_with_code():
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle, evidence_id="missing")]}]),
        bundle,
    )
    block_result = result.section_results[0].block_results[0]
    assert not block_result.valid
    assert CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value in block_result.reason_codes


def test_confidence_cannot_exceed_evidence_confidence():
    bundle = _bundle(confidence="low")
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle, confidence="high")]}]),
        bundle,
    )
    assert CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value in result.section_results[0].block_results[0].reason_codes


def test_disputed_evidence_cannot_be_emitted_as_fact():
    bundle = _bundle(disputed="major_scholarly_disagreement")
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle, interpretation="fact")]}]),
        bundle,
    )
    assert CommentaryRejectionCode.DISPUTED_AS_FACT.value in result.section_results[0].block_results[0].reason_codes


def test_explicit_date_must_be_supported_by_cited_evidence():
    unsupported = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(unsupported, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(unsupported, text="This occurred in AD 70.")]}]),
        unsupported,
    )
    assert CommentaryRejectionCode.UNSUPPORTED_DATE.value in result.section_results[0].block_results[0].reason_codes

    supported = _bundle(claim="A historical source dates this event to about AD 70.")
    result = validate_chapter_commentary(
        _raw_commentary(supported, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(supported, text="This occurred in AD 70.")]}]),
        supported,
    )
    assert result.valid


def test_prompt_lists_all_valid_section_kinds():
    bundle = _bundle()
    prompt = build_user_prompt("Genesis 1", "Genesis", 1, "text", bundle)
    for kind in CommentarySectionKind:
        assert kind.value in prompt
    assert "Never invent values such as section" in prompt


def test_generator_stamps_configured_model_and_timestamp(monkeypatch):
    from bhf_agent.chapter_commentary import generator as generator_module
    from bhf_agent.config import AgentConfig

    bundle = _bundle()
    raw = _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle)]}])
    raw["generated_metadata"] = {"model": "spoofed-model"}
    captured = {}

    class Adapter:
        def chat(self, request):
            captured["request"] = request
            return SimpleNamespace(text=json.dumps(raw), errors=[], error_category=None)

    monkeypatch.setattr(generator_module, "get_chapter_evidence_bundle", lambda *_: bundle)
    monkeypatch.setattr("bhf_agent.adapters.factory.build_chat_adapter", lambda config: Adapter())
    config = AgentConfig(adapter="claude_cli", model="configured-model")
    result = generator_module.CommentaryGenerator(config).generate(
        CommentaryGenerationRequest(
            book="Genesis", chapter=1, reference="Genesis 1", evidence_hash=bundle.evidence_hash
        )
    )
    assert result.status == CommentaryStatus.VALIDATED.value
    assert result.commentary.generated_metadata.model == "configured-model"
    assert result.commentary.generated_metadata.generated_timestamp
    assert captured["request"].max_tokens == 4500


def test_old_commentary_prompt_version_is_stale():
    bundle = _bundle()
    value = _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle)]}])
    value["generated_metadata"]["commentary_prompt_version"] = "1.0"
    result = validate_chapter_commentary(value, bundle, expected_prompt_version=COMMENTARY_PROMPT_VERSION)
    assert not result.valid
    assert any("prompt_version" in error for error in result.errors)


def test_progress_rescan_reconstructs_counts_and_pending():
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        for chapter, status, prompt_version in [
            (1, "validated", COMMENTARY_PROMPT_VERSION),
            (2, "partial", COMMENTARY_PROMPT_VERSION),
            (3, "needs_review", COMMENTARY_PROMPT_VERSION),
            (4, "failed", COMMENTARY_PROMPT_VERSION),
            (5, "validated", "1.0"),
        ]:
            bundle = _bundle()
            save_commentary(ChapterCommentary(
                reference=f"Genesis {chapter}", book="Genesis", chapter=chapter,
                status=status,
                generated_metadata=GeneratedMetadata(
                    evidence_hash=bundle.evidence_hash,
                    evidence_bundle_version="1.0",
                    commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
                    commentary_prompt_version=prompt_version,
                    model="test", generated_timestamp="now",
                ),
            ), tmpdir)
        progress = builder.rescan_progress(check_evidence=False)
        assert (progress.validated, progress.partial, progress.needs_review, progress.failed, progress.stale) == (1, 1, 1, 1, 1)
        assert progress.pending == 1184
        assert progress.completed == 5


def test_resume_regenerates_partial_by_default(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        chapters = [("Genesis", 1)]
        bundle = _bundle()
        monkeypatch.setattr(builder, "discover_canonical_chapters", lambda: chapters)
        monkeypatch.setattr("bhf_agent.chapter_commentary.builder.get_chapter_evidence_bundle", lambda *_: bundle)
        save_commentary(ChapterCommentary(
            reference="Genesis 1", book="Genesis", chapter=1, status="partial",
            generated_metadata=GeneratedMetadata(bundle.evidence_hash, "1.0", COMMENTARY_SCHEMA_VERSION, COMMENTARY_PROMPT_VERSION, "test", "now"),
        ), tmpdir)
        calls = []
        class Fake:
            def generate(self, request):
                calls.append(request)
                return _FakeGenerator().generate(request)
        builder.generator = Fake()
        builder.build_all(resume=True)
        assert len(calls) == 1


def test_resume_skips_current_validated(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        bundle = _bundle()
        monkeypatch.setattr(builder, "discover_canonical_chapters", lambda: [("Genesis", 1)])
        monkeypatch.setattr("bhf_agent.chapter_commentary.builder.get_chapter_evidence_bundle", lambda *_: bundle)
        save_commentary(ChapterCommentary(
            reference="Genesis 1", book="Genesis", chapter=1, status="validated",
            generated_metadata=GeneratedMetadata(bundle.evidence_hash, "1.0", COMMENTARY_SCHEMA_VERSION, COMMENTARY_PROMPT_VERSION, "test", "now"),
        ), tmpdir)
        class Fake:
            def generate(self, request):
                raise AssertionError("current validated chapter was regenerated")
        builder.generator = Fake()
        progress = builder.build_all(resume=True)
        assert progress.validated == 1


def test_failed_generation_attempt_is_recorded_in_progress(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = CommentaryBuilder(tmpdir)
        bundle = _bundle()
        monkeypatch.setattr(builder, "discover_canonical_chapters", lambda: [("Genesis", 1)])
        monkeypatch.setattr("bhf_agent.chapter_commentary.builder.get_chapter_evidence_bundle", lambda *_: bundle)
        class Fake:
            def generate(self, request):
                commentary = ChapterCommentary(
                    reference=request.reference, book=request.book, chapter=request.chapter,
                    status=CommentaryStatus.NEEDS_REVIEW.value,
                    generated_metadata=GeneratedMetadata(bundle.evidence_hash, "1.0", COMMENTARY_SCHEMA_VERSION, COMMENTARY_PROMPT_VERSION, "test", "now"),
                    failure_reason="test failure",
                )
                return CommentaryGenerationResult(request.reference, commentary.status, commentary, "test failure")
        builder.generator = Fake()
        progress = builder.build_all(resume=True)
        assert progress.needs_review == 1
        assert progress.pending == 0


@pytest.mark.parametrize("verse_ref,code", [
    ("Genesis 1:one", CommentaryRejectionCode.MALFORMED_VERSE_REFERENCE.value),
    ("Genesis 1:1-", CommentaryRejectionCode.MALFORMED_VERSE_REFERENCE.value),
    ("Genesis 2:1", CommentaryRejectionCode.OUT_OF_CHAPTER_VERSE_REFERENCE.value),
])
def test_malformed_and_out_of_chapter_verse_references_are_rejected(verse_ref, code):
    bundle = _bundle()
    result = validate_chapter_commentary(
        _raw_commentary(bundle, [{"kind": "chapter_overview", "title": "Overview", "blocks": [_block(bundle, verse_ref=verse_ref)]}]),
        bundle,
    )
    assert code in result.section_results[0].block_results[0].reason_codes
