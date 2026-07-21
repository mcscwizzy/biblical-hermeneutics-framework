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

Open Scriptures dictionaries can be imported with:

```bash
python -m framework.lexical.tools.build_lexicon_database \
  --hebrew ~/sources/openscriptures/hebrew.xml \
  --greek ~/sources/openscriptures/greek.xml
```

The default output is `framework/lexical/database/lexicon.sqlite`; use
`--output` for a deployment-specific location. The command parses XML only at
build time, validates required fields, writes atomically, and prints Hebrew
and Greek import counts.

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

## Agent integration

When BHF detects a word-study request with an explicit Hebrew/Greek target or
Strong's identifier, it retrieves only the matching records before CKL
retrieval. The prompt receives the word, definition, optional morphology and
usage note, and source attribution—not the whole database. Configure the
standalone runtime database with `lexicon.runtime_database_path` or the
`BHF_LEXICAL_DATABASE_PATH` environment variable. The existing
`lexicon.database_path` remains the CKL word-study database for compatibility.

Validate a generated database with:

```bash
python -m framework.lexical.tools.validate_lexicon \
  framework/lexical/database/lexicon.sqlite
```
