# Word Study

BHF word study support is being built around deterministic Greek and Hebrew
data. The model is an explanation layer only; lexical source data comes from
the local SQLite database.

## Current Runtime

The deterministic Word Study action now uses the standalone lexical SQLite
database at `framework/lexical/database/lexicon.sqlite` through an application
service layer. The model explanation path receives compact retrieved lexical
context only after deterministic data is found.

Docker builds generate a seeded lexical database at
`/app/.bhf-seed/lexicon.sqlite`. On first container start, the entrypoint copies
that seed to the mounted runtime path, `.bhf/lexicon.sqlite` on the host and
`/app/.bhf-data/lexicon.sqlite` in the container, if the runtime file is
missing.

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

If `framework/lexical/database/lexicon.sqlite` is missing, startup logs a
diagnostic with the expected path and build command. Word Study should treat
lexical data as unavailable in that state; it must not invent Hebrew or Greek
definitions, Strong's numbers, or lexical ranges from model memory.

In Docker, if Word Study is still using an old lexical database, remove
`.bhf/lexicon.sqlite` and rebuild/restart the web container so the image seed is
copied into the mounted runtime directory.

For download, build, and verification commands, see
[`compile-lexicon.md`](compile-lexicon.md). The smoke test intentionally fails
clearly when the database is missing and prints the import command needed to
create it in the runtime location.

Older CKL lexical source-manifest tooling remains documented in
`docs/lexicon-sources.md` for legacy fixtures and broader source imports:

```bash
python tools/import_lexicons.py --output .bhf/ckl.sqlite --source-manifest <manifest.json> --rebuild
```
