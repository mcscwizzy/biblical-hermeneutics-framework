"""Build the locked production packet from the existing commentary authorities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.prompts import CHAPTER_COMMENTARY_SYSTEM_PROMPT, build_user_prompt
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, validate_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.chapter_commentary.richness_clusters import RICHNESS_GATE_V2_VERSION
from bhf_agent.chapter_commentary.validation import __file__ as validator_file

from .models import InputIdentity, PreparedChapter, ProductionError, canonical_json, sha256_bytes, sha256_json


def validator_identity() -> str:
    digest = hashlib.sha256(Path(validator_file).read_bytes()).hexdigest()
    return f"bhf_agent.chapter_commentary.validation:validate_chapter_commentary:sha256:{digest}"


def literary_category(book: str, chapter: int) -> str:
    administrative = {
        "Numbers": {1, 2, 3, 7, 26, 31, 33, 36},
        "1 Chronicles": {1, 8, 9, 23, 24, 25, 26, 27, 28, 29},
        "2 Chronicles": {2, 8, 9, 29, 30, 31},
        "Ezra": {2, 3, 7, 8, 10},
        "Nehemiah": {3, 7, 10, 11, 12, 13},
    }
    if chapter in administrative.get(book, set()):
        return "Genealogy/list/administrative"
    if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}:
        return "Pentateuch"
    if book in {"Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther"}:
        return "Historical narrative"
    if book in {"Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs"}:
        return "Poetry/Wisdom"
    if book in {"Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"}:
        return "Prophets"
    if book in {"Matthew", "Mark", "Luke", "John", "Acts"}:
        return "Gospels/Acts"
    if book == "Revelation":
        return "Apocalyptic / highly symbolic"
    return "Epistles"


def density_bucket(unit_count: int) -> str:
    if unit_count == 0:
        return "0"
    if unit_count <= 5:
        return "1-5"
    if unit_count <= 10:
        return "6-10"
    if unit_count <= 20:
        return "11-20"
    if unit_count <= 40:
        return "21-40"
    return "41+"


def prepare_chapter(book: str, chapter: int, *, run_id: str = "planned", batch_id: str = "batch-001") -> PreparedChapter:
    reference = bible.verse_range_reference(book, chapter)
    bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    if bundle is None:
        raise ProductionError(f"evidence bundle unavailable for {reference}")
    synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
    errors = validate_synthesis(synthesis, bundle)
    if errors:
        raise ProductionError(f"compiled synthesis failed validation for {reference}: {'; '.join(errors)}")
    chapter_data = bible.resolve_chapter(book, chapter)
    canonical_text = bible.passage_text(chapter_data.get("verses", []))
    user_prompt = build_user_prompt(reference, book, chapter, canonical_text, synthesis, bundle, synthesis.evidence_availability)
    packet_base = {
        "artifact_version": "commentary-production-packet-v1",
        "production_version": "commentary-production-v1",
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "candidate_only": False,
        "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "evidence_bundle_version": bundle.version,
        "evidence_availability": synthesis.evidence_availability,
        "evidence_count": len(bundle.evidence_items),
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "synthesis_schema_version": synthesis.synthesis_schema_version,
        "synthesis_compiler_version": synthesis.synthesis_compiler_version,
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "validator_identity": validator_identity(),
        "synthesis_unit_count": len(synthesis.synthesis_units),
        "density_bucket": density_bucket(len(synthesis.synthesis_units)),
        "literary_category": literary_category(book, chapter),
    }
    # Run and batch are execution provenance, not content inputs.  They are
    # added to the persisted packet after its stable content identity is
    # calculated so replanning the same chapter cannot change its packet ID.
    packet_hash = sha256_json(packet_base)
    packet = {**packet_base, "run_id": run_id, "batch_id": batch_id, "packet_id": f"commentary-production-v1-packet:{packet_hash}", "packet_hash": packet_hash}
    identity = InputIdentity(
        evidence_hash=bundle.evidence_hash,
        synthesis_hash=synthesis.synthesis_hash,
        prompt_version=COMMENTARY_PROMPT_VERSION,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        synthesis_schema_version=synthesis.synthesis_schema_version,
        synthesis_compiler_version=synthesis.synthesis_compiler_version,
        gate_version=RICHNESS_GATE_V2_VERSION,
        validator_identity=validator_identity(),
        packet_hash=packet_hash,
        packet_id=packet["packet_id"],
    )
    row = {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "canonical_ordinal": None,
        "literary_category": packet["literary_category"],
        "evidence_availability": synthesis.evidence_availability,
        "evidence_count": len(bundle.evidence_items),
        "synthesis_unit_count": len(synthesis.synthesis_units),
        "density_bucket": packet["density_bucket"],
        "input_identity": identity.to_dict(),
    }
    return PreparedChapter(row=row, bundle=bundle, synthesis=synthesis, packet=packet)


def attach_ordinal(prepared: PreparedChapter, canonical_ordinal: int) -> PreparedChapter:
    row = dict(prepared.row)
    row["canonical_ordinal"] = canonical_ordinal
    return PreparedChapter(row=row, bundle=prepared.bundle, synthesis=prepared.synthesis, packet=prepared.packet)
