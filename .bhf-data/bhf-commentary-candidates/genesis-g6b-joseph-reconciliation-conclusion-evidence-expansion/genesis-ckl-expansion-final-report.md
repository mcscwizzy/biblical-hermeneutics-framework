# Genesis CKL expansion final report

Base master: `dde95a3fa41ea47f716f3b22de7b8f1e7c59a43e`.

## G0 to final coverage

Starting G0 totals: GOOD 3, THIN 3, SPARSE 6, GAP 38.
Final Genesis 1–50 totals: GOOD 49, THIN 1, SPARSE 0, GAP 0.
Genesis 45 is the only chapter below GOOD. It has 16 retrieved evidence items and 10 synthesis units, but only four fully COVERED dimensions. Remaining dimensions: immediate literary context (THIN), archaeology/material culture (THIN), historical context (THIN), and intertextual/canonical connections (GAP). The other chapters are GOOD; no weak items were added to raise the count.

## Transaction ledger

| Transaction | Scope | New objects | Evidence added | Source records added | Final classification |
|---|---|---:|---:|---:|---|
| G1 Primeval Origins | Genesis 1–5 | 0 | 32 | 11 | Genesis 1–5 GOOD |
| G2 Flood/Post-Flood | Genesis 6–9 | 1 | 25 | 29 | Genesis 6–9 GOOD |
| G3 Nations/Babel | Genesis 10–11 | 1 | 29 | 20 | Genesis 10–11 GOOD |
| G4A Abraham Call/Covenant | Genesis 12–17 | 1 | 46 | 17 | Genesis 12–17 GOOD |
| G4B Abraham Late Cycle | Genesis 18–25 | 1 | 71 | 11 | Genesis 18–25 GOOD |
| G5A Isaac/Jacob Transition | Genesis 26–30 | 1 | 51 | 12 | Genesis 26–30 GOOD |
| G5B Jacob/Esau Return | Genesis 31–36 | 1 | 68 | 14 | Genesis 31–36 GOOD |
| G6A Joseph Descent/Testing | Genesis 37–44 | 1 | 78 | 16 | Genesis 37–44 GOOD |
| G6B Joseph Reconciliation/Conclusion | Genesis 45–50 | 1 | 77 | 15 | Genesis 45 THIN; Genesis 46–50 GOOD |

Across Genesis work, CKL objects changed 679 → 687 (+8), evidence items 815 → 1292 (+477), and source records 5081 → 5226 (+145).

## Architecture lessons

- Comparative Scripture applicability can leak a passage-domain object into another book when contextual texts are stored as direct anchors; G1R repaired the three G1 Genesis 3 items and documented the retrieval semantics.
- Legacy-fallback shared objects contain broad legacy fields whose applicability behavior differs from isolated structured evidence. G2R2 established isolated passage-domain objects and did not migrate or mutate legacy shared objects.
- Source ownership is coupled to canonical object ownership and may change chapter identities. Later transactions used object-local source aliases that preserve full bibliographic identity and keep historical source-owner rows stable.
- Isolated passage-domain cultural_background objects with one-way typed relationships provide chapter-specific structured evidence without attaching new source ownership to broad Genesis or shared people/places/topics.
- Whole-corpus exact-impact gates across all 1,189 chapter preparations detect unintended identity drift; target-only checks are insufficient to prove isolation.
- Coverage classification is dimensional and synthesis-aware. Genesis 45 remains THIN with a documented dimension deficit rather than padded evidence.

## Final G6B result

Added `genesis-joseph-reconciliation-conclusion-context` (`cultural_background`) with 77 evidence items and 15 object-local source records. Existing historical source-owner rows changed: 0. The exact 1,189-chapter changed set is Genesis 45–50, and all 26 controls match the G6B base.

Commentary v1.2 stayed frozen. The deterministic stale-input set is Genesis 2–50 (49 chapters); Genesis 45–50 are included for the later refresh transaction.

Current merge-gate state: `GENESIS_G6B_JOSEPH_RECONCILIATION_CONCLUSION_EVIDENCE_MERGE_GATE_VERIFIED`. No merge, deploy, or Commentary regeneration occurred.
