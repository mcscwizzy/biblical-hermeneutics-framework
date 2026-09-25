"""Typed evidence target and legacy wire-format contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from framework import canonical_library as public_ckl
from framework.canonical_library.evidence_models import (
    CanonicalEvidenceItem,
    EvidenceValidationError,
    validate_evidence_targets,
)


ROOT = Path(__file__).resolve().parents[2]
LEGACY_OBJECT = ROOT / "framework/canonical_library/objects/events/david-and-goliath.json"


def evidence_mapping_without_targets() -> dict[str, object]:
    return json.loads(LEGACY_OBJECT.read_text(encoding="utf-8"))["evidence_items"][0]


def evidence_mapping(*, evidence_targets: list[dict[str, object]]) -> dict[str, object]:
    return {**evidence_mapping_without_targets(), "evidence_targets": evidence_targets}


def canonical_json_hash(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def test_legacy_evidence_targets_are_empty_in_memory_but_omitted_on_output() -> None:
    raw = evidence_mapping_without_targets()
    item = CanonicalEvidenceItem.from_mapping(raw)

    assert item.evidence_targets == []
    assert "evidence_targets" not in item.to_dict()
    assert canonical_json_hash(item.to_dict()) == canonical_json_hash(raw)


def test_entity_and_value_targets_have_canonical_shapes() -> None:
    targets = [
        {"kind": "entity", "relationship": "near", "entity_id": "sychar"},
        {
            "kind": "value",
            "relationship": "territorial-inheritance",
            "value_type": "entitlement",
            "normalized_value": "none",
            "display_value": "No inheritance among Israel",
            "qualifiers": [
                {"kind": "domain", "normalized_value": "territorial"},
                {"kind": "contextual-addressee", "entity_id": "aaron"},
            ],
        },
    ]
    item = CanonicalEvidenceItem.from_mapping(evidence_mapping(evidence_targets=targets))

    assert [target.to_dict() for target in item.evidence_targets] == targets
    assert item.to_dict()["evidence_targets"] == targets


@pytest.mark.parametrize(
    ("targets", "message"),
    [
        ([{"kind": "unknown", "relationship": "near", "entity_id": "sychar"}], "kind"),
        ([{"kind": "entity", "relationship": "near", "entity_id": "sychar", "junk": 1}], "unknown"),
        ([{"kind": "entity", "relationship": "Near", "entity_id": "sychar"}], "kebab-case"),
        ([{"kind": "entity", "relationship": "near", "entity_id": "Sychar"}], "kebab-case"),
        ([{"kind": "value", "relationship": "near", "value_type": "entitlement", "normalized_value": "land", "display_value": "Land", "qualifiers": []}], "normalized_value"),
        ([{"kind": "value", "relationship": "near", "value_type": "unknown", "normalized_value": "none", "display_value": "None", "qualifiers": []}], "value_type"),
        ([{"kind": "value", "relationship": "near", "value_type": "entitlement", "normalized_value": "none", "display_value": "None", "qualifiers": [{"kind": "unknown", "normalized_value": "territorial"}]}], "qualifier"),
        ([{"kind": "value", "relationship": "near", "value_type": "entitlement", "normalized_value": "none", "display_value": "None", "qualifiers": [{"kind": "domain", "normalized_value": "territorial", "entity_id": "aaron"}]}], "exactly one"),
        ([{"kind": "value", "relationship": "near", "value_type": "entitlement", "normalized_value": "none", "display_value": "None", "qualifiers": [{"kind": "domain"}]}], "exactly one"),
        ([{"kind": "entity", "relationship": "near", "entity_id": "sychar"}] * 2, "duplicate"),
    ],
)
def test_invalid_targets_fail_closed(targets: list[dict[str, object]], message: str) -> None:
    with pytest.raises(EvidenceValidationError, match=message):
        validate_evidence_targets(targets)


def test_explicit_empty_targets_remain_explicit() -> None:
    item = CanonicalEvidenceItem.from_mapping(evidence_mapping(evidence_targets=[]))
    assert item.to_dict()["evidence_targets"] == []


def test_default_constructed_item_omits_empty_target_field() -> None:
    item = CanonicalEvidenceItem(
        id="test", title="Test", evidence_type="other", description="Test",
        assertion_type="primary-evidence", confidence="high",
        confidence_rationale="Direct", passage_relevance="Direct",
    )
    assert "evidence_targets" not in item.to_dict()


def test_nonempty_targets_survive_json_round_trip() -> None:
    raw = evidence_mapping(evidence_targets=[
        {"kind": "entity", "relationship": "near", "entity_id": "sychar"}
    ])
    item = CanonicalEvidenceItem.from_mapping(raw)
    assert CanonicalEvidenceItem.from_mapping(json.loads(json.dumps(item.to_dict()))).to_dict() == raw


def test_public_ckl_api_exposes_typed_target_parser() -> None:
    parsed = public_ckl.validate_evidence_targets([
        {"kind": "entity", "relationship": "near", "entity_id": "sychar"}
    ])
    assert isinstance(parsed[0], public_ckl.CanonicalEntityEvidenceTarget)
