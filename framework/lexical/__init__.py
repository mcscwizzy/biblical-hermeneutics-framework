"""Standalone, SQLite-backed Biblical Lexical Engine."""

from .models import LexicalEntry
from .repository import LexicalRepository
from .service import LexicalLookupService, lookup_word

__all__ = [
    "LexicalEntry",
    "LexicalLookupService",
    "LexicalRepository",
    "lookup_word",
]
