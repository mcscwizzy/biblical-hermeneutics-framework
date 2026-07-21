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

## Approved Source Plan

| Dataset | Source Repository | Pinned Revision | Data Used | License | Attribution | Redistribution Status | Import Command |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Open Scriptures Strong's dictionaries | To be pinned in Phase 2/4 | Not yet pinned | Strong's-linked definitions where legally permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| Open Scriptures HebrewLexicon | To be pinned in Phase 2 | Not yet pinned | Hebrew lemmas, glosses, BDB-linked data where permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| Open Scriptures morphhb | To be pinned in Phase 2 | Not yet pinned | Hebrew surface forms, lemmas, Strong's IDs, morphology, verse positions | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| MorphGNT | To be pinned in Phase 4 | Not yet pinned | Greek surface forms, lemmas, morphology, verse positions | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |
| Abbott-Smith Greek lexicon | To evaluate in Phase 4 | Not yet pinned | Greek definitions only if redistribution is permitted | To inspect before import | Preserve upstream attribution | Not bundled yet | Future source parser |

## Phase 1 Import

Phase 1 includes an importer for explicit normalized JSON payloads. It is used
for fixtures and as the target contract for later source-specific parsers.

```bash
python -m framework.canonical_library build-db
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --normalized-json tests/fixtures/lexicon_phase1.json \
  --rebuild
```

The importer:

- Uses a SQLite transaction
- Records source revision, license, attribution, import timestamp, and content
  hash
- Rebuilds only generated lexical tables when `--rebuild` is passed
- Fails clearly on malformed required fields
- Does not download anything

## Update Procedure

1. Inspect the upstream license.
2. Pin a release tag or commit SHA.
3. Record repository URL, revision, license, attribution, redistribution status,
   and import command in this file.
4. Import into a generated SQLite database.
5. Run lexical repository and importer tests.
6. Do not commit raw source data unless redistribution has been confirmed and
   the repository explicitly chooses to vendor it.
