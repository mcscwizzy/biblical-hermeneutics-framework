"""Conservative deterministic fingerprints for CKL claim deduplication."""

from __future__ import annotations

import re

from .normalization import normalize_text


_DEMONYM_TERRITORIES = {
    "judean": "judah",
}
_PLACE_KIND_WORDS = frozenset({"city", "settlement", "town", "village"})


def semantic_claim_fingerprint(text: object, kind: object = "") -> str:
    """Return a conservative claim fingerprint.

    Exact normalized prose is the fallback.  Only narrow, well-understood
    territory constructions are canonicalized across paraphrases; this avoids
    collapsing complementary physical or historical geography.
    """

    normalized = normalize_text(str(text or ""))
    normalized_kind = normalize_text(str(kind or ""))
    if not normalized:
        return ""
    territory = _territory_relation(normalized)
    if territory:
        subject, target = territory
        return f"{normalized_kind}|territory-of|{subject}|{target}"
    return f"{normalized_kind}|exact|{normalized}"


def _territory_relation(normalized: str) -> tuple[str, str] | None:
    for demonym, territory in _DEMONYM_TERRITORIES.items():
        match = re.fullmatch(
            rf"(.+?)\s+(?:was|is|were|are)\s+(?:a\s+|an\s+)?"
            rf"{re.escape(demonym)}\s+(?:{'|'.join(sorted(_PLACE_KIND_WORDS))})",
            normalized,
        )
        if match:
            subject = _relation_subject(match.group(1))
            if subject:
                return subject, territory

    patterns = (
        r"^(.+?)\s+(?:was|is|were|are)\s+(?:located|situated) in (?:the )?([a-z][a-z -]*)$",
        r"^(.+?)\s+(?:belonged|belongs) to (?:the )?([a-z][a-z -]*)$",
        r"^(.+?)\s+(?:was|is|were|are)\s+part of (?:the )?([a-z][a-z -]*)$",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        subject = _relation_subject(match.group(1))
        target_tokens = [
            token
            for token in match.group(2).split()
            if token not in _PLACE_KIND_WORDS and token not in {"a", "an", "the"}
        ]
        if subject and target_tokens:
            return subject, " ".join(target_tokens)
    return None


def _relation_subject(value: str) -> str:
    tokens = value.split()
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    return " ".join(tokens)


__all__ = ["semantic_claim_fingerprint"]
