# NE-A2 authored relationship mapping

## Inventory

The committed CKL contains 4,061 top-level authored object relationships across 687 objects. All 4,061 targets resolve. The original labels contain 1,446 distinct values; none matches the current `_CONNECTION_TYPE_BY_LABEL` keys, so all 4,061 were `uncategorized` at the NE-A1 baseline. There are 98 genuinely reciprocal pairs (196 edges) and 3,865 one-way edges. The projector excludes 795 unscoped book-level `related_objects` edges; the total authored-edge inventory is not the same as passage-projected edge placements.

The full frequency table, with an individual disposition and rationale for every original label, is in [`relationship-label-inventory.csv`](relationship-label-inventory.csv). The most frequent baseline labels are:

| Original label | Count |
|---|---:|
| `related-concept` | 724 |
| `narrative-context` | 524 |
| `geographic-context` | 304 |
| `historical-background` | 155 |
| `institutional-context` | 129 |
| `thematic-anchor` | 41 |
| `evidence-cluster` | 35 |
| `historical-context` | 29 |
| `narrates` | 25 |
| `canonical-theme` | 23 |
| `develops-theme` | 23 |
| `theological-anchor` | 22 |
| `related` | 20 |
| `central-person` | 18 |
| `eschatological-fulfillment` | 16 |

## Versioned, exact-label policy

The projection adds an exact-label policy version `nea2-1`. It does not use substrings, titles, notes, shared vocabulary, or target type to classify an edge. It maps only labels whose authored semantics identify an existing connection category:

| Original CKL labels | Count | Projection type | Basis |
|---|---:|---|---|
| `thematic-anchor`, `canonical-theme`, `develops-theme`, `major-theme`, `primary-theme`, `theological-theme` | 104 | `thematic_relationship` | Each label explicitly marks a theme or thematic development. Examples include FAQ-to-theme, book-to-theme, event-to-theme, and symbol-to-theme records; the original label and note remain attached. |
| `historical-narrative-parallel` | 1 | `narrative_parallel` | Jeremiah 52 and 2 Kings 24–25 are explicitly described as parallel narratives. |
| `new-covenant-quotation` | 1 | `direct_quotation` | The authored note says Hebrews 8 and 10 quote Jeremiah's new-covenant promise through Greek textual forms. `relationship_mode` remains `not_recorded`; the type does not invent a separate structured assertion. |
| `later-reception`, `later-canonical-reuse`, `explicit-new-testament-reception`, `explicit-prophetic-reception`, `seventy-years-reception` | 5 | `later_canonical_reception` | Each exact label and its note identifies a later canonical receiving text. The authored direction is preserved and temporal layer is `later_reception`. |
| `typological-connection` | 2 | `interpretive_association` | CKL explicitly labels the Passover/crucifixion pair typological. The original label is preserved, the mode stays `not_recorded`, and reciprocal status comes only from the actual reverse edge. |
| **Total** | **113** | | |

The mapping changes only `connection_type` and, for the five explicitly later-reception labels, the matching `temporal_layer`. Stable edge IDs remain based on the existing source, target, original label, and basis. Source and target orientation, original label, notes, weight, basis, relationship mode, and reverse-edge detection are preserved. The object relationship schema does not record an assertion type or a separate temporal field; the policy does not fabricate either.

The same exact-label table is shared by evidence-level `related_objects` projection. Two additional evidence edges labeled `canonical-theme` therefore also become `thematic_relationship`. They are outside the 4,061 top-level object-edge inventory above; the machine-readable ledger records them separately, for 115 total existing edge records affected by the table. Of the 113 top-level mapped edges, 49 belong to book-level records and remain excluded by the existing passage-projection guard. The other edges still need to pass the existing passage-anchor eligibility checks.

## Evaluated labels left uncategorized

| Original label | Count | Decision |
|---|---:|---|
| `related-concept` | 724 | Remains `uncategorized`. It spans lexical, theological, historical, and thematic records and cannot safely mean quotation or a specific intertextual relation. |
| `institutional-anchor` | 6 | Remains `uncategorized`. The label indicates institutional context but does not identify a supported Narrative Explorer connection type. |
| `historical-layer` | 1 | Remains `uncategorized`. The Assyrian-exile example places an event in a canonical exile layer; it does not specify a listed literary or temporal connection type. |
| `canonical-fulfillment` | 3 | Remains `uncategorized`. A label and short note are not a sufficient basis to present an authored fulfillment conclusion as established later reception. |
| `later-sanctuary-development` | 2 | Remains `uncategorized`. The tabernacle/temple sequence is a historical development label, not necessarily canonical reception or a fulfillment claim. |
| `quotation-source` | 1 | Remains `uncategorized`. “Psalms in Hebrews” does not specify a particular quotation edge. |
| `narrative-echo` | 1 | Remains `uncategorized` pending review of the proposed echo's textual basis and status. |
| `typological-connection` | 2 | Maps only to the broad `interpretive_association` type, retaining the authored typological label and the actual reciprocal pair. It is not mapped to quotation or fulfillment. |

Other labels such as `narrative-context`, `geographic-context`, `historical-background`, `institutional-context`, and `evidence-cluster` remain uncategorized for the same reason: they are meaningful source labels but do not unambiguously match one of the nine connection types. The A2 change does not add relationships. It classifies 113 existing edges and leaves 3,948 of the 4,061 authored object relationships uncategorized at the source-inventory level. Passage-level counts remain subject to anchor eligibility and the existing book-level exclusion.

The exact reciprocal algorithm is unchanged: an edge is reciprocal only when a reverse edge with the same original label is actually present. No related concept becomes a quotation; no historical sequence becomes an established fulfillment; no comparative ancient text becomes direct borrowing; and no one-way edge gains a reverse edge.
