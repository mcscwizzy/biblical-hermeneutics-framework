# ED-2A regression and compatibility results

## CKL validation and chapter coverage

- The strict CKL validator reports **687 valid objects, 0 errors, and 14 warnings**, matching the base warning count.
- The canonical CKL build completed with schema v4 and retrieval index v3: 687 objects, 2,329 claims, 5,247 source records, and 1,309 typed evidence items. The resulting inventory fingerprint is `45bc240f39f258fc9ef46c62d083eef87d8d60a346d40052ed0b1895c8156095`.
- A generated manifest is semantically identical to the committed manifest (687 objects); no manifest edit was needed.
- The final ED-1A/NE-A1 audit validated 1,189 chapter rows, returned `pass`, and found zero unmapped record identities. The matching baseline fingerprint was `7d5c8b636176b75452f82a7276d1b51a69180414e40ab7ea82527a1fd80f940c`.

| Psalms coverage category | ED-1C base | ED-2A after | Change |
| --- | ---: | ---: | ---: |
| No eligible CKL material | 74 | 66 | −8 |
| Contextual coverage | 22 | 22 | 0 |
| Passage-specific evidence | 53 | 61 | +8 |
| Entity-only coverage | 1 | 1 | 0 |

The selected chapters all resolve to their intended Psalm: each of Psalms 6, 15, 30, 37, 47, 67, 96, and 145 gains passage-specific evidence; Psalm 44 remains passage-specific and increases from one to two eligible items. Psalm 72 retains its existing five eligible items. The final anchor scan found no invalid Psalms anchors; its one corpus-wide invalid anchor remains outside Psalms. The audit’s global chapter categories are 124 no-eligible, 68 contextual, 993 passage-specific, 3 entity-only, and 1 incomplete/unknown.

## Source integrity

- The strict CKL/source validation remains at 0 errors and 14 warnings.
- The deep evidence/source report is a heuristic review inventory, not the strict validator: it moves from 62 flagged errors and 977 warnings at the exact base to 63 flagged errors and 986 warnings after ED-2A. New-source support targets are all valid, and the 12 new source IDs each occur once with a source locator and URL.
- The new heuristic flags are review signals, not adjudications. One pairs `psalm-145-nun-verse-witness` with a high-confidence textual-variant signal: the record is confident that the Qumran/Greek witness is attested, while the priority and origin of the forms remain disputed. Nine unknown-passage-chronology signals reflect the packets’ explicit refusal to assign unsupported composition dates.
- The existing two unresolved source references and 102 invalid source-support targets remain unchanged from baseline. No new unresolved source reference or invalid support target was introduced.

## Narrative Explorer and reader tests

- The CKL/projection and Narrative Explorer Python suite passed: **257 tests, 63 subtests**. It covered schema, Scripture anchors, typed evidence targets, manifest, Psalms record, source locks, release behavior, ED-2A projection, and Narrative Explorer API/projection.
- The focused ED-2A CKL and projection checks passed: **5 tests, 21 subtests**. NE-9C, held-candidate, and route regressions passed: **24 tests**.
- Frontend tests passed: **17 tests**.
- The ED-2A browser acceptance passed **4 desktop/mobile cases** for Psalms 145 and 44. The existing ED-1C additional-record browser regression passed **2 layout cases**. The checks confirm one visible card per record, exact scope, source locators, observation/interpretation distinction, uncertainty, review state, and no horizontal overflow.
- Visual regression testing exposed a hidden-preview display conflict with grid styling. The existing stylesheet now explicitly applies `display: none` to preview and record-list elements carrying `[hidden]`; no component, API endpoint, or route was added.

## Protected scholarly state

Compared with the ED-1C base, all protected artifacts and authored relationship identities remain stable:

| Protected input | Base SHA-256 | Result |
| --- | --- | --- |
| NE-9C historical fingerprint checkpoint | `0f8e4f690bd701be2856fc5af1a304f864163f7a8adc896b760d0c95b349c6f9` | unchanged |
| NE-9C decisions ledger | `5aefd69b89c69f0d941babbd5ea4f7e8fbb5c8065907cfeab1025c2f1fd41826` | unchanged |
| NE-10 verified bridge registry | `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b` | unchanged |
| NE-10 held-candidate ledger | `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3` | unchanged |

Existing authored `related_objects` identities and all prior evidence relationship fields are unchanged; the new records add no authored relationships. Psalm 72’s ED-1B evidence is unchanged. No held or excluded NE-9C/NE-10 decision was promoted, including the held Psalm 22 and Psalm 82 candidates. All nine additions remain `draft` / `in_review`, have no human reviewer, and require human review; no scholarly evidence is marked human-approved.

## Diff and delivery

The Psalms JSON diff preserves the prior formatting and contains only the nine evidence items, twelve source records, the matching primary-source support links, and the ED-2A editor identity. Generated databases and audit output remain outside the repository. `git diff --check`, relative report links, CKL validation, source integrity, and the final targeted tests passed. The branch is `feat/ed2a-psalms-research-wave1`; it is for review and comparison only and has not been merged or deployed.
