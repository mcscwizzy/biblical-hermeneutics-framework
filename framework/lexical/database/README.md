# Lexical database

This directory is the destination for a locally generated `lexicon.sqlite`.
The database is intentionally ignored by Git because it is derived from
externally supplied lexical source files.

Runtime expects the generated database at:

```text
framework/lexical/database/lexicon.sqlite
```

Developer flow:

```text
download sources
        |
        v
run importer
        |
        v
generate lexicon.sqlite
        |
        v
run Word Study
```

Build it from local Open Scriptures XML with:

```bash
mkdir -p sources/openscriptures
git clone https://github.com/openscriptures/HebrewLexicon sources/openscriptures/HebrewLexicon
git clone https://github.com/openscriptures/strongs sources/openscriptures/strongs
find sources/openscriptures -name '*.xml'

python -m framework.lexical.tools.build_lexicon_database \
  --hebrew <path-to-open-scriptures-hebrew-xml> \
  --greek <path-to-open-scriptures-greek-xml> \
  --output framework/lexical/database/lexicon.sqlite
```

Validate an existing database with:

```bash
python -m framework.lexical.tools.validate_lexicon \
  framework/lexical/database/lexicon.sqlite
python -m framework.lexical.tools.smoke_lexicon \
  --database framework/lexical/database/lexicon.sqlite
```

Do not place raw XML, downloaded dictionaries, or other source exports in
this directory. If `lexicon.sqlite` is missing, Word Study must report
unavailable deterministic lexical data rather than substituting LLM guesses.
