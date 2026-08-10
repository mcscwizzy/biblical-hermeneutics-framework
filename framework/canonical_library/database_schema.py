"""SQLite schema for the generated CKL runtime database."""

from __future__ import annotations

CKL_DATABASE_SCHEMA_VERSION = "3"
CKL_RETRIEVAL_INDEX_VERSION = "2"
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

CREATE TABLE canonical_claims (
    object_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    certainty TEXT NOT NULL,
    dispute_status TEXT NOT NULL,
    rationale TEXT,
    notes TEXT,
    PRIMARY KEY (object_id, claim_id),
    FOREIGN KEY (object_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_claim_scripture_references (
    object_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    reference_text TEXT NOT NULL,
    book TEXT,
    start_chapter INTEGER,
    start_verse INTEGER,
    end_chapter INTEGER,
    end_verse INTEGER,
    PRIMARY KEY (object_id, claim_id, reference_text),
    FOREIGN KEY (object_id, claim_id)
        REFERENCES canonical_claims(object_id, claim_id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_sources (
    object_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    year INTEGER,
    locator TEXT,
    url TEXT,
    source_type TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (object_id, source_id),
    FOREIGN KEY (object_id)
        REFERENCES canonical_objects(id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_claim_sources (
    object_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relationship TEXT NOT NULL CHECK (relationship IN ('source_id', 'supports')),
    source_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (object_id, claim_id, source_id, relationship),
    FOREIGN KEY (object_id, claim_id)
        REFERENCES canonical_claims(object_id, claim_id)
        ON DELETE CASCADE,
    FOREIGN KEY (object_id, source_id)
        REFERENCES canonical_sources(object_id, source_id)
        ON DELETE CASCADE
);

CREATE TABLE canonical_source_supports (
    object_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    supported_item TEXT NOT NULL,
    PRIMARY KEY (object_id, source_id, supported_item),
    FOREIGN KEY (object_id, source_id)
        REFERENCES canonical_sources(object_id, source_id)
        ON DELETE CASCADE
);

CREATE VIRTUAL TABLE canonical_fts USING fts5(
    object_id UNINDEXED,
    title,
    aliases,
    summary,
    common_questions,
    keywords,
    claims,
    contexts,
    retrieval_metadata,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE lexicon_sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    repository_url TEXT NOT NULL DEFAULT '',
    revision TEXT NOT NULL,
    license TEXT NOT NULL,
    attribution TEXT NOT NULL,
    redistribution_status TEXT NOT NULL DEFAULT 'unknown',
    imported_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE (name, revision, content_hash)
);

CREATE TABLE lexicon_entries (
    id INTEGER PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'aramaic', 'greek')),
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    transliteration TEXT,
    normalized_transliteration TEXT,
    pronunciation TEXT,
    strongs_number TEXT,
    normalized_strongs_number TEXT,
    strongs_digits TEXT,
    part_of_speech TEXT,
    short_gloss TEXT,
    definition TEXT,
    source_name TEXT NOT NULL,
    source_entry_id TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    license TEXT NOT NULL,
    attribution TEXT NOT NULL,
    UNIQUE (source_name, source_entry_id)
);

CREATE TABLE lexicon_senses (
    id INTEGER PRIMARY KEY,
    lexicon_entry_id INTEGER NOT NULL,
    sense_order INTEGER NOT NULL,
    gloss TEXT NOT NULL,
    definition TEXT,
    semantic_domain TEXT,
    usage_note TEXT,
    source_name TEXT NOT NULL,
    source_sense_id TEXT,
    FOREIGN KEY (lexicon_entry_id)
        REFERENCES lexicon_entries(id)
        ON DELETE CASCADE,
    UNIQUE (lexicon_entry_id, sense_order, source_name)
);

CREATE TABLE word_forms (
    id INTEGER PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'aramaic', 'greek')),
    surface_form TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    transliteration TEXT,
    normalized_transliteration TEXT,
    strongs_number TEXT,
    normalized_strongs_number TEXT,
    strongs_digits TEXT,
    morphology_code TEXT,
    morphology_json TEXT NOT NULL DEFAULT '{}',
    lexicon_entry_id INTEGER,
    source_name TEXT,
    source_word_id TEXT,
    FOREIGN KEY (lexicon_entry_id)
        REFERENCES lexicon_entries(id)
        ON DELETE SET NULL,
    UNIQUE (source_name, source_word_id)
);

CREATE TABLE verse_words (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    word_position INTEGER NOT NULL,
    source_word_id TEXT,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'aramaic', 'greek')),
    surface_form TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    transliteration TEXT,
    normalized_transliteration TEXT,
    strongs_number TEXT,
    normalized_strongs_number TEXT,
    strongs_digits TEXT,
    morphology_code TEXT,
    morphology_json TEXT NOT NULL DEFAULT '{}',
    lexicon_entry_id INTEGER,
    source_name TEXT,
    FOREIGN KEY (lexicon_entry_id)
        REFERENCES lexicon_entries(id)
        ON DELETE SET NULL,
    UNIQUE (book, chapter, verse, word_position, language)
);

CREATE TABLE lexicon_relations (
    source_entry_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (
        relation_type IN (
            'root',
            'derived_from',
            'cognate',
            'synonym',
            'antonym',
            'related_word',
            'hebrew_equivalent',
            'greek_equivalent'
        )
    ),
    target_entry_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    PRIMARY KEY (source_entry_id, relation_type, target_entry_id, source_name)
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

CREATE INDEX idx_claims_object
ON canonical_claims(object_id);

CREATE INDEX idx_claims_type
ON canonical_claims(claim_type);

CREATE INDEX idx_claim_scripture_book
ON canonical_claim_scripture_references(book, start_chapter, start_verse);

CREATE INDEX idx_sources_object
ON canonical_sources(object_id);

CREATE INDEX idx_sources_type
ON canonical_sources(source_type);

CREATE INDEX idx_claim_sources_claim
ON canonical_claim_sources(object_id, claim_id);

CREATE INDEX idx_claim_sources_source
ON canonical_claim_sources(object_id, source_id);

CREATE INDEX idx_source_supports_item
ON canonical_source_supports(supported_item);

CREATE INDEX idx_lexicon_entries_strongs
ON lexicon_entries(normalized_strongs_number);

CREATE INDEX idx_lexicon_entries_strongs_digits
ON lexicon_entries(strongs_digits);

CREATE INDEX idx_lexicon_entries_normalized_lemma
ON lexicon_entries(normalized_lemma);

CREATE INDEX idx_lexicon_entries_language_lemma
ON lexicon_entries(language, normalized_lemma);

CREATE INDEX idx_lexicon_entries_transliteration
ON lexicon_entries(normalized_transliteration);

CREATE INDEX idx_lexicon_senses_entry
ON lexicon_senses(lexicon_entry_id);

CREATE INDEX idx_word_forms_normalized_form
ON word_forms(normalized_form);

CREATE INDEX idx_word_forms_language_lemma
ON word_forms(language, normalized_lemma);

CREATE INDEX idx_word_forms_strongs
ON word_forms(normalized_strongs_number);

CREATE INDEX idx_word_forms_source_word
ON word_forms(source_word_id);

CREATE INDEX idx_word_forms_entry
ON word_forms(lexicon_entry_id);

CREATE INDEX idx_verse_words_reference
ON verse_words(book, chapter, verse);

CREATE INDEX idx_verse_words_reference_position
ON verse_words(book, chapter, verse, word_position);

CREATE INDEX idx_verse_words_strongs
ON verse_words(normalized_strongs_number);

CREATE INDEX idx_verse_words_language_lemma
ON verse_words(language, normalized_lemma);

CREATE INDEX idx_verse_words_source_word
ON verse_words(source_word_id);

CREATE INDEX idx_verse_words_entry
ON verse_words(lexicon_entry_id);

CREATE INDEX idx_lexicon_relations_source
ON lexicon_relations(source_entry_id);

CREATE INDEX idx_lexicon_relations_target
ON lexicon_relations(target_entry_id);
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
    "idx_claims_object",
    "idx_claims_type",
    "idx_claim_scripture_book",
    "idx_sources_object",
    "idx_sources_type",
    "idx_claim_sources_claim",
    "idx_claim_sources_source",
    "idx_source_supports_item",
    "idx_lexicon_entries_strongs",
    "idx_lexicon_entries_strongs_digits",
    "idx_lexicon_entries_normalized_lemma",
    "idx_lexicon_entries_language_lemma",
    "idx_lexicon_entries_transliteration",
    "idx_lexicon_senses_entry",
    "idx_word_forms_normalized_form",
    "idx_word_forms_language_lemma",
    "idx_word_forms_strongs",
    "idx_word_forms_source_word",
    "idx_word_forms_entry",
    "idx_verse_words_reference",
    "idx_verse_words_reference_position",
    "idx_verse_words_strongs",
    "idx_verse_words_language_lemma",
    "idx_verse_words_source_word",
    "idx_verse_words_entry",
    "idx_lexicon_relations_source",
    "idx_lexicon_relations_target",
}
