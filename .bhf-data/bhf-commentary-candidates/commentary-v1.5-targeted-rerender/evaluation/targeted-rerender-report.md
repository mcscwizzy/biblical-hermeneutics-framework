# Commentary 1.5 targeted rerender evaluation

Classification: **DENSE_AVAILABLE_CALIBRATION_SUCCESS**

Prompt 1.5 was evaluated with schema 1.2 and frozen commentary-richness-gate-v2.1. Renderer: GPT-5 Codex; reasoning effort: NOT_EXPOSED.

| Reference | 1.4 weighted | 1.5 weighted | 1.4 CORE | 1.5 CORE | 1.4 categories | 1.5 categories | 1.4 blocks/words | 1.5 blocks/words | 1.5 utilization | 1.5 consolidation | 1.5 dump | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Amos 5 | 0.2766 | 0.9255 | 1.0000 (0) | 1.0000 (0) | 1.0000 | 1.0000 | 3/134 | 4/278 | 0.7143 | 0.8519 | NONE | PASS |
| Mark 7 | 0.6552 | 1.0000 | 0.0000 (1) | 1.0000 (1) | 1.0000 | 1.0000 | 5/194 | 5/306 | 0.5000 | 0.8571 | NONE | PASS |
| 1 Corinthians 11 | 0.4062 | 0.8229 | 1.0000 (0) | 1.0000 (0) | 0.8571 | 0.8571 | 5/222 | 7/415 | 0.2941 | 0.8250 | NONE | PASS |
| Hebrews 4 | 0.4341 | 0.9070 | 1.0000 (2) | 1.0000 (2) | 1.0000 | 1.0000 | 5/194 | 7/377 | 0.6538 | 0.7500 | NONE | PASS |

All four raw responses imported and validated safely. No response was manually repaired; rejected count was zero. Gate v2.1 passed all four, dump severity was NONE for all four, and the renderer preserved cross-unit consolidation without one-unit-per-block behavior.

The four packet rows retain the original evidence and synthesis hashes and compiler/schema versions; only the prompt contract changed from 1.4 to 1.5. Prompt 1.4 responses remain under the preserved Batch 2 directory.

v1.1 protected fingerprints: PASS; CKL integrity: PASS; Batch 3 processed: False; bulk authorization: False.

ReaderSynthesisPlan status: NOT_NEEDED. Recommendation: PROCEED_TO_BATCH_3, with Prompt 1.5 and Gate v2.1 frozen.
