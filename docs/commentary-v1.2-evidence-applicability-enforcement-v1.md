# Commentary v1.2 evidence applicability enforcement v1

This remediation establishes `commentary-evidence-applicability-v1` at the
EvidenceBundle-to-commentary boundary. It is deterministic, makes no model
calls, and does not alter Prompt 1.8, reader projection, the ancestry envelope,
binding v2, renderer reference presentation, output conformance, validation, or
the richness Gate.

The immutable machine-readable output is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-applicability-enforcement-v1-96f7b9c60c4768cc564ef819/`

## Retrieval is not applicability

Scripture-reference overlap answers whether a CKL parent or child should be
retrieved for inspection. It does not answer whether a claim is legal
current-chapter commentary evidence. A parent may mention a chapter because it
is a useful retrieval key while its legacy prose remains entity, book, lexical,
or global background.

The prior consumer path primarily scored serialized `passage_anchors`. Thus a
legacy field could inherit a parent verse anchor and be treated as verse-
specific, even though its authored applicability metadata said `entity` or
`global`. Synthesis made the same mistake when it projected that inherited
anchor into `CURRENT_CHAPTER`.

The new policy reads the existing metadata and fails closed when it is absent,
unknown, or contradictory:

* authored structured child evidence (`anchor_source=child`) with an
  overlapping own passage/section anchor remains current-chapter eligible;
* inherited legacy parent evidence (`anchor_source=parent`,
  `inherited_from_parent=true`) remains retrievable/background evidence only;
* broad authored scopes (`book`, `global`, `entity`, `lexical`, or `testament`)
  may contribute background/THIN context but never passage specificity;
* resolver-owned passage evidence uses explicit `anchor_source=resolver` and
  may remain eligible; and
* missing applicability, missing/ambiguous provenance, mismatched anchor
  specificity, and contradictory flags are rejected.

No claim text is inspected, no child anchor is fabricated, and no parent anchor
is converted into a child anchor. The migration path remains legacy parent
prose → authored structured claim → authored claim-level Scripture anchor.

## Availability and synthesis effects

Availability keeps the existing score mechanics for background context, but
only policy-eligible items can set the specific boolean. Rejected metadata
contributes zero. Synthesis filters out background and rejected items before
grouping; they remain in the EvidenceBundle and appear in unused/evidence
diagnostics. Broad inherited records are not mislabeled as
`SURROUNDING_PASSAGE`, because they are not necessarily surrounding passages.

| Case | CKL objects | Evidence before → after | Availability before → after | Current units before → after | Surrounding after | Excluded |
|---|---:|---:|---|---:|---:|---:|
| 2 Kings 4 | 9 | 18 → 18 | AVAILABLE → THIN | 18 → 0 | 0 | 18 |
| Psalms 103 | 7 | 6 → 6 | AVAILABLE → THIN | 6 → 0 | 0 | 6 |
| Psalms 19 | 22 | 30 → 30 | AVAILABLE → THIN | 30 → 0 | 0 | 30 |
| Numbers 2 | 1 | 2 → 2 | THIN → THIN | 2 → 2 | 0 | 0 |
| Numbers 1 | 2 | 5 → 5 | AVAILABLE → AVAILABLE | 5 → 5 | 0 | 0 |

The three noisy cases are now truthfully thin. For 2 Kings 4, all 18 records
are inherited legacy fields, including the eight false-positive prophet
profiles and generic Elisha context. For Psalms 103, all six inherited fields
are excluded; the old two nominal duplicate families remain a source-quality
finding, but legal synthesis has zero duplicate units. For Psalms 19, the
Torah records were also inherited legacy fields, so they do not survive merely
because their claims appeared defensible in the bounded diagnostic. The
invariant outranks that example; no Torah path is preserved without authored
child applicability.

Numbers 2 remains a positive control because both records are authored
structured child evidence with overlapping passage anchors, including the
disputed comparison and its qualified passage-relevance record. Numbers 1
retains all five authored claim/note paths, including its chapter-level
section note. These controls demonstrate that the policy removes inherited
specificity rather than suppressing structured evidence.

Useful current-chapter verse ancestry after enforcement is 0% for 2 Kings 4,
Psalms 103, and Psalms 19; 100% for Numbers 2 and Numbers 1 over their
respective tested chapter spans. THIN or DATA_GAP is preferable to AVAILABLE
when the remaining records cannot legally explain the passage. A visible gap
is an honest source-curation signal, not a renderer regression.

## CKL pollution inventory

The deterministic inventory scans the maintained CKL JSON objects for parent
verse/chapter anchors, legacy fields, and no child claim/note with an applicable
own anchor. It records 6,514 suspicious inherited-anchor field instances across
542 parent objects. All were retained; none were deleted or rewritten.

The highest-volume families are person historical/ANE fields in Matthew,
place historical/ANE fields in Genesis and Joshua, event historical/ANE fields
in Exodus, person fields in Luke and Acts, and word-study historical/ANE fields
in Psalms. The full counts by parent type, field, book, specificity,
relationship, and review/source status are in
`ckl-pollution-inventory.json` in the artifact namespace. This is the backlog
for the next CKL curation pass, not a deny-list.

## Psalm 19 ASV integrity

The pre-repair deterministic scan found 116 next-Psalm boundary hits, all in
Psalms, and all matching the same systematic heading-at-preceding-verse
pattern. Psalm 19:14 contained the adjacent Psalm 20 heading exactly as
diagnosed. The isolated correction removed only that demonstrably misplaced
suffix; the post-repair scan finds 115 systematic matches and no Psalm 19:14
match. Psalm 19 was therefore one instance of a broader representation issue,
not an isolated parser/import defect. Legitimate superscription text must be
preserved while the remaining heading representation is migrated.

Psalm 19:14 was corrected: yes. The other 115 matches remain unchanged and
deferred because their intended superscription representation cannot be safely
determined by this narrow scan alone.

The scan and the isolated correction decision are recorded in
`asv-contamination-scan.json`. No model or external source was used. The
canonical-data correction is intentionally isolated from applicability
enforcement and is not used to justify any CKL or commentary change.

## Contracts and boundary

The pre-change hashes are recorded in
`commentary-v1.2-evidence-applicability-contract-freeze-v1.json` and copied
into the artifact. Post-run assertions confirm that Prompt 1.8, reader-level
projection, reader ancestry envelope, binding v2, renderer reference
presentation v1, output conformance, structural/synthesis validators, richness
Gate source, and the CKL database did not change as part of this remediation.
The ASV hash changed only in the separate isolated correction commit.

No commentary was generated, the five-case Sol regression was not run, and the
75-chapter pilot was not started. The next remediation boundary is CKL source
curation and authored child evidence for the now-visible chapter coverage
gaps, beginning with the highest-volume inventory families. Do not author new
evidence for 2 Kings 4, Psalms 103, or Psalms 19 until this clean baseline is
accepted.
