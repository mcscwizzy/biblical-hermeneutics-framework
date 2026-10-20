# NE-9A — CKL connection coverage and quality audit

## Executive summary

Audit baseline: `origin/master` at `fc8234947fc01b3adc95437ccde709cce1cf1232`, including merged NE-8B PR #38. The source checkout remained on `master`; this report and its exporter are on the isolated local branch `audit/ckl-connection-coverage-ne9a`.

This is a read-only inventory. No CKL or evidence record was edited, regenerated, or migrated. The requested relationship inventory is in [03-relationship-inventory.csv](03-relationship-inventory.csv); the repeatable exporter is `scripts/audit_ckl_connection_coverage.py`.

## Verified baseline

| Measure | Verified result |
|---|---:|
| CKL objects loaded / manifest count | 687 / 687 |
| CKL semantic inventory fingerprint | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` |
| Authored top-level `related_objects` relationships | 4,061 |
| Distinct raw top-level relationship labels | 1,446 |
| Top-level relationships assigned a typed Narrative Explorer connection | 113 |
| Top-level relationships still projected as `uncategorized` | 3,948 |
| Exact reciprocal pairs / edges (same label, reverse endpoints) | 98 / 196 |
| One-way top-level relationships | 3,865 |
| Top-level relationships without an authored edge rationale | 878 |
| Authored evidence-to-subject/evidence relationships | 1,195 |
| Evidence relationships one-way / reciprocal edges | 1,161 / 34 |
| Passage-applicability anchor rows in the full inventory | 13,081 |
| Source records attached to CKL objects | 5,232 |
| Distinct owner/source-ID pairs referenced | 5,234 (2 unresolved) |
| Distinct raw source-ID strings referenced | 2,784 |
| Inventory CSV rows / bytes | 53,097 / 53,638,723 |

The 113 typed top-level relationships comprise 104 thematic relationships, one narrative parallel, one direct quotation, five later canonical receptions, and two interpretive associations. The remaining 3,948 are not a count of missing biblical connections: most retain descriptive labels, and many lack edge-level rationale or a passage-specific scope. A specific label should not be upgraded to a literary or theological relationship based on its wording alone.

## NE-A1 comparison

NE-A1’s historical audit reported all 4,061 top-level relationships as `uncategorized`. That count is a correct historical baseline for its projection version, not the current master result. NE-A2 subsequently added exact-label mapping: the same 4,061 authored edges now yield 113 typed and 3,948 uncategorized relationships. Its 49 mapped book-level relationships remain intentionally excluded from passage-level projection; this audit confirms the current mapped totals and does not reinterpret broad book scope as passage evidence.

## Integrity and provenance

- The CKL loader read all 687 objects, matching the manifest. The CKL validator reported 687 valid objects, zero errors, and 14 warning records for incomplete section-status metadata.
- The protected `.bhf/ckl.sqlite` and `.bhf-data/study.sqlite` files each returned `ok` from `PRAGMA quick_check` using read-only connections. The CKL cache’s stored inventory fingerprint matches the JSON CKL fingerprint. No SQLite file was created or changed.
- The CKL source-object tree SHA-256 is `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`; `manifest.json` SHA-256 is `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4`.
- The protected SQLite file hashes match the NE-A2 integrity baseline: `.bhf/ckl.sqlite` `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`; `.bhf-data/study.sqlite` `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.
- Two interpretive-note source references in `roman-ephesus-civic-cultic-and-household-life` have no corresponding source record on that CKL object: `glancy-slavery` and `harland-associations`. The inventory retains both as unresolved instead of inventing bibliographic details.
- No unknown target was found among the formal object edges. Unmatched free-text `related_people`, `key_places`, `maps`, and similar field values are recorded as descriptive values, not treated as broken IDs. The 144 human-readable `canonical_story` values are likewise sequence descriptions, not unresolved CKL object IDs.

The CSV contains 53,097 rows across 15 relationship groups. It separately exports object relationships, evidence relationships, claim/evidence/source provenance, passage applicability anchors, typed evidence targets, historical-period links, canonical-sequence metadata, and field-level entity/domain values. A Scripture anchor is never counted as a cross-passage relationship.

## Main findings

1. **Most classification volume is a projection-policy question.** The current projector recognizes a small, exact label set. High-volume labels such as `related-concept`, `narrative-context`, `geographic-context`, `historical-background`, `contextual`, and `institutional-context` are descriptive and do not by themselves specify quotation, allusion, reception, or parallel.
2. **A smaller, concrete presentation gap remains.** The evidence graph contains evidence-to-evidence links, but the current supported navigation target accepts canonical object IDs and does not open a sibling evidence record such as the reciprocal Enuma comparison pair. This is a reader navigation issue, not a missing CKL relationship.
3. **Some supported trails are already navigable.** Examples include the Genesis 1 creation and comparison network, Genesis 2 garden/rivers evidence, Genesis 6 flood/reception/comparison records, Psalm 82 and Deuteronomy 32 material under their shared assembly object, and the Creation/New Creation theme route connecting John 1 and Revelation 21.
4. **Several plausible passage-level bridges are absent as authored edges despite scoped CKL material.** They are candidates for separate editorial and scholarly approval, not approved additions. Examples include John 1 / Genesis 1, Genesis 3 serpent reception / Revelation 12, and Revelation 21–22 / Genesis 2–3 or Ezekiel 40–48.
5. **Some attractive links remain unsupported.** Co-anchoring, shared themes, shared parent objects, and broad free-text cross-reference fields do not establish direct dependence. In particular, the Ugaritic comparison is anchored to Psalm 82 and Psalm 89, not Deuteronomy 32.

## Recommendation

The next transaction should first address the narrow Narrative Explorer navigation gap for authored evidence-to-evidence destinations, then route a small set of source-backed candidate edges to CKL scholarly review. It should not begin with broad source expansion or a blanket remapping of 3,948 labels. The final report distinguishes existing authored and navigable relationships from supported-but-unlinked candidates and genuine research gaps in [07-next-transaction-recommendation.md](07-next-transaction-recommendation.md).
