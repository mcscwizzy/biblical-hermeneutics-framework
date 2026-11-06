# ED-1C baseline and classification analysis

## Baseline

ED-1C starts from the verified `origin/master` commit `5597ecb733d7d4148a76e3f83f0ed58233989fb6`, which contains the ED-1B merge (`#74`). The work branch is `fix/ed1c-evidence-discoverability`.

The ED-1A audit was reproduced against the current CKL and current Narrative Explorer code. It scanned 687 CKL objects, all 1,189 canonical chapters, and 16 targeted service builds; validation passed with no unmapped record identities.

| Current inventory measure | Reproduced count |
| --- | ---: |
| CKL objects | 687 |
| Eligible CKL item-to-chapter placements | 12,665 |
| Section-assigned placements | 11,642 |
| Placements without a Narrative Explorer section | 1,023 |
| Chapters with at least one unassigned placement | 394 |

The historical ED-1A report also counted 1,023 unassigned placements in 394 chapters. ED-1B adds three eligible placements, all assigned to existing sections; thus the total eligible count is three higher, while the unassigned count is unchanged. Section totals overlap and are not a unique-item partition. An unassigned placement is not automatically a defect: it can be a question or broad object, a type without a fitting section, or material already available through a different reader surface.

## Prior work reviewed

ED-1C reviewed the [ED-1A inventory](../ed1a/01-current-inventory.md),
[discoverability findings](../ed1a/04-discoverability-gaps.md), and
[scholarly expansion backlog](../ed1a/05-scholarly-expansion-backlog.md), plus
the [ED-1B compatibility review](../ed1b/compatibility-review.md). ED-1B’s
CKL additions alter the historical NE-9C checkpoint fingerprint; since this
task makes no CKL changes, that checkpoint and the reviewed NE-10 inputs remain
untouched.

## Reader and projection trace

1. CKL book and child records are stored as JSON objects under `framework/canonical_library/objects/`. Child claims, evidence items, and interpretive notes retain their own `scripture_references` and source IDs.
2. `is_canonical_object_passage_eligible` requires an explicit overlapping Scripture anchor and rejects semantically misanchored records. The projector keeps original anchors and separately records the anchors applicable to the selected passage.
3. `project_narrative_explorer` returns eligible items and their `section_ids`. The six section categories are built from those assignments; section assignment does not alter passage eligibility.
4. The reader overview navigates through the six section cards. Each category renders two preview cards and provides a paged “Browse all” path. The separate “Evidence about [passage]” area is limited to at most two source-backed evidence items with authored relationship notes; it does not display unassigned claims.
5. “Browse research sources” opens a hub for libraries and passage tools. It does not open a claim attached to the selected passage or show that claim’s exact anchor and source IDs.

Before ED-1C, the API already returns source-backed unassigned child records, but the passage-first reader has no general route to them. ED-1C keeps the projection contract and six section categories unchanged and adds a collapsed, reader-initiated path for eligible source-backed child records that have no section assignment. It reuses the existing item renderer, original and applicable passage anchors, source details, uncertainty and review metadata, and paged browse control. It excludes parent objects, records without an applicable anchor or source identity, section-assigned records, and records already shown in the connection preview.

## Representative case classification

| Passage / record | Current projection and reader state | ED-1C decision |
| --- | --- | --- |
| 1 Corinthians 11 — `ckl:1-corinthians#claim:1cor-kephale` | Returned for 1 Corinthians 11:3; typed `lexical`; sources `bdag` and `thiselton-1cor`; no section assignment. The reader cannot find it from the selected passage through the category cards or the connection preview. | Keep unclassified because none of the six section labels is a good language-study fit. Expose it in the collapsed additional-records path with the existing uncertainty and source details. |
| Micah 1 — `ckl:micah#claim:micah-empire-reception` | Returned for Micah 1:8–16; typed `reception_history`; sources `kessler-micah`, `cataldo-postcolonial`, and `oxford-minor-prophets`; no section assignment. Its modern postcolonial and trauma-aware reception focus should remain distinct from the chapter’s ancient Assyrian setting. | Keep unclassified and expose through the additional-records path, without merging modern reception into the historical-context section. |
| Mark 2 — `ckl:mark#claim:mark-jewish-debate` | Returned for Mark 2:23–28; typed `historical_cultural`; already assigned to `archaeology_ancient_history`. | No correction needed; it is already section-visible in its ancient Jewish context. |
| Mark 2 — `ckl:mark#claim:mark-disability` | Returned for Mark 2:1–12; typed `pastoral_application`; sources `disabled-body`, `negotiating-disabled-body`, and `oxford-synoptics`; no section assignment. | Keep unclassified because pastoral application is not an ancient-history, geography, narrative, or relationship category. Expose it through the additional-records path with its original caution and attribution. |
| Proverbs 31 — `ckl:proverbs#claim:proverbs-greek-order` | Returned for Proverbs 31:1–31. Its complete CKL anchors are Proverbs 24:23–34, 30:1–33, and 31:1–31. The historical scope concern was mistaken: the record explicitly includes Proverbs 31. It is typed `reception_history` and has no section assignment. | No anchor correction. Keep unclassified and expose through the additional-records path so the Greek textual-order material is discoverable without forcing it into an ill-fitting section. |
| Ezekiel 40 — `ckl:new-jerusalem-prophecy` | A broad CKL parent object overlaps Ezekiel 40:1–4 and carries broader Isaiah and Revelation references. It has no section assignment. The three passage-specific Ezekiel claims are already assigned to existing sections. The held NE-10 bridge `ezekiel-40-48-revelation-21-22-temple` is absent from the projected accepted routes. | Keep the parent object out of the additional child-record path. Do not promote or imply approval of the held Ezekiel/Revelation bridge. Preserve the existing held disposition. |

Mark 2 also includes broader question-oriented and contextual CKL records. They are not reclassified by text keywords. Only a source-backed child record with a non-empty applicable passage anchor and no section assignment is eligible for the new disclosure; passage eligibility continues to use the existing overlap rules, and broader parent objects remain outside it.

## ED-1B compatibility

The ED-1B compatibility review confirms that CKL object changes alter the hash pinned by the historical NE-9C bulk-curation checkpoint. ED-1C makes no CKL object, source, manifest, NE-9C, or NE-10 changes, so it does not refresh or revise those reviewed inputs. The current projector’s six section rules and API schema remain unchanged.

## Reproduction

The baseline was reproduced with:

```bash
python3 scripts/audit_ed1a_evidence_depth.py \
  --output-dir /tmp/ed1c-current-inventory \
  --study-db .bhf-data/study.sqlite
```

Result: 687 CKL objects, 1,189 chapter rows, zero unmapped record identities, validation `pass`; 12,665 eligible placements, 11,642 section-assigned placements, and 1,023 unassigned placements across 394 chapters.
