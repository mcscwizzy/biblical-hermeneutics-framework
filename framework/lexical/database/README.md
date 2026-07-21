# Lexical database

This directory is the destination for a locally generated `lexicon.sqlite`.
The database is intentionally ignored by Git because it is derived from
externally supplied lexical source files.

Build it from local Open Scriptures XML with:

```bash
python -m framework.lexical.tools.build_lexicon_database \
  --hebrew ~/sources/openscriptures/hebrew.xml \
  --greek ~/sources/openscriptures/greek.xml \
  --output framework/lexical/database/lexicon.sqlite
```

Validate an existing database with:

```bash
python -m framework.lexical.tools.validate_lexicon \
  framework/lexical/database/lexicon.sqlite
```

Do not place raw XML, downloaded dictionaries, or other source exports in
this directory.
