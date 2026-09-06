from __future__ import annotations

import json

from tools.ckl_scope_audit import population_report


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_corpus_accounting_excludes_initial_canary_certifications(tmp_path):
    scale = tmp_path / "scale"
    canary = tmp_path / "commentary-v1.1"
    _write(scale / "batch-001/batch-manifest.json", {"final_references": ["Genesis 1", "Exodus 1"]})
    _write(
        scale / ".batch-007.work/population.json",
        {
            "report": {
                "records": [{"reference": ref} for ref in ("Genesis 1", "Exodus 1", "Leviticus 1", "Numbers 1")],
                "chapters_evidence_supports_regeneration": ["Genesis 1", "Exodus 1", "Leviticus 1"],
                "chapters_evidence_insufficient": ["Numbers 1"],
            }
        },
    )
    _write(
        canary / "evidence-certification-commentary_canary.json",
        {"chapters": [{"reference": "Leviticus 1"}]},
    )
    _write(canary / "evidence-certification-supplemental-controls.json", {"reference": "Numbers 1"})
    _write(canary / "evidence-certification-thin_initial.json", {"chapters": [{"reference": "Exodus 1"}]})

    report = population_report(scale, canary)

    assert report["counts"] == {
        "canary": 2,
        "eligible": 3,
        "eligible_finalized": 3,
        "finalized_total": 4,
        "historical_quarantine": 0,
        "insufficient_or_intentionally_excluded": 1,
        "intentional_exclusions": 1,
        "low_information": 4,
        "regular_generated": 2,
        "unresolved_eligible": 0,
    }
    assert report["set_relationships"]["finalized_outside_eligible"] == ["Numbers 1"]
