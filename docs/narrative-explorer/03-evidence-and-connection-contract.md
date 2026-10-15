# Narrative Explorer: Evidence and Connection Contract

## Contract goals

Narrative Explorer needs one versioned, read-only projection over CKL and current Study Companion/map/archaeology contracts. It does not own canonical facts, mutate CKL, persist presentation prose, or create a parallel evidence database.

Proposed route family: GET /api/narrative-explorer/v1/passages/{book}/{chapter}, with optional verse_start and verse_end. The version is explicit in the path and response. Existing routes and response schemas remain unchanged until an approved implementation transaction.

## Projection envelope

| Field | Contract |
|---|---|
| schema_version | Exact projection version, initially 1.0. |
| passage | Normalized reference, book, chapter, optional verse range, and requested scope. |
| coverage | Per-domain query state, returned count, and stable reason code if incomplete. |
| sections | Ordered reader-facing categories with available, partial, not_represented, or unknown state and links to projected items. |
| items | Read-only claim, subject, source, artifact, place, person, event, or relationship projections. |
| connections | Explicit typed edges with stable IDs, endpoints, basis, and direction/reverse-link availability. |
| navigation | Passage, CKL object, map place/route, archaeology record, and source destinations resolvable by existing routes. |

The projection is deterministic for the same source records and version. It may carry an existing evidence hash where the bundle supplies one. It must not include a generated timestamp or confidence score unless an underlying contract supplies it.

## Evidence item fields

Each displayed factual or interpretive item retains, where supported:

| Field | Source and rule |
|---|---|
| id | Stable domain-qualified ID. CKL evidence and claims use a parent namespace, such as ckl:{object_id}#evidence:{local_id} or ckl:{object_id}#claim:{local_id}. Map and archaeology IDs retain their domain prefix. Never rely on a possibly colliding local evidence ID alone. |
| object_id, evidence_id, claim_id | Original CKL IDs, separately preserved when available. Do not replace them with display labels. |
| passage | Original passage reference plus the exact relation from scripture_references or typed evidence passage links. Do not widen a verse-scoped claim to the whole chapter. |
| title, claim, description | Authored source text. A generated headline is not the underlying claim. |
| evidence_category | Preserve source type and assertion type, including artifact, inscription, ancient-text, manuscript, historical-event, literary-convention, and worldview-concept. Do not relabel an ancient text as excavation evidence. |
| basis | Stored relevance rationale, notes, claim rationale, source support, or relationship notes that explain why the item is linked. If no basis is stored, show no explanatory claim or label it uncategorized; do not infer a rationale from title similarity. |
| sources | Source IDs and recorded bibliography fields: title, author, publisher, year, locator, URL, source type, supports, and notes. Omit absent fields. Do not fill missing bibliography from memory. |
| confidence, certainty, dispute_status | Preserve original values and meanings separately. Confidence is not certainty; dispute status is not a confidence score. An absent value is not high, not_disputed, or consensus. |
| review_status, content_status, human_review_required | Preserve CKL governance metadata. Do not suppress draft/in-review records without an explicit eligibility policy; expose their status. |
| relationship_to_passage | Preserve the stored Scripture or evidence relationship (direct, contextual, comparative, contrast, disputed, or the original Scripture-reference relationship). |
| relationship_mode | direct only when an explicit passage/evidence link supports it; inferred only when a stored claim or typed edge records an inference. Do not derive it from retrieval score, co-occurrence, or theme membership. |
| temporal_relation | Keep the evidence's historical relation (contemporary, near-contemporary, earlier-comparative, later-comparative, diachronic, unknown) separate from source composition or surviving-copy date. |
| related_passages | Only passage references present on the claim, evidence, object, or explicit relationship. Include relation and basis for each. |
| related_subjects | Stable CKL/map/archaeology IDs plus recorded relationship label, weight, notes, and whether a reverse edge is present. |

### Source and claim traceability

Use CKL claims, evidence_items, sources, and evidence_graph_edges as the traceability path:

passage → CKL object → claim → evidence → source

The graph module already namespaces object-local IDs and can expose related geography and external-domain edges. The Study Companion EvidenceBundle v1.0 and narration models also preserve passage anchors, source IDs, claim IDs, evidence IDs, source details, certainty, dispute status, and parent-object IDs. Narrative Explorer adapts these into one UI envelope without writing them back.

If a reference points to an unavailable source ID, retain the ID and show “Source details not available in CKL.” Do not fabricate a title. The current card compatibility payload may fall back to a source ID as a display title; that is not complete bibliographic provenance.

## Connection type vocabulary

The projection connection_type is one of:

- direct_quotation
- explicit_textual_reference
- shared_literary_motif
- narrative_parallel
- thematic_relationship
- later_canonical_reception
- proposed_intertextual_echo
- interpretive_association
- uncategorized

Each edge also carries basis (a reference, claim, evidence ID, authored relationship note, or source citation), relationship_mode (direct, inferred, or not_recorded), direction (one_way or reciprocal), reverse_edge_id (only when actually represented), and temporal_layer (original passage context, comparative background, later reception, or unknown).

The semantic labels cannot be safely inferred from a shared theme string. Preserve the original CKL relationship alongside the UI vocabulary. A curation decision is required before mapping ambiguous free-text relationships to a more specific label. If that decision is not recorded, return uncategorized and retain the original label/notes.

## Evidence status and absence semantics

Keep these states separate:

- **Unknown:** a field is absent, the source does not state it, or retrieval failed. Include a reason code where one exists.
- **Not established:** an authored claim explicitly says that evidence does not establish a proposed conclusion. It is not a generic label for missing metadata.
- **Disputed:** the record explicitly marks a dispute, textual variant, interpretive uncertainty, or competing view. Preserve recorded status and basis.
- **Not represented in CKL:** a completed lookup over the selected CKL inventory returned no eligible record for that category. This describes BHF data coverage, not the historical world or truth of a claim.
- **Partial:** at least one relevant record is available, but one or more subdomains or metadata fields are absent or unavailable.

Do not convert an API error, absent field, zero result, or missing source link into one of the other states. Do not turn a record's absence into “no evidence exists.”

## Passage applicability and inherited material

- Apply the same explicit Scripture-anchor overlap and semantic-misanchor check used by bhf_agent/presentation/eligibility.py.
- Prefer claim/evidence-scoped passage links over a broad parent-object anchor. A book-level object must not contribute all its themes, cross-references, or historical background to one chapter merely because the book matches.
- For a broad parent, include only nested claims, notes, and evidence items whose own passage links overlap the selected scope. Preserve parent ID for provenance, but mark the projected child as passage-scoped.
- context_applicability may constrain which historical, ANE, Hebraic-worldview, Second Temple, canonical, or later-reception layer is relevant. A true flag is not itself evidence for a claim; absent or false flags do not authorize inheritance.
- Keep original-passage observations separate from ancient comparative materials and later reception. A later source about a passage is not extra detail in the original passage.

## Physical and cosmic geography

Every location or spatial reference has an explicit geography_kind:

- Physical: physical_place, physical_region, political_territory, route, or archaeological_site.
- Textual/conceptual: cosmic_textual, sacred_space, literary_space, or symbolic_geography.
- unknown when CKL and the linked domain do not establish the kind.

Only physical records can point to a map reference. Cosmic, heavenly-assembly, chaos, Eden-presence, or sacred-space language remains textual/conceptual unless a source explicitly identifies a physical place.

For physical records, keep the biblical name/reference, map record's stored coordinate, modern site identification, identification confidence/uncertainty, and source/period independent. Use only coordinates already stored on an eligible map record. Do not generate coordinates or treat a stored point as proof of identification. Hide exact point geometry when identification is unresolved or materially disputed; offer the text and uncertainty, and a broad region only if supported. Genesis 2–3 is an immediate validation case because current map data gives Eden and named rivers point coordinates without a CKL location-identity record.

## Read-only and privacy rules

- Projection routes use GET and do not write display summaries, claims, confidence, map geometry, or links into CKL or the Study DB.
- Preserve source version/hash supplied by existing APIs where available. Do not cache a projected claim longer than the source cache policy allows.
- Do not include user notes, highlights, saved-study text, or personal study history.
- An Ask BHF handoff may use only a user-selected passage, topic/evidence IDs, source IDs, and typed question after explicit user action. NE-1 does not implement this handoff extension.
