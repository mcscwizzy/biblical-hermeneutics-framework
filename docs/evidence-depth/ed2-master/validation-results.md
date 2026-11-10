# Validation results

## Baseline

- Strict CKL validation: 687 valid; 0 errors; 14 warnings, all `incomplete_section_status` inherited from the base.
- ED-1A chapter audit: pass, 1,189 rows, 0 unmapped identities.
- Deep heuristic report: 63 flagged errors and 986 warnings. Report separately from strict validation; neither count is a scholarly adjudication.
- Protected NE-9C/NE-10 state: no branch changes at baseline. The historical curation fingerprint validation is expected to be incompatible with current CKL after ED-2A integration. Keep historical checkpoints unchanged and verify decision identities/artifact bytes against the base.

Wave-level CKL/schema, manifest, Scripture-anchor, source, projection, source disclosure, relationship, and regression results will be appended after each batch.

## Wave A, batch A1 — Psalms 55, 60, 66, 75, 80, 81, 97, 100

- Strict CKL validation: 687 valid objects, 0 errors, 14 warnings. All warnings are the same inherited `incomplete_section_status` issues listed at baseline.
- Manifest: generated manifest agrees with the checked manifest; no manifest edit was needed.
- ED-1A audit: pass, all 1,189 chapters inventoried, 0 unmapped identities. Passage-specific chapters increased 993→1,001; chapters with no eligible passage-specific material decreased 124→116. All eight target Psalms transitioned to passage-specific eligibility.
- CKL deltas: 8 typed evidence items, 7 new source identities, one existing source identity reused, and no claims or objects added. No authored `related_objects` or `related_evidence` relationships were added; Narrative Explorer produced only the expected passage-anchor projection edges.
- Source and anchor integrity: all new source IDs resolve; the exact anchors and source locators pass strict checks. Psalm 75’s limited access is reflected in its low confidence and source notes.
- Narrative Explorer regression: 66 tests passed with 8 subtests. Exact anchors, item projection, source details/locators, draft and review disclosure, and absence of authored cross-passage links were checked.
- Deep heuristic report: 63 flagged errors and 994 warnings, compared with 63 and 986 at baseline. These heuristic warnings are not strict validation errors or scholarly-quality adjudications.
- Protected relationship state: this batch adds only evidence and source data. NE-9C and NE-10 records, decisions, and runtime relationship registries are unchanged; the historical NE-9C full-tree fingerprint is not regenerated.
