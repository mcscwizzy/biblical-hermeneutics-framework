"""Canonical Knowledge Library public API."""

from __future__ import annotations

from .context_builder import CanonicalContextBuilder
from .loader import CanonicalLibrary
from .normalization import normalize_alias, normalize_id, normalize_text, tokenize_query
from .public_cache import NullPublicAnswerCache, PublicAnswerCache, PublicCacheEntry
from .retrieval import (
    CanonicalRetriever,
    ExactCanonicalRetriever,
    FutureHybridRetriever,
    FutureSemanticRetriever,
    RetrievalResult,
)
from .schema import (
    CATEGORY_FOLDERS,
    SUPPORTED_CATEGORIES,
    CanonicalObject,
    CanonicalValidationError,
    validate_aliases,
    validate_category_type,
    validate_field_types,
    validate_library,
    validate_object,
    validate_required_fields,
)

__all__ = [
    "CanonicalLibrary",
    "CanonicalContextBuilder",
    "CanonicalObject",
    "CanonicalValidationError",
    "RetrievalResult",
    "CanonicalRetriever",
    "ExactCanonicalRetriever",
    "FutureSemanticRetriever",
    "FutureHybridRetriever",
    "PublicCacheEntry",
    "PublicAnswerCache",
    "NullPublicAnswerCache",
    "normalize_text",
    "normalize_id",
    "normalize_alias",
    "tokenize_query",
    "SUPPORTED_CATEGORIES",
    "CATEGORY_FOLDERS",
    "validate_object",
    "validate_library",
    "validate_required_fields",
    "validate_field_types",
    "validate_category_type",
    "validate_aliases",
]

