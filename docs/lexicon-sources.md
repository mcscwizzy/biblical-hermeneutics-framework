# Lexicon Sources

BHF only imports lexical data from reproducible local sources whose licenses
have been inspected. Do not scrape websites, and do not import proprietary
lexicon text such as BDAG, HALOT, or TWOT definitions.

Raw source checkouts should normally live under:

```text
data_sources/lexicons/
```

This directory is ignored by git. Runtime lookup uses SQLite, not raw source
files.

The current standalone lexical runtime expects a generated SQLite file at:

```text
framework/lexical/database/lexicon.sqlite
```

Build that file from local Open Scriptures XML with:

```bash
mkdir -p sources/openscriptures
git clone https://github.com/openscriptures/HebrewLexicon sources/openscriptures/HebrewLexicon
git clone https://github.com/openscriptures/strongs sources/openscriptures/strongs
find sources/openscriptures -name '*.xml'

python -m framework.lexical.tools.build_lexicon_database \
  --hebrew <path-to-open-scriptures-hebrew-xml> \
  --greek <path-to-open-scriptures-greek-xml> \
  --output framework/lexical/database/lexicon.sqlite
python -m framework.lexical.tools.smoke_lexicon \
  --database framework/lexical/database/lexicon.sqlite
```

Developer onboarding flow:

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

## Approved Source Plan

| Dataset | Source Repository | Pinned Revision | Data Used | License | Attribution | Redistribution Status | Import Command |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Open Scriptures Strong's dictionaries | To be pinned in Phase 2/4 | Not yet pinned | Strong's-linked definitions where legally permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | `python -m framework.lexical.tools.build_lexicon_database --greek <xml> --output framework/lexical/database/lexicon.sqlite` |
| Open Scriptures HebrewLexicon | To be pinned in Phase 2 | Not yet pinned | Hebrew lemmas, glosses, BDB-linked data where permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | `python -m framework.lexical.tools.build_lexicon_database --hebrew <xml> --output framework/lexical/database/lexicon.sqlite` |
| Open Scriptures morphhb | To be pinned in Phase 2 | Not yet pinned | Hebrew surface forms, lemmas, Strong's IDs, morphology, verse positions | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| MorphGNT | To be pinned in Phase 4 | Not yet pinned | Greek surface forms, lemmas, morphology, verse positions | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| Abbott-Smith Greek lexicon | To evaluate in Phase 4 | Not yet pinned | Greek definitions only if redistribution is permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |

## Phase 1 Import

The importer accepts explicit normalized JSON payloads. It is used for fixtures
and as the stable target contract for source-specific parsers.

```bash
python -m framework.canonical_library build-db
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --normalized-json tests/fixtures/lexicon_phase1.json \
  --rebuild
```

## Local Source Manifest Import

The importer also accepts inspected local source manifests. A manifest records
source metadata and local file paths. It still imports into `.bhf/ckl.sqlite`
and still does not download anything.

```bash
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --source-manifest data_sources/lexicons/lexicon-sources.json \
  --rebuild
```

Supported manifest source kinds:

- `openscriptures_strongs_json`
- `openscriptures_hebrewlexicon_json`
- `lexicon_json`
- `morphgnt_tsv`
- `morphhb_tsv`
- `verse_words_tsv`
- `word_forms_tsv`

Example:

```json
{
  "sources": [
    {
      "name": "morphgnt-local",
      "kind": "morphgnt_tsv",
      "path": "morphgnt.tsv",
      "repository_url": "https://github.com/morphgnt/sblgnt",
      "revision": "<pinned commit>",
      "license": "<verified license>",
      "attribution": "<required attribution>",
      "redistribution_status": "local-only"
    }
  ]
}
```

TSV verse-word exports must include a header row with:

- `book`
- `chapter`
- `verse`
- `word_position`
- `language` or a prefixed `strongs_number`
- `surface_form`
- `lemma`

Optional columns include `transliteration`, `strongs_number`,
`morphology_code`, `morphology_json`, `source_word_id`, and `source_entry_id`.

The importer:

- Uses a SQLite transaction
- Records source revision, license, attribution, import timestamp, and content
  hash
- Rebuilds only generated lexical tables when `--rebuild` is passed
- Fails clearly on malformed required fields
- Does not download anything
- Records source metadata from each normalized payload or source manifest

## Update Procedure

1. Inspect the upstream license.
2. Pin a release tag or commit SHA.
3. Record repository URL, revision, license, attribution, redistribution status,
   and import command in this file.
4. Create a local source manifest. Start from
   `examples/lexicon-source-manifest.example.json`.
5. Import into a generated SQLite database.
6. Run lexical repository, importer, and onboarding coverage tests.
7. Do not commit raw source data unless redistribution has been confirmed and
   the repository explicitly chooses to vendor it.

## Production Onboarding Smoke Test

After local source files are prepared under `data_sources/lexicons/`, run:

```bash
python -m framework.canonical_library build-db --output .bhf/ckl.sqlite
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --source-manifest data_sources/lexicons/lexicon-sources.json \
  --rebuild
python -m framework.canonical_library verify-db --database .bhf/ckl.sqlite
python tools/lexicon_onboard.py \
  --manifest data_sources/lexicons/lexicon-sources.json \
  --database .bhf/ckl.sqlite \
  --coverage-json examples/lexicon-coverage.example.json
python tools/lexicon_smoke.py \
  --database .bhf/ckl.sqlite \
  --coverage-json examples/lexicon-coverage.example.json
```

The onboarding coverage check verifies known required tokens such as John 1:1
`λόγος / G3056` and Psalm 23:6 `חֶסֶד / H2617`. Add more coverage checks for
any source bundle before treating it as production-ready. Use
`examples/lexicon-coverage.expanded.example.json` for a broader Hebrew/Greek
sample once full production datasets are imported.

`lexicon_onboard.py` checks database coverage directly. `lexicon_smoke.py`
checks the same `StudyActionRouter -> WordStudyService` path used by the Word
Study context menu.
