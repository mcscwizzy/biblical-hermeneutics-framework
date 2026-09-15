"""Regression coverage for the explicit current Commentary v1.2 baseline."""

from __future__ import annotations

import json
from pathlib import Path

from framework.commentary.v12_current_lineage import (
    CURRENT_LINEAGE_REL,
    HISTORICAL_QUALIFICATION_REL,
    HISTORICAL_SCALE_REL,
    load_manifest,
    record_context,
    verify,
)


ROOT = Path(__file__).resolve().parents[1]


def _rows(kind: str) -> dict[str, dict]:
    manifest = load_manifest(ROOT)
    return {row["reference"]: row for row in manifest[kind]["chapters"]}


def test_current_lineage_rebuild_is_deterministic_and_explicit():
    """A source change must fail verification; it cannot update the fixture."""

    result = verify(ROOT)

    assert result == {
        "status": "CURRENT_LINEAGE_VALID",
        "manifest_identity": "e090d26eabfe2a7db20381fb4c511812b248180958346fbc015c3aed9c432bf1",
    }


def test_current_lineage_supersedes_but_does_not_modify_historical_baselines():
    manifest = load_manifest(ROOT)
    historical_qualification = json.loads(
        (ROOT / HISTORICAL_QUALIFICATION_REL / "qualification-manifest.json").read_text()
    )
    historical_scale = json.loads(
        (ROOT / HISTORICAL_SCALE_REL / "manifest.json").read_text()
    )

    assert (ROOT / CURRENT_LINEAGE_REL).is_dir()
    assert historical_qualification["manifest_identity"] == "d504d1361f872efdf4336b4de55339e18126c17d74e991107adcb5e19d553612"
    assert historical_scale["manifest_identity"] == "eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394"
    assert manifest["supersedes"]["qualification_manifest_identity"] == historical_qualification["manifest_identity"]
    assert manifest["supersedes"]["scale_pilot_manifest_identity"] == historical_scale["manifest_identity"]
    assert manifest["supersedes"]["lineage_commits"] == [
        "5c00d961809dbdfe652af0d5908d53831a05c8ca",
        "3522c0dbf748e2edca2f2ce68d52dcf3ea584833",
    ]


def test_migration_census_classifies_every_identity_difference():
    report = json.loads((ROOT / CURRENT_LINEAGE_REL / "migration-report.json").read_text())

    assert report["unexplained_differences"] == []
    assert report["qualification"]["changes"] == {
        "EVIDENCE_APPLICABILITY_REBASE": 15,
        "UNCHANGED": 6,
    }
    assert report["scale_pilot"]["changes"] == {
        "EVIDENCE_APPLICABILITY_REBASE": 47,
        "SOURCE_BOUNDARY_REBASE": 5,
        "UNCHANGED": 23,
    }


def test_isaiah_and_romans_use_the_current_authoritative_source_identities():
    isaiah = record_context(ROOT, "qualification", "Isaiah 13")["row"]
    romans = record_context(ROOT, "scale_pilot", "Romans 3")["row"]

    assert isaiah["synthesis_hash"] == "5fa266c6aa55616b43d212528661b5b03a4deef6b4617c32bfe66eed1d938eed"
    assert isaiah["source_packet_hash"] == "050ae3f5013742edb64710a3d5f8b064c683bb6e03d35b646e791ba5a4da223d"
    assert romans["synthesis_hash"] == "a464b95b7aca4f8cdb711e4c1c930ad06a0590598f3f67cb971e2a56b9bfdb53"
    assert romans["source_packet_hash"] == "8591e517180a8a43e2a3fa4d31dc1cb1fc80366ede02a1fdcc4156207a3eb4c9"


def test_boundary_repaired_rows_have_current_evidence_identities():
    rows = _rows("scale_pilot")

    assert {reference for reference, row in rows.items()
            if row["migration_reason"] == "SOURCE_BOUNDARY_REBASE"} == {
        "Genesis 5", "2 Kings 4", "Psalms 2", "Psalms 19", "Psalms 103"
    }
    for reference in ("Genesis 5", "2 Kings 4", "Psalms 2", "Psalms 19", "Psalms 103"):
        assert rows[reference]["evidence_hash"] != rows[reference]["historical_identity"]["evidence_hash"]
