"""Standalone published commentary resources for the BHF reader."""

from .database_schema import DEFAULT_COMMENTARY_DATABASE_PATH, SCHEMA_VERSION, initialize_database
from .models import CommentaryEntry, CommentarySource, ScriptureAnchor
from .service import CommentaryService

__all__ = [
    "CommentaryEntry",
    "CommentaryService",
    "CommentarySource",
    "DEFAULT_COMMENTARY_DATABASE_PATH",
    "SCHEMA_VERSION",
    "ScriptureAnchor",
    "initialize_database",
]
