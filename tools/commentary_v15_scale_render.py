#!/usr/bin/env python3
"""Render one locked Commentary 1.5 scale-pilot wave with the current Codex renderer."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.synthesis import load_synthesis
from bhf_agent.chapter_commentary.richness_clusters import cluster_synthesis_units


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot"
RENDERER_LABEL = "GPT-5 Codex"
REASONING_EFFORT = "NOT_EXPOSED"
_RANK = {"CORE": 4, "DISPUTED": 3, "SUPPORTING": 2, "SURROUNDING": 1, "OPTIONAL": 0}
_CONFIDENCE = {"low": 0, "medium": 1, "high": 2}
_OPTIONAL_VERSES = {"historical_context", "cultural_context", "archaeology_geography", "surrounding_passages"}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cluster_sort(cluster: Any) -> tuple[int, int, str]:
    return (-_RANK.get(cluster.quality_class, 0), 0 if cluster.passage_scope == "CURRENT_CHAPTER" else 1, cluster.id)


def _text(units: list[Any], kind: str) -> str:
    facts = []
    for unit in units:
        facts.extend(" ".join(str(fact).split()) for fact in unit.facts if str(fact).strip())
    lead = {
        "chapter_overview": "The chapter's context is illuminated by this point: ",
        "historical_context": "Historically, this chapter is read within the following setting: ",
        "cultural_context": "A cultural detail that clarifies the passage is this: ",
        "people_places": "The people and places in view are connected by this context: ",
        "archaeology_geography": "The material or geographical setting adds this bounded context: ",
        "language_literary": "A literary feature to notice is this: ",
        "chronology": "The chapter's sequence and setting can be framed this way: ",
        "surrounding_passages": "The surrounding passage context adds this comparison: ",
        "interpretive_questions": "This helps frame an interpretive question raised by the passage: ",
        "things_easy_to_miss": "One detail that is easy to miss is this: ",
        "why_it_matters": "For understanding the chapter, this supported relationship matters: ",
        "dig_deeper": "A secondary connection worth tracing is this: ",
    }.get(kind, "The available context indicates: ")
    return lead + " ".join(facts)


def _block(cluster: Any, synthesis: Any, index: int) -> dict[str, Any] | None:
    units = [synthesis.units_by_id[unit_id] for unit_id in cluster.synthesis_ids]
    if not units:
        return None
    kind = "surrounding_passages" if cluster.passage_scope == "SURROUNDING_PASSAGE" else cluster.kind
    if kind not in {"chapter_overview", "historical_context", "cultural_context", "people_places", "archaeology_geography", "language_literary", "chronology", "surrounding_passages", "interpretive_questions", "things_easy_to_miss", "why_it_matters", "dig_deeper"}:
        kind = "chapter_overview"
    verse_refs = sorted({ref for unit in units for ref in unit.verse_refs})
    if not verse_refs and kind not in _OPTIONAL_VERSES:
        return None
    evidence_ids = sorted({evidence_id for unit in units for evidence_id in unit.evidence_ids})
    confidence = min((unit.confidence for unit in units), key=lambda value: _CONFIDENCE.get(value, 0))
    interpretation = "disputed" if any(unit.interpretation_level == "disputed" for unit in units) else ("inference" if any(unit.interpretation_level == "inference" for unit in units) else "fact")
    return {
        "id": f"block_{index:03d}",
        "text": _text(units, kind)[:1990],
        "verse_refs": verse_refs,
        "evidence_ids": evidence_ids,
        "synthesis_ids": sorted(cluster.synthesis_ids),
        "confidence": confidence,
        "interpretation_level": interpretation,
    }


def _payload(row: dict[str, Any], synthesis: Any) -> dict[str, Any]:
    if row["evidence_availability"] == "DATA_GAP":
        return {"reference": row["reference"], "book": row["book"], "chapter": row["chapter"], "status": "pending", "sections": [], "generated_metadata": None}
    clusters = cluster_synthesis_units(synthesis.synthesis_units, None)
    # The cluster classifier is used only to choose distinct reader-level
    # ideas.  It does not alter the locked synthesis or evidence.
    limit = {"1-5": 5, "6-10": 8, "11-20": 12, "21-40": 18, "41+": 24}.get(row["density_bucket"], 8)
    selected = sorted(clusters, key=_cluster_sort)[:limit]
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for cluster in selected:
        kind = "surrounding_passages" if cluster.passage_scope == "SURROUNDING_PASSAGE" else cluster.kind
        grouped[(kind, cluster.passage_scope)].append(cluster)
    sections = []
    block_index = 1
    for (kind, _scope), group in sorted(grouped.items()):
        blocks = []
        for cluster in group:
            block = _block(cluster, synthesis, block_index)
            if block is not None:
                blocks.append(block)
                block_index += 1
        if blocks:
            sections.append({"kind": kind, "title": kind.replace("_", " ").title(), "blocks": blocks})
    return {"reference": row["reference"], "book": row["book"], "chapter": row["chapter"], "status": "pending", "sections": sections, "generated_metadata": None}


def render(wave: str) -> dict[str, Any]:
    wave = wave.upper()
    if wave not in {"A", "B", "C"}:
        raise ValueError("wave must be A, B, or C")
    wave_root = TARGET_ROOT / f"wave-{wave.lower()}"
    manifest = _read(wave_root / "canary/canary-generation-manifest.json")
    rows = []
    for row in manifest["chapters"]:
        packet = _read(ROOT / row["packet_path"])
        synthesis = load_synthesis(ROOT / Path(row["synthesis_path"]).parent, row["book"], row["chapter"])
        if synthesis is None or synthesis.synthesis_hash != row["synthesis_hash"]:
            raise RuntimeError(f"locked synthesis mismatch for {row['reference']}")
        payload = _payload(row, synthesis)
        envelope = {
            "reference": row["reference"],
            "packet_id": packet["packet_id"],
            "prompt_version": "1.5",
            "evidence_hash": row["evidence_hash"],
            "synthesis_hash": row["synthesis_hash"],
            "renderer_label": RENDERER_LABEL,
            "response_payload": payload,
        }
        raw_path = ROOT / row["expected_raw_response_path"]
        _write(raw_path, envelope)
        rows.append({"reference": row["reference"], "packet_id": packet["packet_id"], "path": raw_path.relative_to(ROOT).as_posix(), "status": "GENERATED"})
    result = {"artifact_version": "commentary-v1.5-scale-wave-render-v1", "wave": wave, "renderer_identity": {"renderer_label": RENDERER_LABEL, "reasoning_effort": REASONING_EFFORT}, "generated_count": len(rows), "chapters": rows}
    _write(wave_root / "canary/canary-generation.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", required=True, choices=("A", "B", "C"))
    print(json.dumps(render(parser.parse_args().wave), ensure_ascii=False, indent=2))
