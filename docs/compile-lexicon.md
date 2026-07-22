# Compile the Lexicon

BHF does not commit the generated lexical runtime database. Developers build it
locally from inspected Open Scriptures source files.

Runtime expects:

```text
framework/lexical/database/lexicon.sqlite
```

## Flow

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

## Download Sources

Keep raw source checkouts outside committed paths. The repository already
ignores `sources/openscriptures/`.

```bash
mkdir -p sources/openscriptures
git clone https://github.com/openscriptures/HebrewLexicon sources/openscriptures/HebrewLexicon
git clone https://github.com/openscriptures/strongs sources/openscriptures/strongs
```

Inspect upstream licenses and pin revisions before treating a build as
reproducible.

## Build

Use these Open Scriptures XML files:

```text
Hebrew: sources/openscriptures/HebrewLexicon/HebrewStrong.xml
Greek:  sources/openscriptures/strongs/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml
```

Compile the runtime database:

```bash
python3 -m framework.lexical.tools.build_lexicon_database \
  --hebrew sources/openscriptures/HebrewLexicon/HebrewStrong.xml \
  --greek sources/openscriptures/strongs/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml \
  --output framework/lexical/database/lexicon.sqlite
```

Expected successful output is similar to:

```text
Lexical import complete.
Hebrew: 8435 entries imported
Greek: 5503 entries imported
Database: framework/lexical/database/lexicon.sqlite
```

## Import Verse Tokens

Word Study can resolve a whole verse only after original-language verse tokens
are imported into the same runtime database. For Hebrew Bible coverage, use the
Open Scriptures Hebrew Bible OSIS files from `openscriptures/morphhb`:

```bash
git clone https://github.com/openscriptures/morphhb sources/openscriptures/morphhb
git -C sources/openscriptures/morphhb rev-parse HEAD
```

Import one or more OSIS book files, recording the pinned revision:

```bash
python3 -m framework.lexical.tools.import_verse_tokens \
  --database framework/lexical/database/lexicon.sqlite \
  --oshb-osis sources/openscriptures/morphhb/wlc/Gen.xml \
  --source-name OSHB \
  --source-url https://github.com/openscriptures/morphhb \
  --revision <pinned-commit-sha> \
  --license "CC BY 4.0" \
  --attribution "Open Scriptures Hebrew Bible Project"
```

Use `--rebuild-tokens` when replacing previously imported token rows. The tool
also accepts TSV files through `--verse-words-tsv` and `--word-forms-tsv`.
Verse-word TSV exports must include `book`, `chapter`, `verse`,
`word_position`, `surface_form`, and either `language`, `lemma`, or a prefixed
`strongs_number`.

## Verify

Validate SQLite integrity and required tables:

```bash
python3 -m framework.lexical.tools.validate_lexicon \
  framework/lexical/database/lexicon.sqlite
```

Run the runtime smoke test:

```bash
python3 -m framework.lexical.tools.smoke_lexicon \
  --database framework/lexical/database/lexicon.sqlite
```

Expected smoke output includes:

```text
Entries: 13938
Sources: 2
Passed: 2/2
```

## Troubleshooting

If Word Study says the lexical database is missing, rebuild the database at the
exact runtime path:

```text
framework/lexical/database/lexicon.sqlite
```

If the importer cannot find lexical entries, confirm you are using:

```text
sources/openscriptures/HebrewLexicon/HebrewStrong.xml
sources/openscriptures/strongs/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml
```

Do not replace missing lexical data with LLM guesses. If the database is
missing or incomplete, Word Study should report deterministic lexical data as
unavailable.

If Word Study for a full verse reports multiple possible words, the token layer
is working; select one original-language token to run the specific word study.
