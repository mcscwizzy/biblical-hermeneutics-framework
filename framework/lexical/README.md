# Biblical Lexical Engine

The Biblical Lexical Engine is a standalone, deterministic data layer for
Hebrew and Greek lexical records. It is separate from the Canonical Knowledge
Library (CKL): CKL contains curated hermeneutical and contextual material,
while this subsystem stores externally sourced lexical data and provenance.

## Sources and licensing

Raw source files are not committed. Developers provide local XML exports and
must confirm the source license and attribution before importing them. The
importer preserves source name, license, attribution, revision, source URL, and
import time in SQLite. The generated database is ignored by Git.

The default output is `framework/lexical/database/lexicon.sqlite`; use
`--output` for a deployment-specific location. The command parses XML only at
build time, validates required fields, writes atomically, and prints Hebrew
and Greek import counts.

For the current download, build, and verification flow, see
[`docs/compile-lexicon.md`](../../docs/compile-lexicon.md).

The expected default runtime file is
`framework/lexical/database/lexicon.sqlite`. If it is missing, startup logs a
warning with the same build command. BHF must treat lexical data as unavailable
in that state; it must not replace missing Hebrew or Greek source data with LLM
guesses.

## Runtime API

Runtime code opens SQLite in read-only mode:

```python
from framework.lexical import lookup_word

entry = lookup_word(language="greek", strongs="G3056")
entry = lookup_word(language="hebrew", transliteration="hesed")
```

Lookups support Strong's number, lemma, and transliteration. A result is one
compact record containing the lexical fields and provenance. Missing databases
or missing entries return `None` from `lookup_word`; callers should treat that
as unavailable data rather than ask the model to invent a definition.

Whole-passage Word Study also needs verse-token rows in the same database. Use
`python -m framework.lexical.tools.import_verse_tokens` to import OSHB OSIS
files or normalized TSV exports into `verse_words` and `word_forms`. Without
that token layer, the runtime can answer explicit Strong's/lemma requests but
cannot determine which original-language word a verse-level action should use.

## Agent integration

When BHF detects a word-study request with an explicit Hebrew/Greek target or
Strong's identifier, it retrieves only the matching records before CKL
retrieval. The prompt receives the word, definition, optional morphology and
usage note, and source attribution—not the whole database. Configure the
standalone runtime database with `lexicon.runtime_database_path` or the
`BHF_LEXICAL_DATABASE_PATH` environment variable. The existing
`lexicon.database_path` remains the CKL word-study database for compatibility.

Validate and smoke test a generated database with the commands in
[`docs/compile-lexicon.md`](../../docs/compile-lexicon.md).

## Docker

The production image does not copy raw lexical XML or embed an externally
licensed dictionary. The web container reads a generated database from the
mounted `.bhf/lexicon.sqlite` path. Build it with the opt-in Compose helper:

```bash
BHF_LEXICAL_SOURCE_DIR=/absolute/path/to/openscriptures \
  docker compose --profile lexical run --rm bhf-lexicon-build
docker compose up bhf-web
```

The helper expects `hebrew.xml` and `greek.xml` in the supplied directory,
writes the SQLite database to `.bhf/lexicon.sqlite`, and exits. The web
container receives it at `/app/.bhf-data/lexicon.sqlite` in read-only runtime
mode. If no database is mounted, lexical retrieval remains unavailable without
preventing the rest of BHF from starting.
