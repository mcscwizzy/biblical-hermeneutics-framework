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


## Wave A, batch A6 — Psalms 12, 28, 35, 38, and 45

- **Strict CKL validation:** 687 valid objects, 0 errors, and 14 inherited `incomplete_section_status` warnings. No validation rule was changed.
- **Manifest and references:** generated manifest semantically matches the checked manifest. All five exact Scripture anchors and all source-support references resolve.
- **ED-1A chapter census:** pass, 1,189/1,189 chapters and 0 unmapped identities. Coverage is 1,031 passage-specific, 68 contextual-only, 3 entity-only, 86 no-eligible, and 1 incomplete/unknown. Psalms is 99 passage-specific and 28 no-eligible.
- **CKL totals:** 687 objects, 2,329 claims, 1,347 typed evidence items, 5,286 source-record occurrences, and 2,837 source identities. A6 adds five evidence items and five source identities; no claims or CKL objects were added. Each evidence item reuses the existing Masoretic Psalms text source and has one new scholarly source.
- **Source verification:** all five additions use full open-access articles and exact section or page locators. The Persian-period and literary-context proposal for Psalm 12, the Psalm 28 ending classification, Psalm 35's genre/setting, Psalm 38's body-image interpretation, and Psalm 45's performance setting remain qualified as documented in the packet.
- **Source integrity limits:** the same two unresolved child source references, one expected missing locator (`patristic-minor-prophets`), and 558 source IDs without rich bibliography remain. The inventory also reports 81 IDs with metadata variation and 148 with locator variation; these are inherited baseline-wide findings, not A6 sources.
- **Reader projection:** 8 CKL unit tests and 69 targeted Narrative Explorer tests passed. They check exact chapter/verse eligibility, one-item display, section assignment, source and locator disclosure, observation/interpretation, confidence/dispute/review metadata, and absence of authored cross-passage or entity links.
- **Package checks:** 24 manifest/schema package tests passed; the generated manifest matches the committed manifest.
- **ED-1A reader audit:** 19 deterministic passage samples and 16 live service samples passed.
- **Heuristic quality review:** the deep report counts 63 error-severity findings and 1,027 warnings, compared with 63/1,022 after A5. Its five additional findings are `unknown-passage-chronology` warnings for these five records. No heuristic error was introduced. These warnings are separate from strict validation and do not assign a scholarly-quality score.
- **Protected decisions:** the batch changed only the Psalms CKL object, ED-2 regression tests, and ED-2 documentation. No NE-9C/NE-10 curation or bridge file, held/verified decision, historical checkpoint, API contract, or relationship registry was changed. The audit reports 433 accepted curation records, 44 verified NE-10 bridges, and 7 held candidates.
- **Review state:** all new work remains draft/in-review, requires human scholarly review, and has no named human reviewer.
- **Evidence commit:** `ec244726f95604ff93eb6034f1f480270831976c` (`research: add ED-2 Psalms batch A6`).


## Wave A, batch A7 — Psalms 52, 59, 61, 63, 64, and 65

- Strict CKL validation: 687 valid objects, 0 errors, and the same 14 inherited `incomplete_section_status` warnings.
- Manifest/reference checks: regenerated manifest is semantically equal to the checked manifest; all six exact BHF Scripture anchors and new source-support identities resolve.
- ED-1A census: all 1,189 chapter rows pass with 0 unmapped identities. Totals are 1,037 passage-specific, 68 contextual-only, 3 entity-only, 80 no-eligible, and 1 incomplete/unknown; Psalms is 105 specific, 22 contextual, 1 entity-only, and 22 no-eligible.
- CKL totals: 687 objects, 2,329 claims, 1,353 typed evidence items. A7 added six evidence items and five scholarly source identities, with no claims or objects. Audit source inventory reports 5,291 source-record occurrences and 2,842 source identities; the separate identity audit reports 2,843 IDs because its scope differs. Two unresolved child-source references, one expected missing locator (`patristic-minor-prophets`), and 558 source IDs without rich bibliography are inherited findings.
- Source verification: Botha (Psalm 52), Janowski (Psalm 59), Eder (Psalm 64), and Botha (Psalms 65–68) were consulted in full at the locators recorded in the packet. Only LeMon’s publisher abstract was accessible for Psalms 61 and 63; these two entries are narrowly framed and marked low-confidence with the access limit stated.
- Narrative Explorer: 9 ED-2 CKL tests, 70 targeted projection/regression tests, and 24 manifest/schema package tests passed. The protected NE-9C/NE-10 curation suite passed 464 tests. Tests cover exact eligibility, source disclosure, primary observation and interpretation, uncertainty/review fields, single display, and no new relationship routes. The ED-1A audit passed 19 deterministic and 16 live service samples.
- Heuristic quality report: 63 error-severity findings and 1,033 warnings versus 63/1,027 after A6. The six new warnings are `unknown-passage-chronology` notices; no new heuristic errors were added. These are heuristic signals, not strict validation failures or scholarly adjudication.
- Protected state: no NE-9C/NE-10 inputs, held/verified decisions, historical checkpoints, API contracts, or relationship registries were changed or regenerated. All A7 records remain draft/in-review and require human scholarly review.
- Evidence commit: `55265d1d` (`research: add ED-2 Psalms batch A7`).


## Wave A, batch A8 — Psalms 70, 86, 87, 98, 101, and 108

- Strict CKL validation: 687 valid objects, 0 errors, and the same 14 inherited `incomplete_section_status` warnings.
- Manifest: generated with `tools/ckl_manifest.py`; semantic comparison with the checked manifest passed.
- ED-1A census: all 1,189 chapter identities mapped, no unmapped identities; 1,043 passage-specific, 68 contextual-only, 3 entity-only, 74 no-eligible, 1 incomplete/unknown. Psalms rose 105→111 passage-specific chapters and fell 22→16 no-eligible chapters. The 16 remaining zero-eligible Psalms are still queued for qualitative research.
- CKL/source integrity: six typed evidence records and six new scholarly source IDs; all exact anchors, source identities, locators, and support links resolve. Totals: 687 objects, 2,329 claims, 1,359 typed evidence items, 5,297 source occurrences, 2,848 source identities.
- Narrative Explorer: 10 ED-2 CKL tests passed; 71 full projection/regression tests passed; 24 manifest/schema package tests passed. Exact anchors, reader projection, bibliography/locator disclosure, confidence, dispute, human-review status, and absence of new relationship routes were verified. The protected curation suite passed 464 tests. The ED-1A audit passed 19 deterministic and 16 live service samples.
- Heuristic report: 63 error-severity findings and 1,039 warnings versus 1,033 after A7. The six additional chronology warnings are heuristic-only; no new heuristic errors.
- Protected decisions: no NE-9C/NE-10 inputs, verified/held decisions, relationship registries, or historical checkpoints were changed or regenerated.
- Human review: all six additions remain draft/in-review and require scholarly review.
- Evidence commit: `ec33a4f2974e306734a6ebccbd8ecc3889104694`.


## Wave A, batch A9 — Psalms 57, 58, 69, 76, 94, and 99

- Strict CKL validation: 687 valid objects, 0 errors, and 14 inherited `incomplete_section_status` warnings.
- Manifest/reference checks: regenerated manifest semantically matches the checked manifest. All four exact BHF anchors and supporting source identities resolve. A first census surfaced the source’s superscription-inclusive numbering for Psalm 69; the record was corrected from an out-of-range 69:35–37 to BHF 69:34–36, with the mapping documented in the record and packet, then the full audit was rerun.
- ED-1A census after correction: 1,189/1,189 chapters, zero unmapped identities; 1,047 passage-specific, 68 contextual-only, 3 entity-only, 70 no-eligible, and 1 incomplete/unknown. Psalms is 115 specific, 22 contextual, 1 entity-only, and 12 no-eligible. The remaining incomplete chapter is the inherited Obadiah anchor; no A9 anchor remains out of bounds. The audit passed 19 deterministic and 16 live service samples.
- CKL and source inventory: 687 objects, 2,329 claims, 1,363 typed evidence items, 5,300 source-record occurrences, and 2,852 source IDs. Three new scholarly source identities and one reused scholarly source were added/used; two unresolved child-source references remain inherited.
- Narrative Explorer regression: 11 ED-2 CKL tests, 72 projection/regression tests, and 81 manifest/schema package tests passed. The protected NE-9C/NE-10 suites passed 464 tests. Exact scope, source locator disclosure, primary observation, attributed interpretation, uncertainty and human-review fields, and the absence of new authored cross-passage routes were verified.
- Heuristic quality report: 63 error-severity findings and 1,043 warnings versus 1,039 after A8. The four additional findings are `unknown-passage-chronology` warnings; no new heuristic errors. These remain heuristic review signals, separate from strict schema validation.
- Protected decisions: no NE-9C/NE-10 records, held or verified decisions, historical checkpoints, API contracts, or relationship registries changed. All four records remain draft/in-review and require human scholarly review; no human reviewer is named.
- Evidence commit: `258cb7729e8f517a` (`research: add ED-2 Psalms batch A9`).


## Wave A, batch A10 — Psalms 53, 102, 109, and 135

- Strict CKL validation: 687 valid objects, 0 errors, and 14 inherited `incomplete_section_status` warnings.
- Manifest and references: regenerated manifest semantically matches the checked manifest; all four exact Scripture anchors and source-support links resolve.
- ED-1A census: pass, 1,189/1,189 chapters, 0 unmapped identities and 0 invalid anchors. Coverage is 1,051 passage-specific, 68 contextual-only, 3 entity-only, 66 no-eligible, and 1 incomplete/unknown; Psalms is 119 specific, 22 contextual, 1 entity-only, and 8 no-eligible. The audit passed 19 deterministic and 16 live service samples.
- CKL/source inventory: 687 objects, 2,329 claims, 1,367 typed evidence items. Three new scholarly identities and one existing scholarly identity were used; source summary reports 5,303 source occurrences and 2,854 identities, while the separate identity audit counts 2,855 unique IDs. Two unresolved child-source references remain inherited.
- Narrative Explorer: 12 ED-2 CKL tests, 73 projection/regression tests, and 81 manifest/schema package tests passed. Protected NE-9C/NE-10 curation suites passed 464 tests. Exact chapter/verse eligibility, disclosure, observation/interpretation, uncertainty/review metadata, and no new authored routes were checked.
- Source access: full open-access articles were inspected for Psalms 53, 102, and 135 at the recorded locators. For Psalm 109, only the publisher abstract and bibliographic record for Egwim were accessible; its entry reports only the abstract-level proposal, uses low confidence, and requires full-text and human review.
- Heuristic quality report: 63 error-severity findings and 1,047 warnings, four more chronology warnings than A9, and no new heuristic errors. Strict errors and heuristic warnings remain separate measures.
- Protected decisions: no NE-9C/NE-10 curation or bridge file, held or verified decision, historical checkpoint, API contract, or relationship registry changed. No human reviewer is named; all four records remain draft/in-review.
- Evidence commit: `5f0996cc` (`research: add ED-2 Psalms batch A10`).
