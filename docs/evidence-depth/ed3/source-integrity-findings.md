# Source Integrity Findings

This report separates established defects from inherited inventory signals.
The CKL strict validator and heuristic checker were read independently; a
heuristic flag is not treated as a defect without a resolvable target or
identity problem.

## Unresolved child-source references

Both inherited references were in one interpretive caution in
`roman-ephesus-civic-cultic-and-household-life.json`. The same object contains
exact, bibliographically identified records:

| Old reference | Established local record | Identity check | Finding |
|---|---|---|---|
| `harland-associations` | `harland-associations-ephesus` | Philip A. Harland, “Honours and Worship: Emperors, Imperial Cults and Associations at Ephesus,” *Studies in Religion* 25(3) (1996), 319–334; SAGE DOI record | Exact title, author, year, publication, and Ephesian topic match. Safe local-reference repair. |
| `glancy-slavery` | `glancy-slavery-ephesus` | Jennifer A. Glancy, *Slavery in Early Christianity* (Oxford University Press, 2002); local record gives the specific Ephesian-context locator | The exact local record exists. The shorter ID is used for other Glancy works elsewhere in CKL, so the long Ephesian ID is the safe target here. |

No new bibliography record was needed. Other references to the short Glancy ID
in other CKL objects were not globally rewritten; those are separate, locally
defined identities and must be assessed in context.

## Missing expected locator

`patristic-minor-prophets` in `malachi.json` resolves to Hauna T. Ondrey,
*The Minor Prophets as Christian Scripture in the Commentaries of Theodore of
Mopsuestia and Cyril of Alexandria* (Oxford University Press, 2018). The
publisher's public catalog confirms the book identity, but no Malachi-specific
section locator was established from the accessible catalog. The broad
collection-level source may be legitimate; adding a chapter or page number
would be guesswork. The locator remains unresolved, with the OUP book text or
index needed to resolve it.

## 102 source-support-target heuristic findings

The findings were grouped by whether a target actually resolves in the local
object or anywhere in the CKL. The checker was not weakened.

The exact 102 rows, target IDs, current classification, and recommended action
are in [source-support-targets.csv](supporting/source-support-targets.csv).

| Classification | Count | Assessment |
|---|---:|---|
| Target ID exists as a claim in another CKL object | 45 | Cross-object references; the heuristic checks local fields and therefore reports them. These need contextual/human review but are not confirmed invalid targets. |
| Target is a present top-level field not flattened by the heuristic | 14 | `structure`, `archaeology`, or `claims` fields exist; the local field-level target is valid. |
| Generic field labels or categories | 24 | Labels such as `key-events`, `key-people`, `key-places`, or `greek-words`; these are not claim IDs. Whether they express useful support depends on the object's schema and reader use. |
| Semantic target with no exact local or global target found | 19 | Mostly Roman Athens semantic labels plus one Acts label. No safe target can be inferred; retain for human research. |
| **Total** | **102** | **No confirmed defect repaired by broad checker changes.** |

The last group is an unresolved provenance/target issue. A future repair needs
the authoring rationale, intended target, and impact on support tracing. Do not
replace a semantic target with the nearest similarly named claim.

## Sparse bibliography inventory

The ED-1A set of 558 source IDs without a title plus bibliographic detail was
reproduced from the current CKL with the original traceability rule. The exact
IDs and deterministic triage labels are in
[sparse-bibliography-triage.csv](supporting/sparse-bibliography-triage.csv).
This is an identity/type inventory, not fresh publication-level verification
of 558 sources.

| Category | Count | Treatment |
|---|---:|---|
| Scripture/text-source identities | 472 | Expected compact identifiers; not missing scholarly publications. |
| Reference-work identities | 86 | Machine-triaged as 26 Scripture/passage labels typed as reference works, 30 institution/catalog/artifact identities, 7 collection/topic labels, 3 metadata/type variations, and 20 ambiguous identities. |
| IDs with at least some non-empty identity metadata variation in the baseline audit | 81 | Variation is not itself a defect; retain as review signals. |
| IDs with locator variation in the baseline audit | 148 | Variation may reflect different passages/editions; do not normalize globally without relationship checks. |

The 558 IDs were all reproduced and given a deterministic initial class. The
472 Scripture/text-source identifiers need no bibliographic expansion; all 86
reference-work identities remain deferred for use-specific research. Separate
source-identity variation candidates (`aune`, `bauckham`,
`burnett-imperial-honors`) and edition-sensitive entries such as `bdag` and
manuscript catalogs need record-by-record review. No publication identities
were independently established for these by this inventory. **Screened: 558;
safely corrected: 0; deferred for additional work: 86 reference-work
identities plus the separate variation candidates.** No hundreds of
bibliography entries were manufactured.

## Other verified limitations

- Psalm 17's source record asserted that the Italian article had not been
  reviewed. The full article was freshly read. This access/provenance statement
  was stale; the underlying Hebrew apparatus was not independently checked.
- No source-lock input or frozen NE-9C/NE-10 artifact was modified. Stable
  bibliography identifiers, support targets outside the two exact local
  repairs, and all protected relationship decisions remain untouched.
