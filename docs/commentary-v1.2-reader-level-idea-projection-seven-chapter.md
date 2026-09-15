# Commentary v1.2 reader-level idea projection — seven-chapter validation

Status: **`READER_IDEA_PROJECTION_7_CHAPTER_NOT_READY`**

This is the bounded validation namespace for `prompt 1.7` plus
`reader-level-idea-projection-v1`. It does not modify prompt 1.7, CKL records,
evidence routing, synthesis, projection logic, scoring, or Gate v2.1.

## Frozen identity

- Starting SHA: `cc4b485c529b7a67597be471418b72669bdf6e2e`
- Branch: `feat/commentary-v1.2-enrichment`
- Prompt diagnostic: `renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1`
- Prompt version: `1.7`; prompt 1.8 was not created or used
- Projection: `reader-level-idea-projection-v1`
- Renderer contract: `gpt-5.6-sol`, medium effort
- Immutable namespace: `.bhf-data/bhf-commentary-candidates/reader-level-idea-projection-v1-seven-chapter-e01fcbe6fe39ba6949fc`
- Frozen scoring: `essential-passage-context-v2`, `reader-relevance-eligibility-v1`, `commentary-richness-clusters-v2`, `commentary-richness-policy-v3-reader-relevance`, `commentary-richness-gate-v2.1`

The existing prompt-1.7 baseline manifest rebuilt byte-for-byte. Existing
worktree modifications were preserved. No authorized GPT-5.6 Sol endpoint or
complete external response bundle was available, so six candidate generations
were not attempted, selectively retried, substituted, or relabeled. The
previous immutable Revelation 21 candidate was reused as explicitly permitted.

## Projection audit

All seven projections are deterministic and preserve eligible cluster IDs,
synthesis-unit IDs, and evidence IDs. `CORE`/`RELEVANT` counts are projection
labels derived from the existing frozen eligibility contract; they do not alter
the scorer.

| Chapter | Synthesis units | Eligible clusters | Projected ideas | Grouped relationships | CORE | RELEVANT | Ancestry |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Isaiah 13 | 7 | 2 | 2 | 0 | 0 | 2 | preserved |
| Romans 3 | 25 | 4 | 4 | 0 | 1 | 3 | preserved |
| 1 Corinthians 14 | 33 | 7 | 7 | 0 | 0 | 7 | preserved |
| Revelation 20 | 21 | 6 | 4 | 3 | 0 | 4 | preserved |
| Revelation 21 | 119 | 16 | 8 | 23 | 0 | 8 | preserved |
| Exodus 14 | 34 | 2 | 2 | 0 | 1 | 1 | preserved |
| Deuteronomy 10 | 40 | 1 | 1 | 0 | 1 | 0 | preserved |

The dense Revelation 21 projection retains the proven eight-idea compression.
The sparse Exodus 14 and Deuteronomy 10 projections remain small; no
artificial expansion was introduced at the input layer.

## Before / after metrics

The baseline values are the immutable prompt-1.7 diagnostic values. A dash
means that the candidate response was not generated and therefore was not
scored. The only candidate row available is the reused Revelation 21 response.

| Chapter | Baseline weighted | Candidate weighted | Baseline eligible | Candidate eligible | Core | Category | Dump | Gate | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Isaiah 13 | 1.0000 | — | 1.0000 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |
| Romans 3 | .8000 | — | .7500 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |
| 1 Corinthians 14 | .7143 | — | .7143 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |
| Revelation 20 | .8056 | — | .8333 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |
| Revelation 21 | .4615 | 1.0000 | .5000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | REUSED_PRIOR_CANDIDATE |
| Exodus 14 | 1.0000 | — | 1.0000 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |
| Deuteronomy 10 | 1.0000 | — | 1.0000 | — | — | — | — | — | AWAITING_EXTERNAL_RENDERER |

### Revelation 21 confirmation

The reused candidate response SHA-256 is
`6ef87cb24cd3bec64653019ccbe8f4ac47e9320b6b8e0614c252c66caef88080`.
It remains structurally valid with zero hard provenance errors, weighted
coverage `1.0000`, eligible utilization `1.0000`, core coverage `1.0000`,
category coverage `1.0000`, HIGH dump count `0`, Gate `PASS`, and 457 prose
words. All eight projected ideas have a consumed synthesis ancestor; the prior
qualitative audit records natural readability, no material redundancy, and no
checklist-like behavior.

Prose length decreased from the baseline 622 words to 457 words, a delta of
`-165` words.

### 1 Corinthians 14

No candidate conclusion is made because the variant response was not generated.
The baseline remains `.7143` weighted and `.7143` eligible with category
coverage `.8333`. Its prior forensic interpretation—possible scorer-versus-
prose semantic edge case—remains unchanged and must not be addressed by
duplicating prose or changing scoring.

## Qualitative review

The only available candidate, Revelation 21, retains the prior positive review:
natural English, coherent chapter explanation, no evidence-inventory feel, no
checklist structure, no abrupt transitions, and no meaningful redundancy. The
other six candidate qualitative dimensions are intentionally marked
`NOT_REVIEWED_CANDIDATE_NOT_GENERATED` in the namespace. Treating their
baseline prose as candidate prose would invalidate the experiment.

## Tests

Focused validation results:

- `tests/test_commentary_v12_reader_projection_seven_chapter.py`: **6 passed**
- `tests/test_reader_level_idea_projection.py`, `tests/test_commentary_renderer_selection_breadth_diagnostic.py`, and the new seven-chapter suite: **25 passed**
- Warnings: none reported by the focused runs

These tests cover projection determinism, ancestry preservation, sparse/dense
behavior, candidate import/evaluation, prompt 1.7 immutability, scoring
contract immutability, and seven-chapter artifact reproducibility.

## Final classification and bounded next step

`READER_IDEA_PROJECTION_7_CHAPTER_NOT_READY`

This is an execution-completeness result, not evidence of a projection
regression. The smallest remaining issue is renderer availability: obtain one
exact GPT-5.6 Sol medium response for each of the six missing variant prompts,
then evaluate all seven in a fresh immutable namespace using the unchanged
contracts. Do not create prompt 1.8, alter scoring, or modify the projection
before that comparison.

If all seven then pass the stated structural, provenance, dump, readability,
and aggregate criteria, the next step is a fresh frozen 21-chapter renderer
qualification using `prompt 1.7 + reader-level-idea-projection-v1`.
