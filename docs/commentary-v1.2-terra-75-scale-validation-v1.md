# Commentary v1.2 Terra 75-chapter scale validation

This validation used the exact frozen 75-chapter population
`eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394` on
`feat/commentary-v1.2-enrichment`, starting at
`ee29855a824fbb6d2384df392bbf84556f2f4b0f`.

## Why the run proceeded

The fifth Sol control, Psalms 2, remained unavailable because of provider
usage exhaustion. It had no response, no retry, and no substitute model. The
four completed Sol controls were preserved, and the comparison remains
`4_OF_5_COMPLETE_COMPARISON_PENDING`. This does not prevent an independent
Terra reliability measurement.

The existing 25 Terra High generations were reused because they are valid
members of the frozen population, structurally validated, and already bound
to the same Prompt 1.8 and protected contracts. Regenerating them would have
changed the measurement and violated the no-duplicate-generation rule.

## Population and generation result

The remaining population contained 50 chapters. Forty-two were renderer
eligible and received exactly one Terra High generation. Eight had no legal
renderer path and were recorded as `NOT_RENDERABLE_SOURCE_LIMITED`:

`Isaiah 3`, `Psalms 122`, `Judges 3`, `Judges 8`, `Isaiah 63`,
`Revelation 8`, `Revelation 15`, and `Numbers 31`.

Together with the reused pilot, Terra produced 67 outputs for 75 chapters
(89.33% population coverage). There were no model-provider failures after a
local Codex state-database bootstrap issue was recovered, no quality retries,
and no model substitution.

Across the 67 generated outputs:

- Structural PASS: 64/67 (95.52%)
- Provenance PASS: 64/67 (95.52%)
- Ancestry PASS: 67/67 (100%)
- Gate PASS: 62/67 (92.54%)
- Readability PASS: 64/67 (95.52%)
- Normal-reader usefulness PASS: 62/67 (92.54%)
- First-attempt structural pass rate: 95.52%
- Retries: 0
- HIGH dumps: 0
- Unsupported-claim findings: 0

Mean commentary length was 222.45 words; median 185; minimum 47; maximum
832. Mean evidence-path utilization was 0.9023 and median utilization was
0.7033. Terra usage was available for all 67 chapters: 1,911,269 input
tokens, 771,328 cached-input tokens, 72,221 output tokens, and 28,678
reasoning-output tokens. Average input was 28,526.4 tokens per completed
chapter and average output was 1,077.93 tokens.

## Where failures clustered

The failures are predominantly evidence/content-shaped rather than a common
provenance or canonical-text defect. The aggregate classifications were:

| Classification | Count |
| --- | ---: |
| PASS | 38 |
| UNDER_EXPLANATION | 24 |
| STRUCTURAL_MODEL_FAILURE | 3 |
| SOURCE_LIMITED | 2 |
| NOT_RENDERABLE_SOURCE_LIMITED | 8 |

The eight non-renderable chapters are source-limited. The 24
`UNDER_EXPLANATION` results generally had safe structure and provenance but
did not make enough of the available evidence useful to a reader. The three
structural failures are isolated model-output failures, not a repeated
contract or ancestry failure.

By literary category, all four Acts chapters passed the Gate and usefulness
checks. The strongest generated-category Gate rates were Minor Prophets
(8/8), Torah (7/8), and General Epistles (6/7). The main content gaps were
Major Prophets (two non-renderable chapters), Apocalyptic literature (two
non-renderable chapters and three under-explanations), Poetry/Wisdom (one
non-renderable chapter, one source-limited result, and one structural failure),
and Gospels/Pauline Epistles where under-explanation clustered despite good
legal coverage.

By evidence state, `EVIDENCE_RICH` had 7/10 Gate passes and two structural
failures; `EVIDENCE_PARTIAL` had 18/19 Gate passes but 12
under-explanations; and `EVIDENCE_FOCUSED` had 15/15 Gate passes with six
under-explanations. The state report is in the artifact rather than inferred
from the global rate.

## The five enriched controls

Genesis 5, Psalms 2, Psalms 19, Psalms 103, and 2 Kings 4 all completed the
Terra control packet as Terra outputs. Each passed structure, provenance,
ancestry, and the Gate, but each was classified as `UNDER_EXPLANATION` by
the reader-quality layer. The lesson is useful: the hardened pipeline safely
preserves evidence boundaries on these difficult controls, while the current
source packets still do not consistently yield sufficiently explanatory
reader prose. That is a content backlog signal, not justification for a new
prompt or architecture version.

Known Psalm heading-boundary contamination was handled only through the
validated task-local safe-text projection for Psalms 2, 8, 22, 122, and 137.
The ASV file was not changed.

## Human review and content backlog

The reproducible human-review sample contains 10 reader-facing outputs across
at least 5 literary categories, multiple evidence states, short and long outputs,
and at least two of the five enriched controls. It contains no model-debug
metadata. The backlog prioritizes the eight zero-renderable chapters first,
then chapters with strong canonical text but inadequate current-chapter
coverage or repeated under-explanation.

No CKL records were modified. The next content action is to enrich the eight
zero-renderable chapters with chapter-specific, non-inherited evidence, then
re-run only the affected content pass.

## Production interpretation

The Terra population result is classified
`TERRA_PIPELINE_SCALE_VALIDATED_WITH_CONTENT_GAPS`. Terra is provisionally
supported as the default renderer pending the fifth Sol control:
`PROVISIONAL_TERRA_DEFAULT_PENDING_FINAL_SOL_CONTROL`.

The v1.2 release-readiness conclusion is
`V1_2_READY_FOR_PRODUCTION_INTEGRATION_WITH_KNOWN_CONTENT_GAPS`. This means
the application may integrate the existing safe pipeline while preserving
thin-source failure behavior; it does not mean CKL coverage is complete.
Production routing was not changed in this task. The smallest engineering
action is to integrate the Terra-backed commentary path behind the existing
contracts. The smallest product/content action is the eight-chapter source
enrichment pass.

## Artifact and verification

The immutable artifact namespace is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2/`

The final report is `final-report-v2.json`; the human sample is
`human-review-sample-final.json`; checksums are in `checksums-v2.json`.
Focused deterministic tests are in
`tests/test_commentary_v12_terra_75_scale_validation.py`.
