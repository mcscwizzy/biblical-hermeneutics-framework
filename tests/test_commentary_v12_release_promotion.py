import hashlib
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.release import release_chapter_state, release_diagnostics
from bhf_agent.runtime_paths import (
    DEFAULT_COMMENTARY_RELEASE,
    configured_commentary_release,
    default_commentary_storage_path,
)
from tools.commentary_v12_release_promotion import (
    DEFAULT_ARTIFACT,
    _row_is_publishable,
    verify_validation_artifact,
)
from tools.commentary_v12_release import (
    ReconciliationError,
    _effective_audits,
    _validate_audits,
    _validate_presentation_audit,
    build_reconciliation_inventory,
)
from bhf_agent.chapter_commentary.selection_sufficiency import (
    LEGACY_SELECTION_EXCEPTION_DECISION,
    LEGACY_SELECTION_EXCEPTION_VERSION,
    SELECTION_SUFFICIENCY_VERSION,
    _hash_json,
)


RELEASE_ROOT = Path(".bhf-data/bhf-commentary-v1.2")


def test_validation_intersection_is_calculated_from_per_chapter_records():
    info = verify_validation_artifact(DEFAULT_ARTIFACT)
    published = [row for row in info["population"] if _row_is_publishable(row)]

    assert len(published) == 62
    assert len(info["population"]) == 75
    assert {row["failure_classification"] for row in published} <= {
        None,
        "UNDER_EXPLANATION",
        "SOURCE_LIMITED",
    }


def _technically_publishable_row():
    return {
        "reference": "Genesis 1",
        "generated": True,
        "structural_result": "ACCEPTED",
        "provenance_result": "PASS",
        "ancestry_result": "PASS",
        "gate_result": "PASS",
        "readability_result": "PASS",
        "normal_reader_usefulness": "PASS",
        "high_dump": False,
        "provider_failure": False,
        "unsupported_claim_findings": [],
        "parse_status": "JSON_OBJECT",
        "evidence_hash": "locked-evidence",
        "synthesis_hash": "locked-synthesis",
        "raw_response_sha256": "locked-raw",
    }


def _legacy_identity():
    return {
        "reference": "Genesis 1",
        "evidence_hash": "locked-evidence",
        "synthesis_hash": "locked-synthesis",
        "raw_response_sha256": "locked-raw",
        "commentary_sha256": "locked-commentary",
    }


def _legacy_exception(identity):
    return {
        "artifact_version": LEGACY_SELECTION_EXCEPTION_VERSION,
        "decision": LEGACY_SELECTION_EXCEPTION_DECISION,
        "reviewer": "reviewer@example.org",
        "reviewed_at": "2026-10-14T12:00:00Z",
        "rationale": "Reviewed this frozen legacy chapter against its locked source lineage.",
        "source_identity": identity,
    }


def test_75_chapter_promotion_requires_selection_pass_or_source_bound_legacy_exception():
    row = _technically_publishable_row()
    identity = _legacy_identity()
    assert _row_is_publishable(row) is False
    assert _row_is_publishable(
        row,
        selection_source_identity=identity,
        legacy_selection_exception=_legacy_exception(identity),
    ) is True

    failed = dict(row, selection_sufficiency={"status": "FAIL"})
    assert _row_is_publishable(
        failed,
        selection_source_identity=identity,
        legacy_selection_exception=_legacy_exception(identity),
    ) is False

    wrong_exception = _legacy_exception(dict(identity, commentary_sha256="other"))
    assert _row_is_publishable(
        row,
        selection_source_identity=identity,
        legacy_selection_exception=wrong_exception,
    ) is False


def test_corpus_release_requires_valid_selection_receipt_or_legacy_exception():
    identity = {
        "reference": "Genesis 1",
        "evidence_hash": "locked-evidence",
        "synthesis_hash": "locked-synthesis",
        "prompt_version": "1.8",
        "commentary_schema_version": "1.2",
        "raw_response_sha256": "locked-raw",
        "commentary_sha256": "locked-commentary",
    }
    unsigned = {
        "assessment_version": SELECTION_SUFFICIENCY_VERSION,
        "status": "PASS",
        "source_identity": identity,
    }
    assessment = {**unsigned, "assessment_hash": _hash_json(unsigned)}
    audits = {
        "ancestry": {"valid": True},
        "provenance_binding": {"valid": True},
        "envelope": {"valid": True, "ancestry_audit": {}},
        "selection_sufficiency": assessment,
    }
    assert _validate_audits(
        "Genesis 1", audits, require_selection=True,
        selection_source_identity=identity,
    ) is None

    tampered = {**assessment, "status": "FAIL"}
    with pytest.raises(ReconciliationError, match="RENDERER_SELECTION_COLLAPSE"):
        _validate_audits(
            "Genesis 1",
            {**audits, "selection_sufficiency": tampered},
            require_selection=True,
            legacy_exception=_legacy_exception(identity),
            selection_source_identity=identity,
        )

    exception = _validate_audits(
        "Genesis 1",
        {key: value for key, value in audits.items() if key != "selection_sufficiency"},
        require_selection=True,
        legacy_exception=_legacy_exception(
            {
                key: value
                for key, value in identity.items()
                if key in {
                    "reference", "evidence_hash", "synthesis_hash",
                    "raw_response_sha256", "commentary_sha256",
                }
            }
        ),
        selection_source_identity={
            key: value
            for key, value in identity.items()
            if key in {
                "reference", "evidence_hash", "synthesis_hash",
                "raw_response_sha256", "commentary_sha256",
            }
        },
    )
    assert exception["decision"] == LEGACY_SELECTION_EXCEPTION_DECISION


def test_finalize_audit_sidecar_supersedes_older_embedded_audit_fields(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"audits": {"quality": {"old": True}}}))
    (tmp_path / "finalize-audit.json").write_text(
        json.dumps({"selection_sufficiency": {"status": "FAIL"}})
    )
    audits = _effective_audits(result_path, json.loads(result_path.read_text()))
    assert audits["quality"] == {"old": True}
    assert audits["selection_sufficiency"]["status"] == "FAIL"


def test_v12_release_requires_presentation_gate_separately_from_selection():
    assert _validate_presentation_audit("Genesis 1", {})[0] is False
    audits = {
        "presentation_quality": {
            "contract_version": "commentary-richness-gate-v2.1",
            "status": "PASS_WITH_WARNING",
            "assessment": {"outcome": "PASS_WITH_WARNING", "safety_pass": True},
        }
    }
    assert _validate_presentation_audit("Genesis 1", audits) == (True, None)
    with pytest.raises(ReconciliationError, match="QUALITY_FAIL"):
        _validate_presentation_audit(
            "Genesis 1",
            {
                "presentation_quality": {
                    "contract_version": "commentary-richness-gate-v2.1",
                    "status": "QUALITY_FAIL",
                    "assessment": {"outcome": "QUALITY_FAIL", "safety_pass": True},
                }
            },
        )


def test_packaged_v12_manifest_and_checksums_are_reader_safe():
    if not RELEASE_ROOT.is_dir():
        pytest.skip("the local release candidate has not been promoted")
    manifest = json.loads((RELEASE_ROOT / ".bhf-commentary-release.json").read_text())

    assert manifest["release"] == "commentary-v1.2"
    assert manifest["published_chapter_count"] == 972
    assert manifest["validated_population_count"] == 1189
    assert manifest["unavailable_not_published_count"] == 217
    assert len(manifest["chapter_publication_index"]) == 1189
    assert manifest["terminal_state_counts"] == {
        "MODEL_OUTPUT_REJECTED": 26,
        "NOT_RENDERABLE_SOURCE_LIMITED": 185,
        "PUBLISHED": 972,
        "QUALITY_REVIEW_REQUIRED": 6,
    }
    assert len(list(RELEASE_ROOT.glob("*.json"))) == 974
    assert release_diagnostics(RELEASE_ROOT, "commentary-v1.2")["checksum_status"] == "valid"


def test_v12_states_distinguish_rejected_and_outside_chapters():
    if not RELEASE_ROOT.is_dir():
        pytest.skip("the local release candidate has not been promoted")

    assert release_chapter_state(RELEASE_ROOT, "Romans", 3)["release_state"] == "MODEL_OUTPUT_REJECTED"
    assert release_chapter_state(RELEASE_ROOT, "Galatians", 3)["release_state"] == "QUALITY_REVIEW_REQUIRED"
    assert release_chapter_state(RELEASE_ROOT, "Genesis", 1)["release_state"] == "PUBLISHED"


def test_v12_is_opt_in_and_vercel_resolves_packaged_path():
    assert DEFAULT_COMMENTARY_RELEASE == "commentary-v1.1"
    assert configured_commentary_release({}) == "commentary-v1.1"
    assert configured_commentary_release({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"}) == "commentary-v1.2"
    resolved = default_commentary_storage_path({"VERCEL": "1", "BHF_COMMENTARY_RELEASE": "commentary-v1.2"})
    assert resolved.name == "bhf-commentary-v1.2"
    assert "bhf-commentary-candidates" not in str(resolved)


def test_full_corpus_reconciliation_inventory_is_complete_and_generation_free():
    inventory = build_reconciliation_inventory()

    assert len(inventory["canonical"]) == 1189
    assert inventory["runner_result_count"] == 1114
    assert inventory["counts"] == {
        "MODEL_OUTPUT_REJECTED": 26,
        "NOT_RENDERABLE_SOURCE_LIMITED": 185,
        "PUBLISHED": 972,
        "QUALITY_REVIEW_REQUIRED": 6,
    }
    manifest = json.loads((RELEASE_ROOT / ".bhf-commentary-release.json").read_text())
    assert manifest["generation_performed"] is False
    assert manifest["promotion_mode"] == "deterministic_finalized_artifact_reconciliation"


def test_promotion_checksum_tampering_fails_closed(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    source = DEFAULT_ARTIFACT / "frozen-population.json"
    target = artifact / source.name
    target.write_bytes(source.read_bytes() + b"tamper")
    checksums = {"files": {source.name: hashlib.sha256(source.read_bytes()).hexdigest()}}
    (artifact / "checksums-v2.json").write_text(json.dumps(checksums))

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        verify_validation_artifact(artifact)
