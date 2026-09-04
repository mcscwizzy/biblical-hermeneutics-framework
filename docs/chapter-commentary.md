# BHF chapter commentary generation

Chapter commentary follows the existing evidence-bundle → model → validation →
salvage → per-chapter JSON pipeline. The application, rather than the model,
stamps evidence hash, bundle/schema/prompt versions, model name, and generation
timestamp.

The validator deterministically enforces JSON structure, supported section kinds,
requested chapter identity, canonical verse references within that chapter,
evidence IDs, confidence ceilings, dispute labeling, block length, and explicit
dates that appear in cited evidence. It does not claim to detect every semantic
hallucination: invented significance and unsupported entities remain deferred
until the evidence contract exposes safe deterministic fields.

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
