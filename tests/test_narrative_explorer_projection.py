"""Contract tests for the read-only Narrative Explorer projection."""

from copy import deepcopy
from importlib import import_module
from importlib.util import find_spec

import pytest


def test_projection_adapter_module_is_available():
    assert find_spec("bhf_agent.presentation.narrative_explorer") is not None


def _public(name):
    module = import_module("bhf_agent.presentation.narrative_explorer")
    value = getattr(module, name, None)
    assert value is not None, f"public adapter contract {name!r} is missing"
    return value


def _lookup(domain, *, records=(), query_status="complete", reason_code=None):
    domain_lookup = _public("DomainLookup")
    return domain_lookup(
        domain=domain,
        records=records,
        query_status=query_status,
        reason_code=reason_code,
    )


def _project(reference, *, canonical=None, maps=None, archaeology=None):
    project = _public("project_narrative_explorer")
    return project(
        reference,
        canonical_lookup=canonical or _lookup("ckl"),
        map_lookup=maps,
        archaeology_lookup=archaeology,
    ).to_dict()


def test_projection_normalizes_chapter_and_verse_range_and_exposes_v1_envelope():
    result = _project(
        "Gen 6",
        maps=_lookup("maps", query_status="failed", reason_code="resolver_unavailable"),
        archaeology=_lookup("archaeology"),
    )

    assert set(result) == {
        "schema_version",
        "passage",
        "coverage",
        "sections",
        "items",
        "connections",
        "navigation",
    }
    assert result["schema_version"] == "1.0"
    assert result["passage"] == {
        "reference": "Genesis 6",
        "book": "Genesis",
        "chapter": 6,
        "verse_start": None,
        "verse_end": None,
        "scope": "chapter",
    }
    coverage = {item["domain"]: item for item in result["coverage"]}
    assert coverage["ckl"]["source_domain"] == "canonical_knowledge_library"
    assert coverage["ckl"]["state"] == "not_represented"
    assert coverage["maps"]["state"] == "unknown"
    assert coverage["maps"]["reason_code"] == "resolver_unavailable"
    assert coverage["archaeology"]["state"] == "not_represented"

    verse_result = _project("Genesis 6:1-4")
    assert verse_result["passage"] == {
        "reference": "Genesis 6:1-4",
        "book": "Genesis",
        "chapter": 6,
        "verse_start": 1,
        "verse_end": 4,
        "scope": "verse_range",
    }


@pytest.mark.parametrize("reference", ["", "Genesis", "Genesis 6:0", "Genesis 1-2"])
def test_projection_rejects_invalid_or_unsupported_passage_scope(reference):
    with pytest.raises(ValueError):
        _project(reference)


def test_projection_is_stable_and_does_not_mutate_supplied_records():
    records = [
        {
            "id": "book-fixture",
            "type": "book",
            "title": "Genesis",
            "scripture_references": [{"reference": "Genesis 6:1-22", "relationship": "primary"}],
            "sources": [{"id": "genesis-source", "title": "Genesis", "year": None}],
            "private_notes": ["must not cross the projection boundary"],
        }
    ]
    before = deepcopy(records)
    lookup = _lookup("ckl", records=records)

    first = _project("Genesis 6", canonical=lookup)
    second = _project("Genesis 6", canonical=lookup)

    assert first == second
    assert records == before
