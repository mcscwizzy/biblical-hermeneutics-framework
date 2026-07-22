# Lexicon Architecture

The standalone Biblical Lexical Engine now lives under
`framework/lexical/`. Its generated SQLite store is independent of CKL and
contains normalized lexical records plus source attribution. CKL remains the
home for curated hermeneutical/contextual objects and may still contain its
existing word-study tables for passage-token resolution.

BHF lexical support is designed as a deterministic, offline layer beside the
Canonical Knowledge Library (CKL). It does not replace curated CKL objects, and
it does not ask a model to reconstruct Greek or Hebrew data from memory.

## Layers

1. Raw external source data lives outside runtime lookup, normally under
   `data_sources/lexicons/`. These checkouts are ignored by git unless a future
   source is explicitly vendored with license approval.
2. Normalized standalone lexical data is imported into
   `framework/lexical/database/lexicon.sqlite` (or a configured deployment
   path). CKL data is built separately.
3. Runtime code queries compact repository and word-study objects. These can be
   rendered directly, cached deterministically, or passed to a model as compact
   explanation context.

Normal application startup never downloads source data and never parses raw
XML, OSIS, TSV, or JSON lexicon source files.

Docker image builds are the exception to the download/import rule: the
`Dockerfile` clones pinned source revisions, builds a seeded lexical database
at `/app/.bhf-seed/lexicon.sqlite`, validates it, and removes the raw source
checkouts before the final image layer completes. Container startup only copies
that seed into the mounted runtime path when `.bhf/lexicon.sqlite` is missing.

## SQLite Tables

The generated CKL SQLite schema includes these lexical tables:

- `lexicon_sources`
- `lexicon_entries`
- `lexicon_senses`
- `word_forms`
- `verse_words`
- `lexicon_relations`

Indexes prioritize exact lookup by Strong's identifier, normalized lemma,
normalized form, language plus lemma, verse reference, verse word position,
entry ID, and source word ID.

The CKL database schema version is bumped when table layout changes. Existing
generated databases fail safely with the normal rebuild message rather than
being silently migrated.

## Runtime Flow

`LexiconRepository` is the query boundary for runtime code. It supports:

- `lookup_by_strongs`
- `lookup_by_lemma`
- `lookup_word_form`
- `get_verse_words`
- `get_word_at_position`
- `find_occurrences`

Exact lexical lookup should be attempted before semantic CKL retrieval for
word-study requests. Curated CKL `word_study` objects remain useful as
interpretive supplements; imported dictionary records remain separate lexical
source data.

## Normalization

Original forms are preserved. Separate normalized search fields support:

- Hebrew pointed and consonantal lookup
- Greek accented and unaccented lookup
- Greek final sigma normalization
- Unicode composed/decomposed forms
- Strong's numbers with or without leading zeros
- Transliteration lookup where available

Normalization is conservative and should not be used to infer that two distinct
lemmas are the same word.

## Implementation Status

Implemented:

- SQLite lexical schema and indexes
- Repository query boundary
- Source provenance table
- Conservative lexical normalization
- Initial Hebrew and Greek morphology decoders
- Explicit local normalized JSON importer
- Local source-manifest importer for inspected JSON/TSV lexicon and verse-word
  exports
- Fixture-backed tests
- Passage word-study service integration
- Compact prompt-path injection for deterministic Word Study results

The standalone engine also provides native Open Scriptures XML importers,
SQLite-only runtime lookup, provenance validation, and bounded lexical prompt
context. The raw source files remain the developer's responsibility.

Not yet implemented:

- Dedicated parsers for every non-dictionary upstream file layout in Open
  Scriptures Strong's, HebrewLexicon, morphhb, MorphGNT, or Abbott-Smith
- Browser-side original-language token picker for ambiguity resolution
- Licensing decision and pinned revisions for production bundled datasets
