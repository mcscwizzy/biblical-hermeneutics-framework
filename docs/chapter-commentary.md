# BHF Commentary v1.0

BHF Commentary is an evidence-grounded contextual aid for studying the
canonical Bible chapter by chapter. It is designed to help an ordinary reader
notice historical, cultural, literary, geographical, and related context
without presenting itself as a replacement for Scripture or as a theological
authority.

## Generation philosophy

Each chapter is built from the complete canonical chapter text and the current
BHF EvidenceBundle. The Luna development workflow synthesizes commentary only
from that supplied material. The model's general training is not treated as
evidence. Missing CKL evidence is allowed to remain missing; unrelated or
unanchored material is not substituted.

Evidence availability is classified deterministically:

- `AVAILABLE`: anchored evidence is sufficient for normal contextual
  commentary.
- `THIN`: some anchored evidence exists, so commentary is shorter and more
  conservative.
- `DATA_GAP`: no valid anchored CKL evidence exists. Output is limited to
  observations supported directly by the canonical text and does not invent
  contextual citations.

These labels describe evidence coverage, not theological quality.

## Validation and provenance

The validator enforces JSON structure, supported section kinds, chapter
identity, canonical verse references within the requested chapter, evidence
IDs, confidence ceilings, dispute labeling, block length, and explicit dates
against cited evidence. The application stamps the evidence hash, evidence
bundle version, commentary schema and prompt versions, model provenance, and
generation timestamp. Stored files are written atomically and progress is
rescannable from disk.

Validation is a contract check, not a complete semantic or theological review.
It cannot establish that every interpretation is correct, and the corpus does
not claim that all disputed questions are settled. Human review remains
important, especially where CKL coverage is thin or interpretations are
contested.

## Scope and limitations

Commentary v1.0 covers all 1,189 canonical chapters in the release corpus.
Coverage is not uniform: the corpus includes AVAILABLE, THIN, and DATA_GAP
chapters. A DATA_GAP is an honest CKL coverage result, not evidence that no
historical or scholarly information exists elsewhere.

BHF Commentary is not a replacement for Scripture, a doctrinal answer key, or
a substitute for careful study and theological judgment. It is an evidence-
grounded contextual aid intended to support reading in historical and cultural
setting.

## Operational commands

Progress is recoverable from the canonical chapter set and stored JSON files:

```bash
python -m bhf_agent.chapter_commentary status --rescan
```

Normal production resume skips only current `validated` files. Partial,
needs-review, failed, stale, and pending chapters are eligible for generation.
Use `build --partial-only`, `--needs-review-only`, `--failed-only`, or
`--stale-only` for focused retries.

The default model output ceiling is 4,500 tokens. Set
`BHF_COMMENTARY_MAX_TOKENS` to a positive integer for a different ceiling; the
prompt still asks for concise prose and the validator still caps each block at
2,000 characters.

Corpus health metrics can be generated with:

```bash
python tools/commentary_health_report.py \
  --json .bhf-data/bhf-commentary/commentary-health-report-v1.0.json
```

The health report measures coverage, validation state, structure, evidence
usage, citation and verse integrity, size distributions, and repetition
indicators. It is descriptive observability, not a theological quality score.
