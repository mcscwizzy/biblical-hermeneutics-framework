"""Shared conservative normalization for Open Scriptures dictionary XML."""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from ..models import ImportStats


class LexicalImportError(ValueError):
    """Raised when a source XML file cannot be normalized safely."""


_STRONGS_RE = re.compile(r"(?i)(?:^|[^a-z])([hg])?\s*0*([0-9]{1,5})([a-z]?)$")
_ENTRY_NAMES = {
    "entry", "item", "record", "lexeme", "dictionaryentry", "strong", "strongs"
}
_FIELD_NAMES = {
    "lemma": ("lemma", "headword", "word", "original", "greek", "hebrew", "w"),
    "transliteration": ("transliteration", "translit", "romanization", "xlit"),
    "pronunciation": ("pronunciation", "pronounce", "phonetic"),
    "definition": (
        "definition", "strongsdef", "strongdefinition", "meaning", "gloss",
        "description", "kjvdefinition", "kjvdef", "usage", "text", "content",
    ),
    "short_definition": ("shortdefinition", "shortgloss", "gloss", "meaning"),
    "root": ("root", "rootword", "etymology"),
    "part_of_speech": ("partofspeech", "pos", "category", "class"),
    "morphology": ("morphology", "morph", "parse"),
    "semantic_domain": ("semanticdomain", "domain", "semanticfield"),
    "usage_notes": ("usagenotes", "usagenote", "note", "notes"),
}


def import_xml(
    path: str | Path,
    *,
    language: str,
    source: str,
    license_name: str,
    attribution: str,
    source_url: str = "",
    revision: str = "unspecified",
) -> tuple[list[dict[str, str | None]], ImportStats]:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"lexical source file not found: {source_path}")
    if language not in {"hebrew", "greek"}:
        raise LexicalImportError(f"unsupported Open Scriptures language: {language}")
    if not source.strip() or not license_name.strip() or not attribution.strip():
        raise LexicalImportError("source, license, and attribution are required")

    try:
        root = ET.parse(source_path).getroot()
    except ET.ParseError as exc:
        raise LexicalImportError(f"invalid XML source {source_path}: {exc}") from exc
    except OSError as exc:
        raise LexicalImportError(f"could not read XML source {source_path}: {exc}") from exc

    entries: list[dict[str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    for element in _candidate_elements(root):
        record = _record_from_element(
            element,
            language=language,
            source=source,
            license_name=license_name,
            attribution=attribution,
        )
        if record is None:
            continue
        key = (str(record["strongs_number"] or ""), str(record["lemma"] or ""))
        if key in seen:
            continue
        seen.add(key)
        entries.append(record)

    if not entries:
        raise LexicalImportError(
            f"no lexical entries were recognized in {source_path}; "
            "expected dictionary entry elements with a Strong's identifier"
        )
    # These values are intentionally returned as metadata for the database
    # builder. They are not used at runtime and XML is never parsed there.
    for record in entries:
        record["source_url"] = source_url.strip()
        record["revision"] = revision.strip() or "unspecified"
        record["source_file"] = str(source_path)
        record["created_at"] = datetime.now(timezone.utc).isoformat()
    return entries, ImportStats(language, len(entries), source)


def _candidate_elements(root: ET.Element) -> Iterable[ET.Element]:
    for element in root.iter():
        name = _local_name(element.tag)
        if name in _ENTRY_NAMES or _has_identifier(element.attrib):
            yield element


def _record_from_element(
    element: ET.Element,
    *,
    language: str,
    source: str,
    license_name: str,
    attribution: str,
) -> dict[str, str | None] | None:
    strongs = _strongs_identifier(element, language)
    if not strongs:
        return None
    lemma = _field(element, _FIELD_NAMES["lemma"]) or _child_attribute(
        element,
        ("greek", "hebrew", "w", "word", "lemma"),
        ("unicode", "text", "lemma", "word"),
    )
    definition = _definition_from_element(element)
    if not lemma or not definition:
        return None
    short_definition = _field(element, _FIELD_NAMES["short_definition"])
    if short_definition == definition:
        short_definition = _first_sentence(definition)
    return {
        "language": language,
        "strongs_number": strongs,
        "lemma": lemma,
        "transliteration": _field(element, _FIELD_NAMES["transliteration"])
        or _child_attribute(element, ("greek", "hebrew", "w"), ("translit", "xlit")),
        "pronunciation": _field(element, _FIELD_NAMES["pronunciation"])
        or _child_attribute(element, ("pronunciation", "greek", "hebrew", "w"), ("strongs", "pron")),
        "definition": definition,
        "short_definition": short_definition or _first_sentence(definition),
        "root": _field(element, _FIELD_NAMES["root"]),
        "part_of_speech": _field(element, _FIELD_NAMES["part_of_speech"])
        or _child_attribute(element, ("greek", "hebrew", "w"), ("pos",)),
        "morphology": _field(element, _FIELD_NAMES["morphology"]),
        "semantic_domain": _field(element, _FIELD_NAMES["semantic_domain"]),
        "usage_notes": _field(element, _FIELD_NAMES["usage_notes"]),
        "source": source,
        "license": license_name,
        "attribution": attribution,
    }


def _strongs_identifier(element: ET.Element, language: str) -> str | None:
    values: list[str] = []
    for key, value in element.attrib.items():
        if _local_name(key) in {"id", "strong", "strongs", "number", "n", "key"}:
            values.append(value)
    for name in ("id", "strongs", "strong", "number", "key"):
        for child in element:
            if _local_name(child.tag) == name and (child.text or "").strip():
                values.append(child.text or "")
    for value in values:
        match = _STRONGS_RE.fullmatch(str(value).strip())
        if not match:
            continue
        prefix, digits, suffix = match.groups()
        prefix = (prefix or ("H" if language == "hebrew" else "G")).upper()
        return f"{prefix}{int(digits)}{suffix.upper()}"
    return None


def _has_identifier(attributes: Mapping[str, str]) -> bool:
    return any(_local_name(key) in {"id", "strong", "strongs", "number", "n", "key"} for key in attributes)


def _field(element: ET.Element, names: tuple[str, ...]) -> str | None:
    wanted = set(names)
    for key, value in element.attrib.items():
        if _local_name(key) in wanted and str(value).strip():
            return _clean_text(value)
    for candidate in element.iter():
        if candidate is element:
            continue
        if _local_name(candidate.tag) not in wanted:
            continue
        value = " ".join("".join(candidate.itertext()).split())
        if value:
            return _clean_text(value)
    return None


def _definition_from_element(element: ET.Element) -> str | None:
    definition = _field(element, _FIELD_NAMES["definition"])
    if definition:
        return definition
    parts = _named_child_texts(
        element,
        (
            "strongsderivation",
            "source",
            "usage",
            "kjvdef",
            "kjvdefinition",
            "meaning",
            "definition",
        ),
    )
    return _clean_text("; ".join(parts)) if parts else None


def _named_child_texts(element: ET.Element, names: tuple[str, ...]) -> list[str]:
    wanted = set(names)
    values: list[str] = []
    seen: set[str] = set()
    for candidate in element.iter():
        if candidate is element or _local_name(candidate.tag) not in wanted:
            continue
        text = _clean_text(" ".join("".join(candidate.itertext()).split()))
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        values.append(text)
    return values


def _child_attribute(
    element: ET.Element,
    child_names: tuple[str, ...],
    attribute_names: tuple[str, ...],
) -> str | None:
    wanted_children = set(child_names)
    wanted_attributes = set(attribute_names)
    for candidate in element.iter():
        if candidate is element:
            continue
        if _local_name(candidate.tag) not in wanted_children:
            continue
        for key, value in candidate.attrib.items():
            if _local_name(key) in wanted_attributes and str(value).strip():
                return _clean_text(value)
    return None


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].split(":")[-1].replace("_", "").replace("-", "").lower()


def _clean_text(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(str(value).split())).strip()


def _first_sentence(value: str) -> str:
    match = re.split(r"(?<=[.!?])\s+", value.strip(), maxsplit=1)
    return match[0][:280].strip()
