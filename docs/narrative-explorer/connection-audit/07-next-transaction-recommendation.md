# Next transaction recommendation

## Recommendation

The next transaction should be a **narrow Narrative Explorer projection/navigation fix**, followed by a small, approved CKL curation set. It should not begin with broad source expansion or a blanket relationship-label remapping.

The highest-priority A-class finding is concrete: CKL already stores 1,195 evidence-to-object/evidence relationships, including supported and reciprocal evidence-to-evidence comparisons, but a sibling `#evidence:` record is not a supported reader navigation destination. Add a reader destination that can open the linked evidence record with its own sources, anchors, temporal qualification, uncertainty, and parent object. Keep the existing no-inference behavior and exact authored direction. The Genesis 1 Enuma comparison supplies a source-backed acceptance case.

## What BHF already possesses

- 4,061 authored top-level object relationships across the 687-object CKL.
- 1,195 authored evidence-to-object/evidence relationships, plus explicit claim/evidence/source paths and thousands of passage-applicability records.
- Passage-scoped support for several useful pilot trails, including Genesis 1 comparisons, Genesis 2 garden/rivers evidence, Genesis 6 interpretations and reception, Psalm 82 assembly and Ugaritic comparison, Deuteronomy 32 manuscript evidence, and the Creation/New Creation theme route connecting John 1 and Revelation 21.
- Source-backed candidate material for a few additional passage bridges, including John 1 / Genesis 1, Genesis 3 serpent reception / Revelation 12, Psalm 82 / justice theme, and Revelation 21–22 / Genesis or Ezekiel.

These records are not all classified or navigable in the same way. A current `uncategorized` count of 3,948 does not mean those edges or sources are absent. It means they were not assigned one of the projector’s exact typed categories.

## What is actually missing or needs separate review

- **Projection gap:** support navigation to authored child evidence destinations.
- **Source metadata issue:** resolve the two object-local references `glancy-slavery` and `harland-associations` on `roman-ephesus-civic-cultic-and-household-life`.
- **CKL relationship quality:** review high-value edges among the 878 without rationale; review descriptive labels one edge family at a time; keep book-level suppression unless a passage-scoped source record is curated.
- **Scholarly candidate edges:** route the C-class entries in [06-prioritized-candidates.md](06-prioritized-candidates.md) to the relevant source owners. Do not write them until approved.
- **Research gaps:** Exodus 3:5 holy-ground evidence and a direct Deuteronomy 32 / Psalm 82 passage relationship need research before edge curation. This audit does not say that no outside scholarship exists; it says the current CKL material does not establish the relationship at the requested scope.
- **Separate temporal review:** preserve the Watchers record’s `direct` / `contemporary` anchor mismatch for CKL source-owner review. Do not fold it into a general projection change.

## Suggested transaction sequence

1. **Projection transaction:** implement evidence-record destinations and verify source/anchor/uncertainty continuity. Keep feature flags and release/deployment settings outside this audit; no deployment is authorized here.
2. **Metadata transaction:** resolve the two missing source references and perform the separately owned Watchers temporal review.
3. **Scholarly curation transaction:** select a small number of high-utility C-class edges with source-owner approval. Each must identify exact passage scope, relation type, rationale, evidence/source IDs, historical layer, uncertainty, and review status.
4. **Taxonomy transaction only if needed:** review representative descriptive labels and rationale with edge owners. Do not mass-convert `related-concept`, `narrative-context`, `historical-background`, or `canonical-fulfillment` into a specific relation type based on label text.
5. **Source expansion only for confirmed D-class needs:** commission narrowly scoped research for gaps such as Exodus 3:5 or a Deuteronomy/Psalm 82 bridge only if those reader questions remain a priority after current material is surfaced.

## Stop conditions for the next transaction

Keep Scripture anchors as applicability records. Do not create reverse edges automatically. Do not merge original textual evidence, ancient comparisons, later reception, and theological interpretation into one relation class. Do not make claims about dependence, coordinates, chronology, or equivalence without explicit source support. Use the CKL and the existing evidence graph as the source of truth; do not create a competing relationship store.

The principal missing work is currently presentation and selective relationship curation, not a wholesale absence of evidence. Source expansion is warranted only for individually confirmed research gaps after the existing material is made legible.
