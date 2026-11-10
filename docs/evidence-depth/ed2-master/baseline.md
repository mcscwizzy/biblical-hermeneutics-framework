# ED-2 Master baseline

## Reproduction

- Baseline commit: `04eed56ece941f9efce2f7f05b3908baf0197648` (`origin/master`, with ED-2A merged).
- Command: `python3 scripts/audit_ed1a_evidence_depth.py --output-dir /tmp/ed2-master-baseline --study-db .bhf-data/study.sqlite`.
- Result: audit status **pass**, 1,189 of 1,189 canonical chapters inventoried, zero unmapped record identities. Inventory fingerprint: `45bc240f39f258fc9ef46c62d083eef87d8d60a346d40052ed0b1895c8156095`.
- Full machine output was kept under `/tmp/ed2-master-baseline/` and is not committed. The committed backlog retains chapter-level measures and triage rationale.

## CKL baseline

- Objects: 687 (66 book records).
- Claims: 2329; typed evidence items: 1309; interpretive notes: 3691.
- Source record occurrences: 5247; unique IDs in the source identity audit: 2798; 2,240 IDs have title and traceability detail; 558 lack a title or sufficient bibliographic detail.
- Child source references: 17512; 2 unresolved references. There is one expected-locator warning for `patristic-minor-prophets`.
- The audit detects 81 source IDs whose non-empty identity metadata varies and 148 with locator variation. These are inherited inventory review signals, not automatically adjudicated defects.
- The lexicon has entries for both languages and verse-word rows for all 1189 chapters; this is general lookup coverage, not curated passage-specific lexical scholarship.

## Passage-specific eligibility

| Baseline category | Chapters |
| --- | ---: |
| Passage-specific evidence | 993 |
| Contextual coverage only | 68 |
| Entity-only coverage | 3 |
| No eligible material | 124 |
| Incomplete/unknown | 1 |

These counts are eligibility categories, not a quality score. `research-backlog.csv` retains chapter-specific evidence, anchor, source, and section measures. Candidate thinness is flagged for qualitative review; the count itself does not establish adequacy.

## Baseline validation and quality signals

- `python3 tools/ckl_validate.py --root framework/canonical_library`: 687 valid objects, 0 strict errors, 14 pre-existing warnings (`incomplete_section_status`).
- `python3 tools/ckl_report.py --deep --json`: 63 heuristic flagged errors and 986 heuristic warnings. These are a review inventory distinct from strict schema/manifest validation. They include inherited missing or incomplete bibliographic detail and other heuristic signals.
- Scripture reference validation: zero errors.
- Protected base artifacts are unchanged by this branch at creation. The exact NE-9C source fingerprint may not match the historical checkpoint after legitimate CKL changes; the accepted base already incorporates ED-2A. Do not regenerate historical checkpoints.

## Baseline interpretation limits

The audit reconstructs the ED-1A chapter census with current Narrative Explorer eligibility and each child record’s own Scripture anchors; broad parent anchors are not counted as passage-specific child scope. Audit tags such as `contextual`, `entity-only`, `unclassified`, missing source detail, or possible misanchor are audit signals. They do not replace reading the underlying passage and source.
