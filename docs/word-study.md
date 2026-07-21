# Word Study

BHF word study support is being built around deterministic Greek and Hebrew
data. The model is an explanation layer only; lexical source data comes from
the local SQLite database.

## Current Phase

The deterministic Word Study action now uses CKL SQLite lexical tables through
an application service layer. The model explanation path receives compact
retrieved lexical context only after deterministic data is found.

## Runtime Data

When the lexical database is populated, runtime code can retrieve:

- Original-language word
- Lemma
- Transliteration
- Strong's identifier
- Morphology code and decoded morphology
- Concise gloss/definition data
- Verse word positions
- Representative occurrences by exact lemma
- Source attribution

If a selected English word cannot be aligned to one original-language token,
the UI should present all original words in the verse and let the user choose.
It should not guess silently.

## Interpretation Guardrails

Word-study displays and model explanations should warn against:

- Root fallacy
- Strong's-number fallacy
- Illegitimate totality transfer
- English reverse-lookup fallacy
- Morphology neglect
- Context neglect
- Frequency fallacy
- Etymology over context

Concise displays should show a brief caution by default, with fuller
explanation available in Scholar View.

## Compact Prompt Context

When a model explanation is requested, BHF should pass compact lexical context,
roughly 150-350 tokens by default. It should include source names and cautions,
but not full lexicon entries, raw XML, SQL, filenames, retrieval scores, or large
occurrence lists.

The answer should distinguish general semantic range from the likely
contextual sense and state uncertainty when the data does not determine a single
sense.

## Troubleshooting

If lexical tables are empty or missing, rebuild the generated CKL database and
then run the importer:

```bash
python -m framework.canonical_library build-db
python tools/import_lexicons.py --output .bhf/ckl.sqlite --normalized-json <payload.json> --rebuild
```

Future source-specific importers will add commands for Open Scriptures
Hebrew/Greek data and MorphGNT after each source license and revision is
recorded in `docs/lexicon-sources.md`.

For inspected local JSON/TSV source exports, use a source manifest:

```bash
python tools/import_lexicons.py --output .bhf/ckl.sqlite --source-manifest <manifest.json> --rebuild
```

Then verify runtime coverage:

```bash
python tools/lexicon_onboard.py --manifest <manifest.json> --database .bhf/ckl.sqlite
python tools/lexicon_smoke.py --database .bhf/ckl.sqlite
```

If this check fails, Word Study may still render ambiguity or unavailable
states for passages whose original-language tokens were not imported.
