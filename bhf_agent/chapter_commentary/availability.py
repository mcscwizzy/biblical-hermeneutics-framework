"""Deterministic classification of contextual evidence coverage."""
from __future__ import annotations
import os
from enum import Enum


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    THIN = "THIN"
    DATA_GAP = "DATA_GAP"


DEFAULT_THIN_EVIDENCE_THRESHOLD = 2


def thin_evidence_threshold() -> int:
    raw = os.getenv("BHF_COMMENTARY_THIN_EVIDENCE_THRESHOLD", str(DEFAULT_THIN_EVIDENCE_THRESHOLD))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_THIN_EVIDENCE_THRESHOLD


def classify_evidence_availability(bundle, *, threshold: int | None = None) -> EvidenceAvailability:
    count = len(getattr(bundle, "evidence_items", ()) or ())
    if count == 0:
        return EvidenceAvailability.DATA_GAP
    return EvidenceAvailability.THIN if count < (threshold or thin_evidence_threshold()) else EvidenceAvailability.AVAILABLE
