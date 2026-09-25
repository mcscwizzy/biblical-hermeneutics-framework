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
from framework.canonical_library.schema import CanonicalObject, CanonicalValidationError, validate_library
from tests.canonical_library.helpers import make_object


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


def test_legacy_canonical_object_omits_absent_target_field() -> None:
    raw = json.loads(LEGACY_OBJECT.read_text(encoding="utf-8"))
    result = CanonicalObject.from_mapping(raw).to_dict()
    assert "evidence_targets" not in result["evidence_items"][0]
    assert [canonical_json_hash(item) for item in result["evidence_items"]] == [
        canonical_json_hash(item) for item in raw["evidence_items"]
    ]


def test_raw_object_builder_keeps_mapping_evidence_payloads() -> None:
    raw = evidence_mapping_without_targets()
    result = make_object("bethlehem", "place", "Bethlehem", ["Bethlehem of Judah"], evidence_items=[raw])
    assert result["evidence_items"] == [raw]


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


def _entity(relationship: str, entity_id: str, **metadata: object) -> dict[str, object]:
    return {"kind": "entity", "relationship": relationship, "entity_id": entity_id, **metadata}


def _entitlement(relationship: str, value: str, domain: str) -> dict[str, object]:
    return {
        "kind": "value", "relationship": relationship, "value_type": "entitlement",
        "normalized_value": value, "display_value": value.title(),
        "qualifiers": [{"kind": "domain", "normalized_value": domain}],
    }


def _object_with_targets(
    targets: list[dict[str, object]], *, subject_id: str = "bethlehem",
    subject_type: str = "place", temporal_scope: dict[str, object] | None = None,
) -> CanonicalObject:
    original = json.loads(LEGACY_OBJECT.read_text(encoding="utf-8"))
    evidence = dict(original["evidence_items"][0])
    evidence.update(
        source_ids=[original["sources"][0]["id"]], related_objects=[],
        related_evidence=[], geography_ids=[], claim_ids=[], evidence_targets=targets,
    )
    if temporal_scope is not None:
        evidence["temporal_scope"] = temporal_scope
    source = {**original["sources"][0], "supports": []}
    raw = make_object(
        subject_id, subject_type, subject_id.title(), [f"alias for {subject_id}"],
        sources=[source], evidence_items=[evidence],
    )
    return CanonicalObject.from_mapping(raw)


def _target_object(entity_id: str, type_name: str = "place") -> CanonicalObject:
    return CanonicalObject.from_mapping(make_object(
        entity_id, type_name, entity_id.title(), [f"alias for {entity_id}"],
    ))


@pytest.mark.parametrize(
    ("targets", "target_objects", "subject_id", "subject_type"),
    [
        ([_entity("encamped-between", "socoh-1", role="boundary"), _entity("encamped-between", "azekah", role="boundary")], ["socoh-1", "azekah"], "camp", "place"),
        ([_entity("river-water-context", "abana", role="compared-river"), _entity("river-water-context", "pharpar", role="compared-river")], ["abana", "pharpar"], "damascus", "place"),
        ([_entity("narrated-navigation-markers", "myra", role="reached", sequence=1), _entity("narrated-navigation-markers", "crete", role="passed", sequence=2)], ["myra", "crete"], "sidon", "place"),
        ([_entity("ruled-by", "archelaus")], ["archelaus"], "judea", "place"),
        ([_entity("located-in", "judea")], ["judea"], "bethlehem", "place"),
        ([_entity("near", "sychar")], ["sychar"], "well", "place"),
        ([_entitlement("territorial-inheritance", "none", "territorial")], [], "levites", "institution"),
        ([_entitlement("tithe-as-inheritance", "tithe", "economic")], [], "levites", "institution"),
    ],
)
def test_registered_target_relationships_validate(
    targets: list[dict[str, object]], target_objects: list[str], subject_id: str, subject_type: str,
) -> None:
    objects = [_object_with_targets(targets, subject_id=subject_id, subject_type=subject_type)]
    objects.extend(_target_object(entity_id, "person" if entity_id == "archelaus" else "place") for entity_id in target_objects)
    validate_library(objects)


@pytest.mark.parametrize(
    ("targets", "target_objects", "subject_id", "subject_type", "temporal_scope", "message"),
    [
        ([_entity("encamped-between", "socoh-1", role="boundary")], ["socoh-1"], "camp", "place", None, "exactly two"),
        ([_entity("narrated-navigation-markers", "myra", role="reached", sequence=1), _entity("narrated-navigation-markers", "crete", role="passed", sequence=1)], ["myra", "crete"], "sidon", "place", None, "unique positive sequence"),
        ([_entitlement("territorial-inheritance", "none", "economic")], [], "levites", "institution", None, "domain=territorial"),
        ([_entitlement("territorial-inheritance", "none", "territorial")], [], "levites", "institution", {}, "temporal scope"),
        ([_entity("near", "missing-place")], [], "bethlehem", "place", None, "missing-place"),
        ([_entity("ruled-by", "judea")], ["judea"], "bethlehem", "place", None, "person"),
        ([_entity("located-in", "judea")], ["judea"], "levites", "institution", None, "place subject"),
        ([_entitlement("tithe-as-inheritance", "tithe", "economic")], [], "bethlehem", "place", None, "levites"),
    ],
)
def test_target_relationship_compatibility_fails_closed(
    targets: list[dict[str, object]], target_objects: list[str], subject_id: str,
    subject_type: str, temporal_scope: dict[str, object] | None, message: str,
) -> None:
    with pytest.raises(CanonicalValidationError, match=message):
        objects = [_object_with_targets(
            targets, subject_id=subject_id, subject_type=subject_type,
            temporal_scope=temporal_scope,
        )]
        objects.extend(_target_object(entity_id) for entity_id in target_objects)
        validate_library(objects)


def test_library_rejects_unresolved_qualifier_entity() -> None:
    target = _entitlement("territorial-inheritance", "none", "territorial")
    target["qualifiers"].append({"kind": "contextual-addressee", "entity_id": "missing-person"})
    with pytest.raises(CanonicalValidationError, match="missing-person"):
        validate_library([_object_with_targets([target], subject_id="levites", subject_type="institution")])
