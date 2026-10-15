# Prioritized gaps and recommended work

Priority is an editorial recommendation based on reader impact, existing source availability, reuse across passages, and severity of a broken link. It is not a numeric certainty score.

## A. Retrieval and projection

1. **Expose already-anchored but unclassified CKL items.** 1892 projected item placements have no NE section. Audit the concrete IDs in `chapter-census.csv` before changing policy; keep NE-5A safeguards in force.
2. **Map authored relationships to supported projection types.** All 4061 authored object relationships currently map to `uncategorized`; review the label-to-type mapping and add examples for supported relationship kinds without inventing new edges.
3. **Investigate the sampled Acts 7 map miss.** The explicit place link `openbible-a012705` was not returned by the live map resolver; trace the resolver's text-first filtering and fallback before changing display behavior.
4. **Review broad parent anchors.** 0 chapters have broad-scope parent anchors excluded by the projector; 0 chapters contain unscoped book-level anchors and 704 contain multi-chapter anchors. The multi-chapter count is a scope inventory, not a quota or demonstrated failure.
5. **Review semantic-misanchor suppression.** Current guard suppresses matching authored anchors in 0 chapters. Preserve negative controls; fix only proven authoring or scope errors.
6. **Connect political-context/territory links to the Narrative Explorer map lookup if desired.** The current NE provider calls place and route resolvers; it does not query the existing `political_context_references` repository. Keep these results distinct from physical place identification.

## B. Relationship curation

1. Resolve 0 authored relationships with missing destinations; preserve rationale and target identity.
2. Review the rationale and scope of one-way object edges (3865); 98 reciprocal pairs are present and 0 exact duplicate entries were found.
3. Preserve passage-specific anchors and their relationship types while curating cross-book trails. The trail audit lists where CKL has objects but no authored traversable object-to-object relationship.

## C. Genuine CKL evidence gaps

- 132 chapters currently have no passage-eligible CKL item under NE-5A rules. Treat this as an inventory gap only; commission research where the narrative and available scholarship justify it, not to meet a chapter quota.
- Use the pilot and stratified cases to identify high-value episodes where source material already exists but CKL lacks an explicit, supported passage link. Add evidence only in a future, separately reviewed CKL curation transaction.
- Do not count ancient literary comparisons as archaeology records or infer physical site identification from coordinates.

## D. Provenance and review

- Resolve 2 child citations whose source ID is absent from the parent source list. Both occur on the same interpretive note without a note-level Scripture anchor; add bibliography entries and anchor scope only if its applicability is supported.
- Harden 16 source references lacking a title plus author/publisher/year/locator/URL detail.
- Target eligible records missing certainty, dispute, review, or human-review metadata before expanding their section reach. Uncertainty belongs with disputed evidence rather than being hidden.

## E. Domain completeness uncertainty

- The all-chapter map and archaeology service outputs were not requested 1,189 times. Explicit link tables are fully enumerated; text-first resolver results are established only for the validation sample. Keep all other API result states unknown.
- A passage with zero archaeological link rows is not a verified absence of relevant historical evidence. Research and source-aware linkage are separate next steps.
- The map link tables establish a linked-record inventory, not whether a stored physical identification is accepted or certain.
