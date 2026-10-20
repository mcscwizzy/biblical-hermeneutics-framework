# Classification and visibility gaps

## The 4,061 relationship finding, recomputed

NE-A1 reported 4,061 authored object relationships and 4,061 projected as `uncategorized`. On current `origin/master`, the authored edge set is still 4,061, but NE-A2’s exact-label map changes the result:

| Current projected type | Edges |
|---|---:|
| `thematic_relationship` | 104 |
| `narrative_parallel` | 1 |
| `direct_quotation` | 1 |
| `later_canonical_reception` | 5 |
| `interpretive_association` | 2 |
| `uncategorized` | 3,948 |
| **Total** | **4,061** |

The 113 mapped edges use 14 exact raw label values. The mapping does not infer a relationship from shared passage scope, theme text, retrieval score, or a presumed reverse edge. NE-A2 also found 49 of its mapped top-level relationships were book-scoped and excluded from passage projection. Those broad edges do not become passage-specific merely because a chapter is inside the book.

## Why edges remain uncategorized

The current result has several different causes; they must not be merged into a single “missing relationship” figure.

| Cause | Current evidence | Audit interpretation |
|---|---|---|
| Authored descriptive label outside exact map | 3,948 top-level edges retain `uncategorized`; 1,446 distinct raw labels occur in the full edge set | Often intentional descriptive association. `related-concept`, `narrative-context`, `geographic-context`, `historical-background`, `contextual`, and `institutional-context` do not each define a specific biblical connection type. |
| Edge rationale absent | 878 top-level relationships have an empty `notes` value | A rationale/support gap at the edge. Do not borrow every parent-object citation and present it as edge-specific support. Prioritize well-used, passage-scoped edges for source-owner review. |
| Coarse or absent passage scope | `CanonicalRelationship` has no passage scope; parent anchors and child claim/evidence anchors are separate | A broad object relation may be accurate but unusable for a chapter-level trail until a claim/evidence record scopes the relation. |
| Relationship meaning needs human review | Labels such as `canonical-fulfillment`, `presence-fulfillment`, `comparative-ancient-text-context`, `parallel`, `later-sanctuary-development`, `historical-layer`, and `institutional-anchor` remain untyped | Some may merit precise categories after review; label text alone is insufficient. Current uncategorized status is a safeguard, not proof that the relationship is false. |
| Existing supported child edge lacks destination navigation | Evidence-to-evidence edges exist in the deterministic graph; the reader’s supported destination parser accepts canonical object IDs, not sibling `#evidence:` IDs | A-class UI/projection gap. The Genesis/Enuma reciprocal `compared-with` records are concrete examples. |
| Non-edge text or field metadata | `cross_references`, `intertextuality`, `new_testament_connections`, legacy entity lists, and sequence descriptions are not all represented as typed `related_objects` edges | Preserve them as authored leads/metadata; promote only after scope, evidence, and classification approval. |

The schema’s `CanonicalRelationship` stores `id`, `relationship`, `weight`, and `notes`; it does not carry source IDs, evidence IDs, temporal qualification, uncertainty, or review status. The CSV therefore marks unavailable edge-level fields as not recorded. Scoped child records and separate provenance rows retain their own source IDs, anchors, certainty/dispute status, and temporal metadata.

## Anchors, provenance, and graph edges are different records

The inventory includes 13,081 passage-applicability rows. These include subject, claim, evidence, and interpretive-note scopes, often with more than one anchor for a record. They answer “what passage applies to this record?” They are not 13,081 cross-passage links. `passage:Genesis 1` → a John claim is not a John-to-Genesis relationship unless an authored claim or edge states and supports that relationship.

The export also contains 1,195 evidence-to-object/evidence relationships, 770 claim-to-evidence links, 4,201 evidence-to-source links, 6,536 claim-to-source links, 6,744 interpretive-note-to-source links, and object-source reference rows. These rows make support traceable without treating nested structure as an independent literary relationship. The two unresolved source IDs are `glancy-slavery` and `harland-associations` on `roman-ephesus-civic-cultic-and-household-life`; no bibliographic metadata was invented.

The explicit evidence graph is deterministic and reuses `framework/canonical_library/evidence_graph.py`; no graph database or second relationship model was created. Its output is supplemented because it does not itself export every legacy/source field that this audit must inventory.

## Directionality

The 4,061 top-level edges contain 98 exact reciprocal pairs (196 edges) and 3,865 one-way edges. Evidence-to-object/evidence relationships contain 34 exact reciprocal edges (17 pairs) and 1,161 one-way edges. “Reciprocal” requires the same label and reversed endpoints. Different labels in opposite directions remain separate one-way records. The count describes authored direction; it is not a quality score. The audit recommends no automatic reverse-link generation.

## Reader projection behavior after NE-8B

NE-8B now places a compact preview above the existing evidence sections. It selects up to three source-backed evidence records with applicable passage anchors and an authored outgoing object/evidence edge with a basis note. A displayed Scripture or comparative anchor is explicitly described as evidence scope, not as proof of a cross-passage connection. Unclassified authored relationships keep the descriptive-association warning.

The remaining pilot gap is navigation to a child evidence destination: a `related_evidence` target can be present in the CKL graph and show its authored basis, but the detail navigation does not open the sibling evidence record as a supported destination. This gap does not make the stored relationship absent. Broad book-level relationships are intentionally suppressed by passage projection, and that behavior should not be “fixed” by inheriting every book theme into each chapter.

## Historical and temporal safeguards

The Genesis 6 Watchers reception record has later-reception content but an anchor marked `direct` / `contemporary`. NE-8B already preserves this concern in the reader. It is a source-owner temporal metadata issue; this audit does not rewrite it. Manuscript witness dates, composition horizons, comparative material dates, and later reception dates remain distinct. Likewise, ancient comparisons such as Ugaritic assembly imagery and Mesopotamian creation material remain comparison evidence, not evidence of dependence by default.

## Gap summary

- **Existing relationships possessed:** 4,061 authored top-level relationships and 1,195 authored evidence-to-object/evidence relationships, plus passage-scoped claim/evidence/source trails. Many are navigable now.
- **Existing relationships needing presentation/classification review:** child-evidence navigation, high-frequency descriptive labels, unscoped or book-level edges, and 878 edges with no rationale.
- **Supported candidates lacking an authored edge:** the smaller set listed in [06-prioritized-candidates.md](06-prioritized-candidates.md). These require separate scholarly and source-owner approval.
- **Genuinely missing CKL support:** a limited set of research gaps, including a scoped Exodus 3:5 holy-ground evidence record and a passage-specific link between Deuteronomy 32 and Psalm 82. “Not represented in CKL” is not a claim that no historical evidence exists.
