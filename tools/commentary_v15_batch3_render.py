#!/usr/bin/env python3
"""Record the bounded conversational-renderer output for Commentary 1.5 Batch 3.

The prose below is generated against each chapter's locked Prompt 1.5 packet.
This script only writes raw renderer envelopes; import, validation, and Gate
evaluation remain separate transactions.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-batch-3"
PACKET_ROOT = TARGET_ROOT / "canary/prompts"
SYNTHESIS_ROOT = TARGET_ROOT / "canary/synthesis"
RAW_ROOT = TARGET_ROOT / "canary/responses/raw"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _rank_confidence(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(value, 0)


def _block(synthesis: dict[str, Any], block_id: str, text: str, section_kind: str, synthesis_ids: list[str]) -> dict[str, Any]:
    units = {unit["id"]: unit for unit in synthesis["synthesis_units"]}
    selected = [units[item] for item in synthesis_ids]
    scopes = {unit["passage_scope"] for unit in selected}
    if len(scopes) != 1:
        raise RuntimeError(f"mixed passage scopes in {block_id}: {scopes}")
    evidence_ids = sorted({item for unit in selected for item in unit["evidence_ids"]})
    verse_refs = sorted({item for unit in selected for item in unit["verse_refs"]})
    confidence = min((unit["confidence"] for unit in selected), key=_rank_confidence)
    interpretation = "disputed" if any(unit["interpretation_level"] == "disputed" for unit in selected) else (
        "inference" if any(unit["interpretation_level"] == "inference" for unit in selected) else "fact"
    )
    return {
        "id": block_id,
        "text": text,
        "verse_refs": verse_refs,
        "evidence_ids": evidence_ids,
        "synthesis_ids": synthesis_ids,
        "confidence": confidence,
        "interpretation_level": interpretation,
    }


def _payload(reference: str, book: str, chapter: int, synthesis: dict[str, Any]) -> dict[str, Any]:
    availability = synthesis["evidence_availability"]
    if availability == "DATA_GAP":
        return {"reference": reference, "book": book, "chapter": chapter, "status": "pending", "sections": [], "generated_metadata": None}
    if reference == "Judges 12":
        sections = [{"kind": "surrounding_passages", "title": "A restrained reading", "blocks": [
            _block(synthesis, "block_1", "The available context for Judges 12 is thin and concerns the chapter's place within the surrounding Judges narrative. It does not support a fuller reconstruction of the conflict, the place names, or the speech distinction at the Jordan for this commentary.", "surrounding_passages", ["syn_surrounding_passages_4c1af90ce2ad"]),
        ]}]
    elif reference == "Ecclesiastes 4":
        sections = [{"kind": "interpretive_questions", "title": "A cautious reading", "blocks": [
            _block(synthesis, "block_1", "The available context is too limited to add substantial historical or cultural detail to Ecclesiastes 4. Its interpretive question is disputed, so broader claims about the chapter should remain tentative rather than being supplied from outside the chapter's context.", "interpretive_questions", ["syn_interpretive_questions_13c33deb4e9b"]),
        ]}]
    elif reference == "Nehemiah 2":
        sections = [
            {"kind": "chapter_overview", "title": "Rebuilding within an empire", "blocks": [_block(synthesis, "block_1", "Nehemiah 2 presents Jerusalem's rebuilding within Persian imperial administration. Artaxerxes is a real imperial authority whose authorization gives Nehemiah access to letters and timber, while the chapter does not portray Persian kings as covenant rulers or as restoring Davidic sovereignty.", "chapter_overview", ["syn_cultural_context_898abe398102", "syn_why_it_matters_138737c44be5"])]},
            {"kind": "historical_context", "title": "Yehud under Persian rule", "blocks": [_block(synthesis, "block_2", "Cyrus II's capture of Babylon in 539 BCE brought Judah into the wider Persian system as the small province of Yehud. The biblical narratives span several Persian kings, so their reigns should not be collapsed into one undifferentiated period.", "historical_context", ["syn_historical_context_d243ebf32cbc"])]},
            {"kind": "interpretive_questions", "title": "Dates, walls, and opposition", "blocks": [_block(synthesis, "block_3", "Artaxerxes I is the conventional identification for Nehemiah's king, placing the twentieth year around 445/444 BCE, but accession-year and calendar questions leave the exact reckoning qualified. Archaeology confirms Persian-period occupation and administration without establishing an uncontested route or complete circuit for the wall. Sanballat, Tobiah, and Geshem should be read as regional interests in the narrative, not as a timeless ethnic feud.", "interpretive_questions", ["syn_interpretive_questions_0fc1a3693c2d", "syn_interpretive_questions_12e92b41d6eb", "syn_why_it_matters_1eafea6a4a50"])]},
            {"kind": "why_it_matters", "title": "A later comparative witness", "blocks": [_block(synthesis, "block_4", "A 407 BCE petition from Judeans at Elephantine to Bagohi, governor of Judah, offers later comparative evidence for Persian provincial administration, priestly authority, and written appeals. It helps illuminate the administrative world around Ezra-Nehemiah, but it is not direct evidence for every detail of Nehemiah 2.", "why_it_matters", ["syn_interpretive_questions_b9d74d0a9b7d", "syn_why_it_matters_242ec049c26d"])]},
            {"kind": "surrounding_passages", "title": "From prayer to authorization", "blocks": [_block(synthesis, "block_5", "The surrounding narrative connects Nehemiah's response to Jerusalem's distress with mourning, fasting, confession, planning, and the request that Artaxerxes authorizes. The rebuilding project therefore follows a movement from remembered covenant crisis to practical imperial permission.", "surrounding_passages", ["syn_surrounding_passages_9c701b16fd57"])]},
        ]
    elif reference == "Zechariah 5":
        sections = [{"kind": "interpretive_questions", "title": "Wrongdoing exposed and removed", "blocks": [_block(synthesis, "block_1", "Zechariah 5 presents two visions of judgment. The flying scroll carries a land-wide curse into the houses of thieves and false swearers, while the ephah confines Wickedness under a lead weight and carries her to a prepared house in Shinar. The images communicate the reach and removal of wrongdoing, but their symbolic details should not be forced into one exhaustive decoding.", "interpretive_questions", ["syn_interpretive_questions_0577cf01def6", "syn_why_it_matters_e22376f306e8"])] }]
    elif reference == "Acts 6":
        sections = [
            {"kind": "chapter_overview", "title": "Synagogue, instruction, and witness", "blocks": [_block(synthesis, "block_1", "Acts 6 places Stephen's dispute within a Jerusalem setting where synagogue life could center on Torah reading, instruction, and hospitality for visitors. A Greek dedicatory inscription associated with a priest and synagogue leader provides bounded comparative context for that setting; it does not establish every detail of the scene.", "chapter_overview", ["syn_interpretive_questions_29de182def1d", "syn_why_it_matters_168873a16add"])]},
            {"kind": "surrounding_passages", "title": "Text and historical judgment", "blocks": [_block(synthesis, "block_2", "The wider textual history of Acts includes early papyri and major Greek codices with different textual profiles. Historical evaluation therefore compares particular claims with particular witnesses rather than assigning blanket reliability or unreliability to the whole book.", "surrounding_passages", ["syn_surrounding_passages_bd6053707d47", "syn_surrounding_passages_f23d3d8d8175"])]},
        ]
    elif reference == "James 3":
        sections = [
            {"kind": "chapter_overview", "title": "Speech, teaching, and wisdom", "blocks": [_block(synthesis, "block_1", "James 3 joins a warning about teachers and speech with a contrast between earthly wisdom and wisdom from above. The chapter's images make speech's disproportionate power visible, while its description of wisdom tests claims to wisdom by conduct rather than by confident assertion.", "chapter_overview", ["syn_interpretive_questions_9dbf0d2d4b35", "syn_language_literary_304ab71f7146"])]},
            {"kind": "cultural_context", "title": "Human dignity beyond royal privilege", "blocks": [_block(synthesis, "block_2", "Ancient royal imagery could describe kings as images of gods, but the biblical image-of-God tradition extends representative dignity to humanity as a whole. James's concern that people bless God and curse people therefore treats speech about others as speech about those who bear that dignity.", "cultural_context", ["syn_cultural_context_136499f1ed27", "syn_cultural_context_e13dc394cad1"])]},
            {"kind": "historical_context", "title": "Wisdom as faithful living", "blocks": [_block(synthesis, "block_3", "Israelite wisdom grew from family instruction, court life, and worship. It shares forms with neighboring cultures but anchors wisdom in covenant loyalty and the fear of the LORD; James's appeal to conduct belongs within that tradition of teaching faithful living.", "historical_context", ["syn_cultural_context_2b7cd04c4a1e", "syn_historical_context_c647ba34a844"])]},
            {"kind": "cultural_context", "title": "The character of wisdom from above", "blocks": [_block(synthesis, "block_4", "Wisdom from above is recognized as peaceable, gentle, open to reason, merciful, impartial, and sincere. In James's argument, these qualities are not decorative ideals: they are the conduct by which a claim to wisdom is examined.", "cultural_context", ["syn_cultural_context_4ade4d38f48e"])]},
            {"kind": "interpretive_questions", "title": "Power carried by speech", "blocks": [_block(synthesis, "block_5", "Teachers receive stricter judgment because speech carries responsibility, and the tongue's fire imagery names harm that can be disproportionate to the size of the instrument. The warning cannot be used to grant teachers immunity from scrutiny or to turn spiritual authority into protection from accountability.", "interpretive_questions", ["syn_interpretive_questions_c1055a9f7e8b", "syn_why_it_matters_59218acac8b5"])]},
            {"kind": "why_it_matters", "title": "A consistent human regard", "blocks": [_block(synthesis, "block_6", "The image-of-God theme gives the chapter's speech warning a human scope: dignity and moral responsibility are not reserved for rulers or for people with social power. James's demand for consistency reaches both the words spoken about others and the manner in which wisdom is exercised.", "why_it_matters", ["syn_historical_context_0f39e21d5bbb", "syn_historical_context_fad3bc8c3e2f", "syn_why_it_matters_ca823a684aa2"])]},
            {"kind": "surrounding_passages", "title": "A sustained exhortation", "blocks": [_block(synthesis, "block_7", "Across the letter, James combines greeting, moral exhortation, wisdom contrasts, questions, examples, and prophetic warning. The label assigned to its genre highlights features of the writing without exhausting them, and the letter does not identify a certain place of composition.", "surrounding_passages", ["syn_surrounding_passages_6ae729cba7dd", "syn_surrounding_passages_ea824575395c"])]},
        ]
    else:
        raise RuntimeError(f"no renderer payload defined for {reference}")
    return {"reference": reference, "book": book, "chapter": chapter, "status": "pending", "sections": sections, "generated_metadata": None}


def render() -> dict[str, Any]:
    manifest = _read(TARGET_ROOT / "batch-3-manifest.json")
    rows = []
    for row in manifest["chapters"]:
        packet = _read(ROOT / row["packet_path"])
        synthesis = _read(ROOT / row["synthesis_path"])
        payload = _payload(row["reference"], row["book"], row["chapter"], synthesis)
        envelope = {
            "reference": row["reference"],
            "packet_id": packet["packet_id"],
            "prompt_version": "1.5",
            "evidence_hash": row["evidence_hash"],
            "synthesis_hash": row["synthesis_hash"],
            "renderer_label": "GPT-5 Codex",
            "response_payload": payload,
        }
        path = RAW_ROOT / Path(row["expected_response_path"]).name
        _write(path, envelope)
        rows.append({"reference": row["reference"], "packet_id": row["packet_id"], "path": path.relative_to(ROOT).as_posix(), "status": "GENERATED"})
    result = {"artifact_version": "commentary-v1.5-batch-3-render-v1", "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"}, "generated_count": len(rows), "chapters": rows}
    _write(TARGET_ROOT / "canary/canary-generation.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(render(), ensure_ascii=False, indent=2))
