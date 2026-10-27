# NE-11A coverage baseline

## Repository and data baseline

- Refreshed origin/master at **e2f696db98be2e1662916a14781a6203073a4605**; it matched the plan's expected SHA. The audit branch, `audit/ne11a-discovery-coverage`, is based on that commit.
- The worktree was clean before the audit. The only intended branch changes are these audit documents and the compact chapter inventory linked below.
- The CKL contains **687 objects**. Its inventory fingerprint is **90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6**. The canonical inventory has 66 books and 1,189 chapters.
- The coverage audit revalidated the CKL manifest at 687 objects, the object identities and fingerprint, the passage API samples, and the study database integrity. The database remained read-only and unchanged during the census.

The reproducible census command was `python3 scripts/audit_narrative_explorer_coverage.py --output-dir /tmp/ne11a-coverage`. It completed with validation status **pass**: 1,189 chapter rows, 19 sample checks, 16 API builds, and no missing or stale CKL identity. Full generated output was kept outside Git. The compact result is [chapter-coverage.csv](chapter-coverage.csv); it preserves one row per application-canonical chapter without copying object inventories or source lists.

## Curation and bridge baselines

- NE-9C validation passes: **3,925 reviewed relationships** against a 4,061-edge relationship inventory; 408 curated, 1,895 held, and 1,622 excluded. The 408 current NE-9C decisions plus 23 retained object-relationship decisions and 2 evidence decisions give 433 active curated registry identities. These are review counts and identities, not route counts.
- The NE-10 bridge registry contains **43 verified bridge records**, 44 support-record references, 31 distinct CKL record identities across 19 objects. Every record resolved to its named CKL record, attached sources, and both passage scopes. The registry has 15 direct quotations, 10 later-canonical-reception routes, 7 thematic relationships, 6 interpretive associations, 4 shared literary motifs, and 1 proposed intertextual echo.
- NE-10 has **7 separate held candidates**. Their status remains held; the audit did not change or promote any candidate. See [the existing NE-10 audit](../ne10-evidence-discovery-audit.md) and [results](../ne10-results.md) for the established record-level rationale.

## Phase B, C, and D context

- **Phase B Locations:** the Study Companion combines explicit map-place results with source-backed CKL places and pages the list (five items per page). It preserves place identity and does not infer coordinates from literary geography. This audit reports returned location totals only as context; a zero is not a missing connection verdict.
- The census found 7,741 explicit map place links, all valid and linked to 812 chapters. The archaeology service inventory had 94 link rows; 71 items had passage links and 4 had no valid passage link. These are distinct service inventories, not relationship totals or a claim that the other rows failed.
- **Phase C discovery presentation:** local discovery presentation renders at most three “Did you know?” cards and one “Walk the land” card. It suppresses a walk card when its map destination is already visible. Cards retain confidence, interpretation level, and evidence details.
- **Phase D acceptance corrections:** current HEAD includes the chapter-option preservation correction in `b16db4eb` and the retired Commentary packaging-check alignment in `2e8b0d5e`, merged by PR #46. The selected Phase D acceptance and packaging checks passed in this audit. The separate NE-10 bridge acceptance retained 32 classifications and corrected 11; all 43 bridge identities remained present and verified. Retired BHF Commentary routes still return HTTP 410. Tyndale Open Study Notes remains an active service. NE-11A changes none of these behaviors or records.

## Corpus-level coverage

| Measure | Count | Definition |
| --- | ---: | --- |
| Canonical chapter inventory | 1,189 | Chapters exposed by the application's current Bible inventory (66 books). |
| Passage-specific evidence coverage | 985 | Chapters classified by the census as having passage-specific eligible CKL material. |
| Contextual coverage | 68 | Eligible CKL context exists, but the chapter lacks the census's passage-specific evidence classification. |
| Entity-only coverage | 3 | Eligible entity coverage without passage-specific evidence. |
| No eligible CKL material | 132 | The complete CKL lookup returned no eligible census item for the chapter. This is a data-availability measure, not proof that research is absent. |
| Incomplete or unknown | 1 | Obadiah 1 has an invalid/out-of-bounds Scripture anchor in a note; its route/evidence coverage cannot be safely inferred from that anchor. |
| Chapters with source-grounded claim/evidence placements | 986 | Distinct chapter placements of source-backed claims or evidence; one chapter has a partial/invalid anchor state. |
| Source-backed claim/evidence placements | 6,098 | Chapter placements, not distinct claims and not relationship edges. |
| Eligible CKL item placements | 12,662 | All eligible item-to-chapter placements in the census. |
| Authored CKL object relationships | 4,061 | Raw related-object edges before NE-9C presentation eligibility; includes edges not usable as passage routes. |
| Authored distinct passage destinations | 382 | Existing NE-9C curated authored pathway destinations in the NE-10 corpus audit; destination count, not edge count. |
| Verified NE-10 bridge records | 43 | Unique registry records. A bridge can be returned from either endpoint, so endpoint projections must not be added as unique records. |

The most frequent section placements are Themes and Biblical Connections (6,155), Biblical Narrative (5,003), Archaeology and Ancient History (3,051), People and Events Relationships (1,720), Biblical Geography (607), and Cosmic Geography (17). These are overlapping CKL item placements, not exclusive chapter categories. A further 1,023 item placements across 394 chapters remain unclassified for section display; this is a presentation-classification issue, not a reason to invent connections.

Among chapters with no eligible material, the largest book totals are Psalms (74), 2 Chronicles (14), Proverbs (12), Ezekiel (9), 1 Kings (6), 2 Kings (6), Numbers (4), 1 Chronicles (3), and Luke (3), followed by Ecclesiastes (1). Those are genuine low CKL-eligibility areas in this inventory. They still require passage- and domain-specific research before any coverage work is proposed.

## Retrieval and integrity notes

The coverage audit performed full-inventory, read-only CKL retrieval and checked representative API projections. It found no failed CKL query in the 16 sampled passage builds. The census also found one malformed anchor: interpretive note `obadiah#interpretive_note:sha256-21d8661d398d03bd016453f63d2be7e1338764bf635c38c76ea40ec56f860819` cites “Obadiah 7,” which the canonical parser marks out of bounds. Do not silently rewrite it: source-owner review is needed to establish the intended scope.

There are two unresolved bibliography IDs on an unanchored interpretive note, `roman-ephesus-civic-cultic-and-household-life#interpretive_note:sha256-a69db357b2e4ae0efd94846f597f048835c3ab81143ddc5371ad3c14b0702fff`: `harland-associations` and `glancy-slavery`. This is a source-lookup limitation on that note, not evidence of a missing passage route. The census checked explicit map place links and archaeology service links; dynamic service coverage outside the sampled APIs is not inferred from empty responses.

## Verification completed

- NE-9C curation validation: passed, with the baseline totals above.
- CKL coverage audit: passed; 1,189 chapter rows and all identity checks passed.
- Focused backend regression suite covering coverage, projection, passage routes, APIs, curation, Locations, presentation, and integrity boundaries: **682 passed, 10 skipped, 11 subtests passed**.
- Additional Phase D/packaging/UI checks: **12 passed**.
- Frontend suite: **13 passed**.

No tests or source data were added or modified by this audit. The results above count retrieved CKL data and existing routes; they do not measure scholarly importance or establish that a zero-route chapter has no relationship worth studying.
