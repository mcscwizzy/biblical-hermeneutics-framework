"""Regression coverage for the explicit current Commentary v1.2 baseline."""

from __future__ import annotations

import json
from pathlib import Path

from framework.commentary.v12_current_lineage import (
    CURRENT_LINEAGE_REL,
    HISTORICAL_QUALIFICATION_REL,
    HISTORICAL_SCALE_REL,
    build,
    load_manifest,
    record_context,
)


ROOT = Path(__file__).resolve().parents[1]


def _rows(kind: str) -> dict[str, dict]:
    manifest = load_manifest(ROOT)
    return {row["reference"]: row for row in manifest[kind]["chapters"]}


def test_current_lineage_rebuild_is_deterministic_and_explicit():
    """Current CKL identities include the explicit post-Transaction-A drift."""

    stored = load_manifest(ROOT)
    current = build(ROOT)["manifest"]

    assert stored["manifest_identity"] == "e090d26eabfe2a7db20381fb4c511812b248180958346fbc015c3aed9c432bf1"
    assert current["manifest_identity"] == "e3674534fb1acf0141a602cc602857f084cb2b5198f03967ea4e0e8b1bef8ea5"
    assert current["manifest_identity"] != stored["manifest_identity"]

    expected_changes = {
        "John 2": (
            "f8f1e3ff98d5ee3540eab7ff1320e3ca9f8284f32e228e4c27e820cc7c811cde",
            "08a0963fbb995e8a8462d9c4f4057a78f7d09bb122471eeee5ca1d5fedd43ca3",
            "7f546cc7da0a2832689555bf4fd5220d177b9a4a6d4810b08158f47e9da68b0b",
            "080fedaa506f0121ea4bba9cd063a5d6f412752bf2b3f4d2146652f7f76e4a26",
        ),
        "Jeremiah 49": (
            "a8e1ab56d7cbae06cd3a7fe35b6c07d60a6f7dc0eebae1e1ce1b62bff531b392",
            "ed6af372885a844f3c1dc2ffafa3e56bfe68c56a94b778c788f950a01f884972",
            "b8589c6fa8934cea85bd416aa90c028aa82d98bb31dbd7c399b25c2cffd4d31c",
            "37d17ffe688acf7575937f16217f0e800273c4c2b27121798f02c75226de2730",
        ),
        "Acts 27": (
            "43fab16887c84e08998867bfda7d0a272b276965f4d46b079f2613d81fa556db",
            "ff14fba83fb2c7718d454252c70d64649e0901dabee5d2dd4ca12f860a601f78",
            "62bade47f701b4a49eee5cc595723774ead0772970780af5a4b74bcec3075a9d",
            "e763b6c025da056653022115b1799b21ad51d82e348a491936df211bede85a2a",
        ),
    }
    previous = {row["reference"]: row for row in stored["scale_pilot"]["chapters"]}
    rebuilt = {row["reference"]: row for row in current["scale_pilot"]["chapters"]}
    changed_references = {
        reference for reference in previous if previous[reference] != rebuilt[reference]
    }
    assert changed_references == set(expected_changes)
    for reference, expected in expected_changes.items():
        old, new = previous[reference], rebuilt[reference]
        assert (
            old["evidence_hash"], new["evidence_hash"],
            old["synthesis_hash"], new["synthesis_hash"],
        ) == expected


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


def test_frozen_lineage_record_is_preserved_as_a_pre_transaction_a_baseline():
    """The pre-Transaction-A source contract remains a separate frozen record."""

    record = record_context(ROOT, "scale_pilot", "Acts 27")

    assert record["row"]["evidence_hash"] == "43fab16887c84e08998867bfda7d0a272b276965f4d46b079f2613d81fa556db"
    assert record["row"]["synthesis_hash"] == "62bade47f701b4a49eee5cc595723774ead0772970780af5a4b74bcec3075a9d"


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
