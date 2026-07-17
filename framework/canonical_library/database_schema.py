"""SQLite schema for the generated CKL runtime database."""

from __future__ import annotations

CKL_DATABASE_SCHEMA_VERSION = "1"
CKL_RETRIEVAL_INDEX_VERSION = "1"
DEFAULT_CKL_DATABASE_PATH = ".bhf/ckl.sqlite"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE ckl_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE canonical_objects (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    summary TEXT,
    content_status TEXT NOT NULL,
    review_status TEXT NOT NULL,
    confidence TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 0,
    object_version TEXT,
    source_path TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE canonical_aliases (
    normalized_alias TEXT NOT NULL,
    object_id TEXT NOT NULL,
    original_alias TEXT NOT NULL,
    PRIMARY KEY (normalized_alias, object_id),
    FOREIGN KEY (object_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_keywords (
    term TEXT NOT NULL,
    object_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_weight INTEGER NOT NULL,
    PRIMARY KEY (term, object_id, field_name),
    FOREIGN KEY (object_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_relationships (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    PRIMARY KEY (
        source_id,
        target_id,
        relationship
    ),
    FOREIGN KEY (source_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE,
    FOREIGN KEY (target_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_scripture_references (
    object_id TEXT NOT NULL,
    reference_text TEXT NOT NULL,
    book TEXT NOT NULL,
    start_chapter INTEGER,
    start_verse INTEGER,
    end_chapter INTEGER,
    end_verse INTEGER,
    relationship TEXT,
    notes TEXT,
    FOREIGN KEY (object_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_objects_type
ON canonical_objects(type);

CREATE INDEX idx_objects_normalized_title
ON canonical_objects(normalized_title);

CREATE INDEX idx_aliases_normalized_alias
ON canonical_aliases(normalized_alias);

CREATE INDEX idx_keywords_term
ON canonical_keywords(term);

CREATE INDEX idx_keywords_term_type
ON canonical_keywords(term, field_name);

CREATE INDEX idx_relationships_source
ON canonical_relationships(source_id);

CREATE INDEX idx_relationships_target
ON canonical_relationships(target_id);

CREATE INDEX idx_scripture_book
ON canonical_scripture_references(book);

CREATE INDEX idx_scripture_range
ON canonical_scripture_references(
    book,
    start_chapter,
    start_verse,
    end_chapter,
    end_verse
);
"""


REQUIRED_INDEXES = {
    "idx_objects_type",
    "idx_objects_normalized_title",
    "idx_aliases_normalized_alias",
    "idx_keywords_term",
    "idx_keywords_term_type",
    "idx_relationships_source",
    "idx_relationships_target",
    "idx_scripture_book",
    "idx_scripture_range",
}
