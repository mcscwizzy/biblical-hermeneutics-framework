# Commentary v1.2 post-applicability coverage census

This is the deterministic census `commentary-v1.2-post-applicability-coverage-census-v1`. It is not a commentary pilot. It made zero model calls, generated no commentary, invoked no renderer, and changed no production behavior.

The exact frozen population was recovered from:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-922472547555015a3ced/manifest.json`

It contains 75 unique chapters in six frozen batches (`13, 13, 13, 12, 12, 12`). Population manifest identity is `eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394`; ordered-reference hash is `876d0fbca0c3986a0c40c9e87b1028b826d2d510dd74c8c2875462482f4538ea`.

The immutable output is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-post-applicability-coverage-census-v1-5cd6a3e32d5b4dcb03e5ecf0/`

It contains the manifest, frozen population, all 75 chapter records, contract hashes, coverage records, before/after comparison, state classifications, legacy-dependency metrics, CKL family impact, the two curation queues, editorial-review queue, Psalm exposure, summary statistics, checksums, and final report.

## What disappeared

Applicability enforcement did not remove raw retrieval. The 75 chapters still retrieve 1,978 raw evidence items, but only 940 are commentary-eligible; 1,038 are inherited legacy items and are background-only. Thus the apparent evidence-item richness fell from an average of 26.37 raw items per chapter to 12.53 legal items, with medians of 17 and 6.

The more important effect is on synthesis. Across the historical packets, total synthesis units changed from 1,470 to 585, CURRENT_CHAPTER units from 1,320 to 435, projected ideas from 202 to 170, and provenance paths from 695 to 570. These are diagnostic before/after comparisons against frozen pre-applicability packet data; they are not claims that every reduction is a defect.

Raw verse ancestry covers an average of 84.62% of each chapter. Legal commentary ancestry covers 72.36%, a 12.26 percentage-point difference. The median legal coverage is 100%. Thirteen chapters have zero legal CURRENT_CHAPTER synthesis, 17 have partial legal verse coverage, and 45 have either focused or rich legal evidence by the diagnostic criteria.

The loss is mostly false specificity where it is largest: inherited parent fields supplied passage-shaped anchors without authored claim-level child anchoring. The 2 Kings 4, Psalms 103, and Psalms 19 controls demonstrate this directly. The census does not claim that every inherited record is useless; it distinguishes possible migration candidates from generic material that should stay background-only.

## Population results

| Measure | Result |
| --- | ---: |
| Chapters | 75 |
| AVAILABLE / THIN / DATA_GAP availability | 66 / 9 / 0 |
| Zero legal synthesis chapters | 13 |
| CURRENT_CHAPTER synthesis units | 435 |
| Chapters with 1 legal unit | 6 |
| Chapters with 2–5 legal units | 31 |
| Chapters with 6–10 legal units | 13 |
| Chapters with more than 10 legal units | 12 |
| Mean / median raw evidence | 26.37 / 17 |
| Mean / median legal evidence | 12.53 / 6 |
| Mean / median raw verse coverage | 84.62% / 100% |
| Mean / median legal verse coverage | 72.36% / 100% |
| Chapters with a LEGACY_INFLATED diagnostic flag | 21 |
| Chapters whose primary state is LEGACY_INFLATED | 1 |
| Chapters with an EVIDENCE_PARTIAL diagnostic flag | 17 |
| Chapters whose primary state is EVIDENCE_PARTIAL | 19 |
| Chapters with an EVIDENCE_FOCUSED flag | 24 |
| Chapters with an EVIDENCE_RICH flag | 14 |

The primary states are: `MIXED` 23, `EVIDENCE_PARTIAL` 19, `EVIDENCE_FOCUSED` 15, `EVIDENCE_RICH` 10, `COMMENTARY_DATA_GAP` 7, and `LEGACY_INFLATED` 1. A primary state is deliberately conservative; diagnostic flags can coexist inside `MIXED`.

## Literary-category gaps

These are descriptive averages within the frozen sample, not equal-density quotas.

| Category | Chapters | Raw coverage | Legal coverage | Gap | Zero legal synthesis |
| --- | ---: | ---: | ---: | ---: | ---: |
| Poetry/Wisdom | 8 | 83.82% | 37.25% | 46.57 pp | 4 |
| Historical Narrative | 10 | 77.06% | 37.65% | 39.41 pp | 3 |
| Torah | 8 | 87.50% | 75.00% | 12.50 pp | 2 |
| Major Prophets | 8 | 56.92% | 51.05% | 5.87 pp | 2 |
| Gospels | 8 | 87.48% | 86.73% | 0.75 pp | 0 |
| Acts | 4 | 94.64% | 94.64% | 0 pp | 0 |
| General Epistles | 7 | 95.92% | 95.92% | 0 pp | 0 |
| Minor Prophets | 8 | 100.00% | 100.00% | 0 pp | 0 |
| Pauline Epistles | 8 | 100.00% | 100.00% | 0 pp | 0 |
| Apocalyptic literature | 6 | 66.67% | 66.67% | 0 pp | 2 |

Poetry/Wisdom and Historical Narrative are the largest actual coverage gaps. Apocalyptic literature has two zero-synthesis chapters, but in this sample that is primarily source thinness rather than additional applicability loss.

## CKL impact and curation queues

Within this population, 1,038 inherited legacy evidence instances intersect the deterministic path. The top ten family rows by affected-chapter spread, lost legal verse coverage, and former synthesis impact are:

| Family | Chapters | Inherited | Former units | Current legal units | Legal verse coverage lost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Psalms:faq:ancient_near_east_context | 6 | 9 | 9 | 0 | 31 |
| Psalms:faq:historical_context | 6 | 9 | 9 | 0 | 31 |
| Psalms:theology:ancient_near_east_context | 5 | 12 | 12 | 0 | 31 |
| Psalms:theology:historical_context | 5 | 12 | 12 | 0 | 31 |
| Psalms:theme:ancient_near_east_context | 5 | 8 | 11 | 0 | 13 |
| Psalms:theme:historical_context | 5 | 8 | 8 | 0 | 13 |
| Psalms:event:ancient_near_east_context | 4 | 5 | 9 | 0 | 31 |
| Psalms:event:historical_context | 4 | 5 | 5 | 0 | 31 |
| Psalms:event:hebraic_worldview | 3 | 4 | 8 | 0 | 31 |
| Psalms:theme:hebraic_worldview | 3 | 3 | 6 | 0 | 12 |

This is why sorting all 6,514 repository-wide inherited-anchor instances by frequency would be misleading: the population-impact table identifies where legacy material actually changed commentary coverage. The known person/place/event families in Matthew, Genesis/Joshua, Exodus, and Luke do not lead this bounded population’s impact table; their actual intersection is smaller than the Psalm legacy families above.

The census produced 66 `MIGRATION_CANDIDATES`, 812 `BACKGROUND_ONLY_CANDIDATES`, and 66 `REQUIRES_EDITORIAL_REVIEW` entries. A migration candidate is only a deterministic signal: legacy text contains an explicit target chapter reference and source provenance. It does not supply an anchor and must be authored and checked by an editor. Generic parent biography, Bible-related wording, retrieval score, frequency, or historical synthesis alone never creates a migration candidate.

The background-only queue is the larger and safer default. It contains generic parent fields without a deterministic claim-level target signal; those records should remain retrievable context and should not be promoted into passage commentary merely because the parent is associated with the chapter.

## Enrichment priorities

The descriptive priority queue is ordered by legal coverage loss, then low legal synthesis, inherited dependency, and stable reference order:

1. Psalms 2 — 0% legal coverage; 26 inherited items.
2. Psalms 122 — 0%; 17 inherited.
3. Genesis 5 — 0%; 8 inherited.
4. Judges 8 — 0%; 3 inherited.
5. Joshua 10 — 9.30%; 2 inherited.
6. Judges 3 — 0%; 3 inherited.
7. Psalms 19 — 0%; 30 inherited.
8. Psalms 8 — 33.33%; 15 inherited.
9. 2 Kings 15 — 42.11%; 6 inherited.
10. Isaiah 63 — 0%; 26 inherited.
11. Psalms 103 — 0%; 6 inherited.
12. Esther 1 — 72.73%; 4 inherited.
13. 2 Kings 18 — 78.38%; 20 inherited.
14. 2 Kings 4 — 0%; 18 inherited.
15. Jeremiah 49 — 25.64%; 28 inherited.
16. John 12 — 54.00%; 6 inherited.
17. Isaiah 3 — 0%; no inherited evidence.
18. Numbers 31 — 0%; no inherited evidence.
19. Revelation 15 — 0%; no inherited evidence.
20. Revelation 8 — 0%; no inherited evidence.

The first four are coverage gaps, not automatic migration instructions. Psalms 19 is a possible editorial-review case only if its underlying Torah material can support an authored Psalms 19:7–11 child claim; this census does not make that anchor.

The smallest next curation batch should be five editorially reviewed candidates from the head of the migration queue, beginning with the Daniel 7/Qumran candidate and the first four Romans 16 person-field candidates. This is a review batch, not an automatic CKL edit and not a production quota. After editors either author child anchors or reject the candidates as generic, rerun the census before expanding the batch.

## Controls

| Chapter | Raw / legal evidence | Inherited | Availability | Legal synthesis | Raw → legal coverage |
| --- | ---: | ---: | --- | ---: | ---: |
| 2 Kings 4 | 18 / 0 | 18 | THIN | 0 | 15.91% → 0% |
| Psalms 103 | 6 / 0 | 6 | THIN | 0 | 27.27% → 0% |
| Psalms 19 | 30 / 0 | 30 | THIN | 0 | 78.57% → 0% |
| Numbers 2 | 2 / 2 | 0 | THIN | 2 | 100% → 100% |
| Numbers 1 | 5 / 5 | 0 | AVAILABLE | 5 | 100% → 100% |

2 Kings 4 is overwhelmingly legacy-inflated and has no legal passage evidence; generic Elisha biography is not promoted. Psalms 103 is thin and redundant rather than six distinct useful claims. Psalms 19’s former 30-path appearance was inflated; any Torah-related recovery requires authored verse-level editorial review. Numbers 2 remains the focused positive control, and Numbers 1 remains the strong positive control.

## Before/after interpretation

The frozen historical packets report 72 AVAILABLE and 3 THIN chapters. The rebuilt path reports 66 AVAILABLE and 9 THIN. Six chapters changed `AVAILABLE → THIN`; three changed from nonzero to zero synthesis. No priority-path-to-none or fallback-path-to-zero transition occurred in this comparison. These changes are expected consequences of fail-closed applicability and should be interpreted as removal of unsupported specificity, not automatically as regressions.

## Psalm superscription exposure

The current ASV identity is `1a37e6f9a6d4b8331f839a3d04b7cfd332802ead02f5f032957697b31baa6e3c`. Psalm 19:14 contamination is recorded as repaired. The census found 115 remaining systematic heading-boundary patterns, deferred pending a Psalms superscription representation policy. Five intersect the frozen population: Psalms 2:12 → Psalm 3, Psalms 8:9 → Psalm 9, Psalms 22:31 → Psalm 23, Psalms 122:9 → Psalm 123, and Psalms 137:9 → Psalm 138. ASV data was not modified.

## Pilot recommendation

A model-based 75-chapter Sol pilot is not advisable yet. Thirteen chapters have no legal CURRENT_CHAPTER synthesis, and Poetry/Wisdom and Historical Narrative have large legal coverage gaps. The appropriate next step is the five-candidate editorial review batch above, followed by a fresh deterministic census. No CKL records should be changed until the editors establish claim-level anchors and source/review quality.

The census tool and nine focused deterministic tests cover population identity, coverage, legacy dependency, state classification, family aggregation, queue ordering, CKL/ASV non-mutation, protected contract fingerprints, and the zero-model/zero-renderer boundary.
