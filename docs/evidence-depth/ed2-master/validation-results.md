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

## Wave A, batch A2 — Psalms 5, 20, and 25

- Strict CKL validation: 687 valid objects, 0 errors, and the same 14 inherited `incomplete_section_status` warnings.
- Manifest and reference integrity: generated manifest semantically matches the checked manifest. The first census surfaced an invalid `Psalm 5:1-13` anchor: that range used Hebrew numbering while the CKL canonical lookup follows English/ASV numbering, where Psalm 5 has 12 verses. The anchor is corrected to `Psalm 5:1-12`; the item and packet clarify both numbering systems. The corrected full census reports 0 unmapped identities and no incomplete lookup caused by the new records.
- ED-1A census: pass, 1,189/1,189 chapters; 1,004 passage-specific, 68 contextual-only, 3 entity-only, 113 no eligible, and 1 incomplete/unknown. Eleven baseline zero-eligible Psalms now have eligible material across A1/A2; 55 Psalm chapters remain with no eligible item.
- CKL deltas: 3 typed evidence items, 4 source identities created, no claims or objects added, and no authored cross-passage relationship entries. The source register records exact identities and which text source was reused.
- Source limits: the full Ward dissertation and Botha and Human articles were inspected. Kister’s institutional record and abstract were inspected, but not its full article; it is cited only as confirmation that a recent Psalm 20/Amherst 63 study exists, not for its detailed conclusions. The dissertation source uses schema type `other` because CKL has no dissertation type.
- Narrative Explorer: 69 tests passed with 11 subtests. Exact verse scope, source and locator disclosure, primary observation and interpretation, confidence/dispute/review metadata, and absence of authored cross-passage links were checked.
- Deep heuristic report: 63 flagged errors and 998 warnings, versus 63/986 at baseline and 63/994 after A1. A2’s four additional warnings are three unknown passage chronologies (the compositions/settings remain unresolved) and one heuristic `weak-source-type` warning for the dissertation’s schema-valid `other` type. No new heuristic errors were introduced; these are review signals, not strict validation failures.
- Protected relationship state: only the Psalms CKL object and ED-2 test/docs changed. No NE-9C/NE-10 decision, bridge, curation, or runtime relationship registry was changed; historical checkpoints were not regenerated.

## Wave A, batch A3 — Psalms 7, 11, 14, 17, 21, 26, 33, 43, 49, 83

- Strict CKL validation: 687 valid objects, 0 errors, 14 warnings. The same 14 `incomplete_section_status` warnings are inherited from the base.
- Manifest and reference integrity: the generated manifest semantically matches the checked manifest; all 10 Scripture anchors validate, and no source or evidence target is unresolved.
- ED-1A chapter census: pass, 1,189/1,189 rows and 0 unmapped identities. Coverage is 1,014 passage-specific, 68 contextual-only, 3 entity-only, 103 no-eligible, and 1 incomplete/unknown. Psalms is 82 passage-specific and 45 no-eligible.
- CKL deltas: 10 evidence items, 11 new scholarly source identities, no claims or CKL objects, and no authored relationship edges. The audit now counts 1,330 typed evidence items, 5,269 source occurrences, and 2,820 source identities. The inherited two unresolved child-source references and one missing expected locator remain unchanged.
- Reader projection: the A3 regression tests cover exact chapter/verse eligibility, reader projection, evidence/source disclosure, observation and interpretation fields, confidence/dispute/review metadata, and no authored cross-passage links. Targeted regression result: 71 passed; 21 subtests passed.
- Deep heuristic review: 63 error-severity findings and 1,010 warnings versus 63/998 after A2. There are no new heuristic errors. The 12 added warnings are 10 unknown-passage-chronology notices (the composition/settings are unresolved) and 2 `weak-source-type` notices for dissertations using CKL’s schema-valid `other` type. They remain heuristic signals, not strict validation failures or scholarly adjudications.
- Protected decisions: the batch changes only the Psalms CKL object, ED-2 tests, and ED-2 documentation. No NE-9C curation, NE-10 bridge/hold, API contract, or relationship registry was changed; no historical checkpoint was regenerated.


## Wave A, batch A4 — Psalms 46, 56, 77, 91, 92, 105, 111, 139

- Strict CKL validation: 687 valid objects, 0 errors, and 14 inherited `incomplete_section_status` warnings. The schema and source-target checks pass.
- Manifest and references: generated manifest semantically matches the checked manifest; all eight exact Scripture references and source-support IDs resolve. No existing CKL claim, object, or source support was rewritten.
- ED-1A census: pass, all 1,189 chapter rows, 0 unmapped identities. Coverage is 1,022 passage-specific, 68 contextual-only, 3 entity-only, 95 no-eligible, and 1 incomplete/unknown. Psalms is 90 passage-specific and 37 no-eligible. Each of the eight A4 target Psalms became eligible.
- CKL deltas: 8 typed evidence items, 8 new source identities, 0 claims or CKL objects. Overall totals are 687 objects, 2,329 claims, 1,338 typed evidence items, 5,277 source-record occurrences, and 2,828 source identities. The inherited 2 unresolved child-source references, 1 missing expected locator, and 558 IDs without detailed bibliography remain unchanged.
- Source limits: full texts were inspected for seven articles. Gillingham's Psalm 105 full text was inaccessible; the entry is narrowly based on the publisher abstract, marked low-confidence/speculative, and explicitly requires full-text and human review. Schäder's article has conflicting page-range metadata between the journal index and the repository/PDF; the locator follows PDF page numbering, and the discrepancy is documented.
- Narrative Explorer regression: 6 CKL unit tests and 67 targeted projection/regression tests passed. Exact anchors, source locator disclosure, observation/interpretation visibility, confidence/dispute/review fields, duplicate suppression, and absence of authored cross-passage links were checked.
- Deep heuristic report: 63 error-severity findings and 1,018 warnings, compared with 63/1,010 after A3. The eight additional warnings are `unknown-passage-chronology` notices for the new records, whose composition/settings remain unresolved. No new heuristic errors were introduced. These are review signals, not strict validation failures or scholarly adjudications.
- Protected state: A4 changes only the Psalms CKL object, ED-2 tests, and ED-2 documentation. NE-9C/NE-10 records, held/verified decisions, runtime relationship registries, and historical checkpoints were not changed or regenerated.

## Wave A, batch A5 — Psalms 39, 48, 62, and 71

- Strict CKL validation: 687 valid objects, 0 errors, and the same 14 inherited `incomplete_section_status` warnings.
- Manifest and source integrity: generated manifest semantically matches the checked manifest. Four new source identities and four new evidence items resolve; all locators are present. The four items each cite the existing Masoretic Psalms text source as the textual base. The inherited 2 unresolved child-source references, 1 expected missing locator, and 558 source IDs without rich bibliography are unchanged.
- ED-1A census: pass, 1,189/1,189 chapters, 0 unmapped identities. Coverage is 1,026 passage-specific, 68 contextual-only, 3 entity-only, 91 no-eligible, and 1 incomplete/unknown. Psalms is 94 passage-specific and 33 no-eligible; all four targets became passage-specific.
- CKL totals: 687 objects, 2,329 claims, 1,342 typed evidence items, 5,281 source-record occurrences, and 2,832 source identities. A5 added 4 typed evidence items, 4 source identities, and no claims or CKL objects.
- Source verification: full texts were consulted for all four additions: the University of Pretoria repository article for Psalm 39, the SciELO PDF for Psalm 48, Botha's full *Acta Theologica* article for Psalm 62, and Liess's open-access Heidelberg University Publishing chapter for Psalm 71. Illness/cultic setting, Psalm 48's redaction layers and historical occasion, Psalm 62's proposed post-exilic social setting, and Psalm 71's speaker biography remain unestablished or disputed and are explicitly qualified.
- Narrative Explorer regression: 7 CKL unit tests and 68 targeted projection/regression tests passed. The full ED-1A audit also completed its 19 deterministic passage samples and 16 live service samples. Exact verse anchors, reader section assignment, source/locator disclosure, observation and interpretation, confidence/dispute/review state, no duplicate display, and no authored cross-passage links were checked.
- Deep heuristic review: 63 error-severity findings and 1,022 warnings, compared with 63/1,018 after A4. The four new warnings are `unknown-passage-chronology`; no new heuristic errors were introduced. These findings are separate from strict CKL errors and are not scholarly-quality adjudications.
- Protected state: A5 changed only the Psalms CKL object, ED-2 tests, and ED-2 documentation. No NE-9C/NE-10 decision, hold, relationship identity, API contract, or historical checkpoint was edited or regenerated.
