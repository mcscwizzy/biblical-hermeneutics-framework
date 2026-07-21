"""Application-facing lexical services for deterministic word study."""

from .models import LexicalEntry, WordOccurrence, WordStudyResult
from .repository import LexiconRepository
from .service import WordStudyService

__all__ = [
    "LexicalEntry",
    "LexiconRepository",
    "WordOccurrence",
    "WordStudyResult",
    "WordStudyService",
]
