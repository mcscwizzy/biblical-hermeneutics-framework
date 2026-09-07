"""Deterministic chapter-level understanding packets for Commentary v1.2."""

from .compiler import compile_chapter_synthesis
from .hashing import calculate_synthesis_hash
from .models import (
    SYNTHESIS_COMPILER_VERSION,
    SYNTHESIS_SCHEMA_VERSION,
    CompiledChapterSynthesis,
    SynthesisCoverage,
    SynthesisGap,
    SynthesisUnit,
)
from .storage import load_synthesis, save_synthesis
from .validation import SynthesisValidationError, validate_synthesis

__all__ = [
    "SYNTHESIS_COMPILER_VERSION",
    "SYNTHESIS_SCHEMA_VERSION",
    "CompiledChapterSynthesis",
    "SynthesisCoverage",
    "SynthesisGap",
    "SynthesisUnit",
    "SynthesisValidationError",
    "calculate_synthesis_hash",
    "compile_chapter_synthesis",
    "load_synthesis",
    "save_synthesis",
    "validate_synthesis",
]
