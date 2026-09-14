# Commentary v1.2 richness scoring remediation

This bounded pass changes only the richness denominator.  It does not change CKL, Commentary v1.1, validation, provenance or ancestry checks, Gate v2.1, or the qualification threshold of 0.75.

## Frozen inputs

Branch: `feat/commentary-v1.2-enrichment` (base `13cc63fb42be92b235233afe569212d966c31f0b`). Historical qualification ID: `renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a`. Historical remediation ID: `renderer-remediation-v1-gpt-5.6-sol-2d03bb002c24cdbcca72`.

All manifests, evaluation JSON, packets and raw responses are hashed in [`freeze/historical-results.json`](../.bhf-data/bhf-commentary-candidates/richness-scoring-remediation-v1/freeze/historical-results.json). Audits and counterfactual results live in the same immutable namespace; no response was regenerated.

## Diagnosis

The old scorer counted every non-OPTIONAL cluster.  The v3 audit found the following old weighted denominators:

| chapter | denominator | direct | significance | understanding kind | specific support | general support | entity-only background | surrounding | disputed | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exodus 14 | 13.4 | 7.46% | 0 | 0 | 0 | 0 | 88.81% | 0 | 3.73% | 0 |
| Deuteronomy 10 | 5.9 | 16.95% | 0 | 0 | 0 | 0 | 83.05% | 0 | 0 | 0 |
| Job 1 | 4.8 | 0 | 0 | 0 | 0 | 29.17% | 29.17% | 0 | 41.67% | 0 |
| Revelation 21 | 27.2 | 0 | 0 | 0 | 12.87% | 61.76% | 18.01% | 0 | 7.35% | 0 |

The complete cluster-level record (IDs, evidence, scope, consumption, signatures, eligibility judgment and reason) is [`denominator-audit-v3.json`](../.bhf-data/bhf-commentary-candidates/richness-scoring-remediation-v1/audit/denominator-audit-v3.json).

## Eligibility policy

`commentary-richness-policy-v3-reader-relevance` adds deterministic `coverage_eligibility`, classified by `reader-relevance-eligibility-v1`:

* CORE is REQUIRED; OPTIONAL is EXCLUDED_FROM_COVERAGE.
* DISPUTED is RELEVANT only for direct-context, book-context, intertextual-reuse or later-reception relationships.
* Specific contextual support is RELEVANT unless it is only a raw entity inventory.
* Generic entity/general context is RELEVANT only when at least half of its parent concepts occur as contiguous, non-template concepts in the canonical chapter text; otherwise it is CONTEXTUAL_OPTIONAL.
* Surrounding-passage material is contextual optional unless promoted by the preceding rules.

Thus entity IDs alone no longer enlarge required coverage.  A passage-relevant entity explanation still counts; encyclopedia-style location/person lists do not.  Eligibility is independent of quality class, and the old non-optional cluster count remains in dump diagnostics.

## Semantic overlap

[`revelation-21-overlap-v1.json`](../.bhf-data/bhf-commentary-candidates/richness-scoring-remediation-v1/audit/revelation-21-overlap-v1.json) compares parent families, facts, unit kinds and ancestry.  It found zero safe new merge candidates: creation, resurrection, exile, Jerusalem, temple and related records vary in reader dimension, unit kind or evidence ancestry. Existing exact/ancestry/parallel/high-fact rules are retained; no aggressive transitive rule was added.

## Counterfactual results

Five remediation responses (same raw bytes, no Sol call):

| chapter | old clusters / denominator / weighted | new eligible clusters / denominator / weighted | old→new result |
|---|---|---|---|
| Exodus 14 | 19 / 13.4 / .4254 | 2 / 1.5 / 1.0000 | QUALITY_FAIL → PASS |
| Deuteronomy 10 | 8 / 5.9 / .4068 | 1 / 1.0 / 1.0000 | QUALITY_FAIL → PASS |
| Job 1 | 8 / 4.8 / .4583 | 4 / 2.0 / .7500 | QUALITY_FAIL → PASS (omitted later-reception idea still costs coverage) |
| Revelation 21 | 40 / 27.2 / .3309 | 16 / 10.4 / .5288 | QUALITY_FAIL → PASS under Gate v2.1, still below the .75 qualification target |
| 1 Corinthians 14 | — | .7143; ancestry valid | remediation PASS; original historical response remains rejected |

Five-chapter aggregate changed from 4 quality failures to 0, with weighted coverage .7986, core 1.0, eligible idea utilization .8054, category .9667 and high dumps 0. Gate thresholds and behavior are unchanged.

The full original 21-response counterfactual has 20 structurally valid and one unchanged `SYNTHESIS_ANCESTRY_MISMATCH`, weighted coverage .9186, core 1.0, eligible idea utilization .9154, category 1.0, high dumps 0; outcome transitions are PASS→PASS 16, QUALITY_FAIL→PASS 4, REJECTED→REJECTED 1. Qualification therefore remains `NOT_QUALIFIED` solely because the historical 1 Corinthians response is structurally invalid.

## Controls and tests

The calibration artifact covers 22 accepted historical controls (13 v1.2 canaries and 9 v1.5 controls). Core regressions: 0; dump-severity changes: 0; rich-control and data-gap regressions: none. Genesis 1 remains a high-dump quality failure, so the remediation does not reward evidence dumping.

Focused tests: `29 passed` in `tests/test_commentary_v12_richness_clusters.py`; the renderer-remediation regression suite also passes. Tests cover unrelated entity exclusion, relevant entity inclusion, distinct ideas, redundant evidence consolidation, and an omitted Job-style reception idea.

## Bounded outcome

Result: **SCORING_REMEDIATION_PASS**. Failures classify as Exodus 14 and Deuteronomy 10 **SCORING_NOISE_RESOLVED**; Job 1 and Revelation 21 **MIXED_SCORING_AND_RENDERER_ISSUE**. No new GPT-5.6 Sol generation was necessary for this isolated scoring pass.

The next step is to freeze a new 21-chapter renderer qualification using prompt candidate 1.6 (including its ancestry safeguard) and the v3 scoring contract. Do not launch that generation as part of this remediation; the repository is now ready for it.
