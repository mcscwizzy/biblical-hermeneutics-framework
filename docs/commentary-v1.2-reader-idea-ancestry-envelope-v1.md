# Commentary v1.2 reader-idea ancestry envelope diagnostic

## Scope

This is a one-chapter diagnostic for `1 Corinthians 14` on
`feat/commentary-v1.2-enrichment`. It adds the bounded presentation layer
`reader-level-idea-ancestry-envelope-v1` to the frozen
`reader-level-idea-projection-v1` input. CKL, synthesis compilation, evidence
routing, scoring, richness clustering, reader-relevance eligibility, Gate
v2.1, prompt 1.7 selection breadth, and reader-level grouping semantics were
not changed. No prompt 1.8 was created.

## Original failure

The frozen seven-chapter diagnostic rejected `1 Corinthians 14` with
`SYNTHESIS_ANCESTRY_MISMATCH` in `section[0].block[2]` (`block_3`). The block
cited:

- synthesis: `syn_interpretive_questions_2b58756fa889`,
  `syn_interpretive_questions_48738fe0e7f8`
- evidence: `corinthian-tongues-sign-crux`,
  `corinthian-tongues-sign-crux:passage-relevance`,
  `corinthian-outsider-intelligibility`,
  `corinthian-outsider-intelligibility:passage-relevance`,
  `corinthian-participatory-order`,
  `corinthian-participatory-order:passage-relevance`,
  `corinthian-peace-order-not-suppression`,
  `corinthian-peace-order-not-suppression:passage-relevance`

The invalid pair was synthesis
`syn_interpretive_questions_48738fe0e7f8` → evidence
`corinthian-outsider-intelligibility`. That evidence is owned by
`syn_interpretive_questions_d2f573076d8d` (and also by the related
`syn_why_it_matters_e5e5571f98fb`). The cited unit owns only
`corinthian-outsider-intelligibility:passage-relevance`. All of these records
were grouped into `reader_idea_5112c0d207d0e64e`, whose projection artifact
retained flat `synthesis_unit_ids` and `evidence_ids` arrays. The frozen prompt
did not present explicit per-synthesis paths.

## Envelope representation

The new envelope retains the source projection identity and represents each
projected idea with `ancestry_paths`. Every path contains one existing
synthesis unit ID and the exact evidence IDs from that unit, plus existing
confidence, disputed/interpretation, passage-scope, kind, verse-anchor, and
hash metadata. It creates no parentage or IDs and does not merge evidence
across synthesis units. The envelope audit records:

- 7 projected ideas
- 33 explicit synthesis-unit paths
- full synthesis-ID preservation
- full evidence-ID preservation
- zero cross-synthesis path leakage
- no flat idea-level evidence list rendered
- no synthetic parentage

The renderer input is exactly `prompt 1.7 + projection v1 +
ancestry-envelope-v1`. It adds the instruction to pair evidence IDs only with
synthesis IDs from the same listed path; the existing validator remains the
authority and still rejects the original pair.

## Fresh candidate result

The isolated immutable namespace is
`.bhf-data/bhf-commentary-candidates/reader-idea-ancestry-envelope-v1-b970c53e1dc561f23530/`.

- source projection hash: `4aa6438d0b7ac7812c35060a1c6e9fcde8a6e6d4e0eb75917e50ec7c2d28cdf1`
- ancestry-envelope hash: `b62c50c1838f81e12573425165b9a469c9833a95eb5bbac28f42dc4ff4142f7b`
- candidate input SHA-256: `fa97d926287dec636db40338076e6d5b3ef7440956b93ffef6fb52f32027b86b`
- one fresh response SHA-256: `db49e68bd61b20bd6976f501eb8ad4015fa0462281814ab9334ac463fd824d56`
- generation count: `1`; retries: `0`

The candidate is structurally accepted. The existing validator reports zero
`SYNTHESIS_ANCESTRY_MISMATCH` errors and zero hard provenance errors. The
separate response path audit also reports zero ancestry mismatches, including
for the repaired visitor-scene block.

| Metric | Result |
| --- | ---: |
| Weighted coverage | 0.8571 |
| Core coverage | 1.0000 |
| Eligible idea utilization | 0.8571 |
| Category coverage | 1.0000 |
| Projected ideas represented | 6/7 |
| HIGH dump count | 0 |
| Dump severity | NONE |
| Gate | PASS |
| Prose blocks / words | 7 / 411 |

The omitted projected idea is the assembly-order label
`reader_idea_f205ac15edbe029b`; it was not forced into the response. The
qualitative review records natural English, readability, no checklist-like
behavior, no evidence-inventory feel, no material repetition, and no abrupt
transition regression.

## Classification

`ANCESTRY_ENVELOPE_PROMISING`

The envelope fixes the primary ancestry failure without weakening provenance.
The result is promising rather than perfect: 6/7 projected ideas were
represented, while the weighted and eligible metrics exceeded the requested
targets.

## Tests

The focused envelope suite has **7 passed** tests covering deterministic paths,
no cross-synthesis leakage, full ancestry preservation, projection-v1
immutability, prompt-1.7 immutability, unchanged validator rejection, and
artifact reproducibility. The existing projection suite has **14 passed** and
the existing renderer-diagnostic suite has **5 passed**. The combined focused
run is **26 passed**.

## Recommendation

Apply `ancestry-envelope-v1` to the full existing seven-chapter projection
diagnostic input, regenerate only a fresh complete seven-chapter immutable
diagnostic set, and—if all seven are structurally valid with no regressions—run
the fresh 21-chapter qualification. Do not change the validator or any
underlying evidence/projection contracts.
