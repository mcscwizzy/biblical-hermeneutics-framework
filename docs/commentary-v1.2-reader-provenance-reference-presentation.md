# Commentary v1.2 reader-provenance reference presentation

## Issue

The Numbers 1 structural failure was not random model formatting. The selected
disputed provenance path itself carried the deliberate chapter-scoped source
reference `Numbers 1`:

`reader_path_numbers_001_4b56e1acc9b3f47af93f395b`

Both Prompt 1.8 renderer attempts reproduced that path's chapter-level scope.
The downstream validator requires ordinary prose blocks to serialize
verse-level references, so both attempts were rejected as
`AMBIGUOUS_VERSE_REFERENCE`.

## Remediation

The versioned renderer-reference presentation adapter preserves the immutable
source scope and path identity while deriving a renderer-facing serialization
only when exact equivalence is mechanically proven. For Numbers 1:

```text
source_verse_refs:   ["Numbers 1"]
renderer_verse_refs: ["Numbers 1:1-54"]
```

The final verse is derived from BHF's committed `bhf_agent/data/asv_bible.json`
through `bhf_agent.bible.resolve_chapter`; no hand-written verse-count table,
model knowledge, external API, prose inference, or synthesis rewrite is used.
The adapter requires canonical current-chapter identity, explicit
`CURRENT_CHAPTER` scope, genuine chapter-level synthesis scope, no competing
verse-specific anchor, and a contiguous canonical chapter boundary. Otherwise
it leaves the source reference unchanged and fails safely. Any post-generation
guard is path-constrained to a selected proven path and cannot infer a narrower
meaning from prose or chapter membership.

This is deterministic reference serialization, not semantic inference.

## Bounded validation

The immutable validation namespace is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-reader-provenance-renderer-reference-presentation-v1-bounded-validation-v1-ce695db52b3ad2d0e6f8`

The preflight active-path audit found:

- `VALID_ALREADY`: 59
- `SAFE_FULL_CHAPTER_SCOPE`: 1
- `AMBIGUOUS`: 0
- `INVALID_SOURCE_REFERENCE`: 0

The one fresh Numbers 1 generation passed structural, provenance, and ancestry
validation on the first attempt. The bounded five-case regression passed 5/5
final structural validity, 5/5 provenance validity, and 5/5 ancestry validity,
with zero retries, hard provenance errors, evidence leakage, normalization
events, and HIGH dumps. Quality remains a separate gate: Numbers 2 was `PASS`,
Numbers 1 was `PASS`, and 2 Kings 4, Psalms 103, and Psalms 19 remained
`QUALITY_FAIL`. Readability was `PASS` for all five cases.

The adapter does not authorize the 75-chapter pilot. Prompt 1.8, reader-level
projection, evidence, compiled synthesis, validator, scorer, Gate thresholds,
transport, model, effort, confidence, and dispute semantics remain unchanged.
