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
Open Scriptures Hebrew Bible OSIS files from `openscriptures/morphhb`. For New
Testament Greek coverage, use MorphGNT SBLGNT:

```bash
git clone https://github.com/openscriptures/morphhb sources/openscriptures/morphhb
git -C sources/openscriptures/morphhb rev-parse HEAD
git clone https://github.com/morphgnt/sblgnt sources/openscriptures/morphgnt-sblgnt
git -C sources/openscriptures/morphgnt-sblgnt rev-parse HEAD
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

Or import the whole Hebrew Bible OSIS directory:

```bash
python3 -m framework.lexical.tools.import_verse_tokens \
  --database framework/lexical/database/lexicon.sqlite \
  --oshb-osis-dir sources/openscriptures/morphhb/wlc \
  --source-name OSHB \
  --source-url https://github.com/openscriptures/morphhb \
  --revision <pinned-commit-sha> \
  --license "CC BY 4.0" \
  --attribution "Open Scriptures Hebrew Bible Project" \
  --rebuild-tokens
```

Use `--rebuild-tokens` when replacing previously imported token rows. The tool
also accepts TSV files through `--verse-words-tsv` and `--word-forms-tsv`.
Add `--strict` when the imported token dataset should be Word Study-ready; in
strict mode every token Strong's number must resolve to a lexical entry, verse
positions must be valid, and morphology JSON must be well-formed. Lemma-only
tokens that do not resolve are reported separately as source gaps because
MorphGNT and Strong's sometimes use different lemma conventions.
Verse-word TSV exports must include `book`, `chapter`, `verse`,
`word_position`, `surface_form`, and either `language`, `lemma`, or a prefixed
`strongs_number`.

Then import the whole Greek New Testament. Do not pass `--rebuild-tokens` here
unless you intentionally want to clear the Hebrew rows first:

```bash
python3 -m framework.lexical.tools.import_verse_tokens \
  --database framework/lexical/database/lexicon.sqlite \
  --morphgnt-dir sources/openscriptures/morphgnt-sblgnt \
  --source-name "MorphGNT SBLGNT" \
  --source-url https://github.com/morphgnt/sblgnt \
  --revision <pinned-commit-sha> \
  --license "Morphology CC BY-SA 3.0; SBLGNT text subject to SBLGNT EULA" \
  --attribution "Tauber, J. K., ed. (2017) MorphGNT: SBLGNT Edition"
```

For Docker, the image build performs the source checkout, dictionary build,
Hebrew token import, Greek token import, validation, and smoke test
automatically:

```bash
docker compose up -d --build bhf-web
```

The generated seed database is stored inside the image at
`/app/.bhf-seed/lexicon.sqlite`. On container startup it is copied to the
mounted runtime path `/app/.bhf-data/lexicon.sqlite`, which appears on the host
as `.bhf/lexicon.sqlite`. Compose defaults `BHF_LEXICAL_SEED_POLICY` to
`refresh`, so the runtime database is replaced from the image seed on startup.
Set `BHF_LEXICAL_SEED_POLICY=missing` to keep an existing host database.

## Verify

Validate SQLite integrity and required tables:

```bash
python3 -m framework.lexical.tools.validate_lexicon \
  framework/lexical/database/lexicon.sqlite
```

For a Word Study-ready token dataset, run strict validation:

```bash
python3 -m framework.lexical.tools.validate_lexicon \
  --strict \
  framework/lexical/database/lexicon.sqlite
```

Run the runtime smoke test:

```bash
python3 -m framework.lexical.tools.smoke_lexicon \
  --database framework/lexical/database/lexicon.sqlite
```

Expected smoke output for a full dictionary-plus-token database includes:

```text
Entries: 13938
Sources: 4
Passed: 2/2
```

Strict validation may still report lemma-only source gaps for Greek tokens that
do not carry Strong's numbers. Those gaps should not block Word Study smoke
coverage as long as required Strong's-backed checks pass.

## Troubleshooting

If Word Study says the lexical database is missing, rebuild the database at the
exact runtime path:

```text
framework/lexical/database/lexicon.sqlite
```

For Docker, the runtime path is mounted from the host as:

```text
.bhf/lexicon.sqlite
```

If that file predates the Docker build automation, remove it and run
`docker compose up -d --build` so the image seed is copied into the mount.

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
