# ED-1C before/after results and backlog

## Inventory and projection results

The inventory was reproduced against the current CKL before implementation:

| Measure | Before | After | Change |
| --- | ---: | ---: | ---: |
| CKL objects scanned | 687 | 687 | 0 |
| Eligible item-to-chapter placements | 12,665 | 12,665 | 0 |
| Placements assigned to existing sections | 11,642 | 11,642 | 0 |
| Placements without a section assignment | 1,023 | 1,023 | 0 |
| Chapters with at least one unassigned placement | 394 | 394 | 0 |

ED-1C changes neither the CKL classifier nor the API projection. Its after
state is an additional reader path derived from the existing projection. The
existing six categories, section IDs, source identities, and exact
`applicable_passage_anchors` remain the same. Items are shown in the new path
only when they are CKL claims, evidence records, or interpretive notes; have no
section assignment; have an applicable anchor for the selected passage; carry
a source ID; and are not already assigned to a section or included in the
connection preview.

| Reader state | Before | After |
| --- | --- | --- |
| Overview | Six section cards and passage connection previews; no general route to unassigned child records. | Same six section cards and connection previews, plus a collapsed “Browse N additional sourced records” control when qualifying records exist. |
| Before disclosure activation | The selected passage’s unassigned claims are not available through the overview. | No extra evidence cards are rendered until the reader activates the control. |
| After activation | Not applicable. | The existing section/item renderer shows the qualifying records with their attached provenance, scope, uncertainty, confidence, and review details. Long lists use the existing paged “Browse all” behavior. |
| API and section assignment | Exact passage projection and current assignments. | Unchanged. The new disclosure is a reader view over the same payload; it does not create a topic assignment. |

## Representative outcomes

| Case | Before | After / disposition |
| --- | --- | --- |
| 1 Corinthians 11:3 — `ckl:1-corinthians#claim:1cor-kephale` | Exact passage match was in the API, with `bdag` and `thiselton-1cor`, but no section route exposed it from the overview. Its card label incorrectly said “Evidence type not recorded” despite `claim_type: lexical`. | Available through the collapsed disclosure. The card now says “Lexical research” from the structured claim type; uncertainty and source details remain in provenance. No section is assigned. |
| Micah 1:8–16 — `ckl:micah#claim:micah-empire-reception` | Modern reception-history claim was unassigned; the existing passage path did not surface it. | Eligible for the same reader disclosure. It remains distinct from Assyrian-period historical context and is not reclassified by keywords. |
| Mark 2:23–28 — `ckl:mark#claim:mark-jewish-debate` | Already assigned to `archaeology_ancient_history`. | No correction. It remains in its existing reader category and is excluded from the additional-record list. |
| Mark 2:1–12 — `ckl:mark#claim:mark-disability` | Unassigned pastoral-application record; no section path. | Eligible for the collapsed disclosure at Mark 2:1–12. It is not included when the selected passage is Mark 2:23–28. |
| Proverbs 31:1–31 — `ckl:proverbs#claim:proverbs-greek-order` | API applies the Proverbs 31 anchor in addition to Proverbs 24 and Proverbs 30. The earlier scope concern was not a data defect. | No anchor change. It can be discovered from Proverbs 31 through the disclosure while retaining its three original anchors. |
| Ezekiel 40 — `ckl:new-jerusalem-prophecy` and held bridge `ezekiel-40-48-revelation-21-22-temple` | The broad parent object overlaps Ezekiel 40:1–4; passage-specific Ezekiel claims already have categories. The held bridge is not an accepted route. | Parent objects are excluded from the new child-record path. The held bridge remains absent; no approval or relationship claim is implied. |

These are not keyword-based section rules. The reader path is constrained by
record kind, non-empty applicable passage anchor, source identity, and existing
assignment/preview state. The lexical label reads the structured
`claim_type`; it does not create a Narrative Explorer section assignment.

## Remaining prioritized backlog

1. **Review dense-passage list lengths and navigation.** The new control is
   collapsed and uses the existing paged list, but broad browser acceptance
   should sample passages with many qualifying records and check that the
   count, ordering, and “Browse all” affordance remain easy to scan.
2. **Audit unresolved or incomplete source references separately.** A source
   ID remains visible when its bibliographic record is unavailable. Resolve
   those only through the existing CKL source-integrity workflow; do not hide
   or invent source details in the reader.
3. **Assess unassigned records that do not qualify for this path.** Parent
   objects, questions, unanchored records, and source-less material may need
   their own data-owner or curation review. Do not promote them based on
   matching words or broad object overlap.
4. **Consider category changes only after scholarly review.** Lexical research,
   pastoral application, and later reception remain outside ill-fitting
   categories. Any future category or classification change needs a separate
   review and regression plan.
5. **Keep held-route decisions independent.** Continue to test held NE-10
   candidates, especially the Ezekiel/Revelation bridge, independently of
   discoverability UI work.

The 1,023 unassigned placement count remains a coverage signal. It is not a
completion target and should not be driven to zero through mass remapping.
