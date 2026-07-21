"""Deterministic morphology decoders for initial lexical imports."""

from __future__ import annotations

from typing import Any

_HEBREW_POS = {
    "A": "adjective",
    "C": "conjunction",
    "D": "adverb",
    "N": "noun",
    "P": "pronoun",
    "R": "preposition",
    "T": "article",
    "V": "verb",
}
_HEBREW_GENDER = {"m": "masculine", "f": "feminine", "c": "common"}
_HEBREW_NUMBER = {"s": "singular", "p": "plural", "d": "dual"}
_HEBREW_STATE = {"a": "absolute", "c": "construct", "d": "determined"}
_HEBREW_NOUN_TYPE = {"c": "common", "p": "proper", "g": "gentilic"}
_HEBREW_STEM = {
    "q": "qal",
    "N": "niphal",
    "p": "piel",
    "P": "pual",
    "h": "hiphil",
    "H": "hophal",
    "t": "hithpael",
}
_HEBREW_CONJUGATION = {
    "p": "perfect",
    "q": "sequential perfect",
    "i": "imperfect",
    "w": "sequential imperfect",
    "v": "imperative",
    "r": "participle",
    "s": "infinitive construct",
    "a": "infinitive absolute",
}
_PERSON = {"1": "first", "2": "second", "3": "third"}

_GREEK_POS = {
    "A": "adjective",
    "C": "conjunction",
    "D": "adverb",
    "I": "interjection",
    "N": "noun",
    "P": "preposition",
    "R": "pronoun",
    "T": "article",
    "V": "verb",
    "X": "particle",
}
_GREEK_TENSE = {
    "P": "present",
    "I": "imperfect",
    "F": "future",
    "A": "aorist",
    "R": "perfect",
    "L": "pluperfect",
}
_GREEK_VOICE = {"A": "active", "M": "middle", "P": "passive", "E": "middle/passive"}
_GREEK_MOOD = {
    "I": "indicative",
    "D": "imperative",
    "S": "subjunctive",
    "O": "optative",
    "N": "infinitive",
    "P": "participle",
}
_CASE = {"N": "nominative", "G": "genitive", "D": "dative", "A": "accusative", "V": "vocative"}
_GENDER = {"M": "masculine", "F": "feminine", "N": "neuter"}
_NUMBER = {"S": "singular", "P": "plural"}


def decode_hebrew_morphology(code: str | None) -> dict[str, Any]:
    raw = str(code or "").strip()
    if not raw:
        return {}
    core = raw.split("/")[-1].lstrip("H")
    result: dict[str, Any] = {"code": raw}
    pos = core[:1]
    if pos in _HEBREW_POS:
        result["part_of_speech"] = _HEBREW_POS[pos]
    else:
        result["unknown_code"] = raw
        return result

    if pos == "V":
        _set(result, "stem", _HEBREW_STEM.get(_char(core, 1)))
        _set(result, "conjugation", _HEBREW_CONJUGATION.get(_char(core, 2)))
        _set(result, "person", _PERSON.get(_char(core, 3)))
        _set(result, "gender", _HEBREW_GENDER.get(_char(core, 4)))
        _set(result, "number", _HEBREW_NUMBER.get(_char(core, 5)))
    elif pos == "N":
        _set(result, "noun_type", _HEBREW_NOUN_TYPE.get(_char(core, 1)))
        _set(result, "gender", _HEBREW_GENDER.get(_char(core, 2)))
        _set(result, "number", _HEBREW_NUMBER.get(_char(core, 3)))
        _set(result, "state", _HEBREW_STATE.get(_char(core, 4)))
    elif pos in {"A", "T"}:
        _set(result, "gender", _HEBREW_GENDER.get(_char(core, 1)))
        _set(result, "number", _HEBREW_NUMBER.get(_char(core, 2)))
        _set(result, "state", _HEBREW_STATE.get(_char(core, 3)))
    elif pos == "P":
        _set(result, "person", _PERSON.get(_char(core, 1)))
        _set(result, "gender", _HEBREW_GENDER.get(_char(core, 2)))
        _set(result, "number", _HEBREW_NUMBER.get(_char(core, 3)))
    return result


def decode_greek_morphology(code: str | None) -> dict[str, Any]:
    raw = str(code or "").strip()
    if not raw:
        return {}
    result: dict[str, Any] = {"code": raw}
    pos = raw[:1]
    if raw.startswith("RA"):
        result["part_of_speech"] = "article"
    elif pos in _GREEK_POS:
        result["part_of_speech"] = _GREEK_POS[pos]
    else:
        result["unknown_code"] = raw
        return result

    if pos == "V":
        chars = raw.replace("-", "")
        offset = 2 if len(chars) > 1 and chars[1].isdigit() else 1
        if len(chars) > offset + 2:
            _set(result, "tense", _GREEK_TENSE.get(chars[offset]))
            _set(result, "voice", _GREEK_VOICE.get(chars[offset + 1]))
            _set(result, "mood", _GREEK_MOOD.get(chars[offset + 2]))
        if "-" in raw:
            tail = raw.rsplit("-", 1)[-1]
            _set(result, "person", _PERSON.get(_char(tail, 0)))
            _set(result, "number", _NUMBER.get(_char(tail, 1)))
    if pos != "V" or result.get("mood") == "participle":
        tail = raw[-3:]
        _set(result, "case", _CASE.get(_char(tail, 0)))
        _set(result, "number", _NUMBER.get(_char(tail, 1)))
        _set(result, "gender", _GENDER.get(_char(tail, 2)))
    return result


def decode_morphology(language: str, code: str | None) -> dict[str, Any]:
    if language == "greek":
        return decode_greek_morphology(code)
    if language in {"hebrew", "aramaic"}:
        return decode_hebrew_morphology(code)
    return {"code": str(code or ""), "unknown_language": language}


def _char(value: str, index: int) -> str:
    return value[index] if len(value) > index else ""


def _set(target: dict[str, Any], key: str, value: str | None) -> None:
    if value:
        target[key] = value
