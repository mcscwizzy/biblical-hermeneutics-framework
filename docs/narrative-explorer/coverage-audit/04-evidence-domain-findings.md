# Evidence-domain findings

## CKL context and evidence types

- Eligible cultural-background parent records across chapter projections: 449.
- Passage-anchored historical/cultural claims: 1000; historical/ANE/Second Temple notes: 333.
- CKL archaeology parent projections: 148 across 64 chapters; typed artifact/site/inscription/material-culture evidence items: 118 across 77 chapters; unanchored CKL archaeology evidence items: 0.
- Ancient-text/manuscript/primary-source CKL evidence items: 85 across 70 chapters. These are literature/manuscript evidence classifications and do not automatically represent archaeological sites.

## Archaeology service

- Inventory items: 75; items with valid passage links: 71; items without one: 4.
- Explicit passage-link rows: 94; valid references: 94; invalid references: 0; broken targets: 0.
- Manuscript service is separate: 6 items, 6 with valid passage links, 0 without.
- Chapters with at least one explicit archaeology-service link: 59.
- A zero link count means no matching explicit row in this service index; it does not prove that no relevant historical or archaeological evidence exists.

## Physical geography

- Place catalog: 1338 items; 1281 have valid passage associations and 57 do not. Passage-linked place rows: 7741 across 812 chapters; route links: 2; territorial/political links: 13.
- Place-catalog confidence rows labeled unknown/low/disputed: 277. This is the catalog's general confidence field, not a separate site-identification judgment.
- CKL place objects with unknown/uncertain identification status: 388 chapter placements; this is separate from coordinate presence and general map-catalog confidence.
- Static map feature passage links: 222 across committed map layer JSON; the NE service map lookup reads linked place/route repositories and does not query those static layer files.
- Missing destinations and invalid anchors are recorded per source table in the validation JSON. CKL identification metadata and general map-catalog confidence are separate; stored coordinates do not establish identification.

## Cosmic geography

- CKL cosmic-section item projections: 17 across 6 chapters, under the unmodified NE-5A special evidence rules.
- Current map records use physical place/route categories; explicit typed sacred-space map links found in the sampled service outputs: 0.
- The current SQLite place/route link schema has no authored `geography_kind` field. General mountain, temple, presence, kingship, sea, or wilderness references were not promoted to cosmic geography.
- Exact cosmic-section item IDs are in `cosmic_geography_ckl_item_ids_json` by chapter in the CSV; cross-canonical topic anchors are in `06-narrative-trails.md` and the topic inventory in validation JSON.

## Narrative Explorer sections and retrieval

- `biblical_narrative`: 5003 CKL projected item-chapter placements.
- `archaeology_ancient_history`: 2475 CKL projected item-chapter placements.
- `biblical_geography`: 607 CKL projected item-chapter placements.
- `divine_council_cosmic_geography`: 17 CKL projected item-chapter placements.
- `themes_biblical_connections`: 5588 CKL projected item-chapter placements.
- `people_events_relationships`: 1720 CKL projected item-chapter placements.
- Projected CKL items with no current section assignment: 1892 placements.
- CKL object relationships: 4061 authored relationships; 4061 map to `uncategorized` under the current projection taxonomy; 11342 explicit passage graph edges; 795 book-level edges are excluded from NE projection.
- Projected relationship placements: 14381 direct and 9 inferred; placements repeat an edge across applicable chapters. In the underlying object graph, 98 relationship pairs are genuinely reciprocal and 3865 edges are one-way.
- Source IDs in the global inventory: 2784; unresolved child source references: 2; weak bibliography references: 16; unresolved passage anchors: 1.
- The sample identifies records present in explicit-link tables but absent from normal text-first API results. Acts 7 has one explicit place link (`openbible-a012705`) absent from the sampled live map output. Unqueried map and archaeology API results remain unknown, not empty.

## Provenance and content review

- Source records: 5232 records and 2784 distinct IDs; 17483 child source references, 17481 resolving to a parent bibliography entry, and 2 unresolved. The two unresolved IDs (`harland-associations`, `glancy-slavery`) occur on one interpretive note with no note-level Scripture anchor, so it has no eligible chapter placement.
- Records without a valid explicit passage association: 0 archaeological evidence items, 0 ancient-text/manuscript items, and 15 historical/cultural claims. Stable IDs and per-record anchor states are in validation JSON.
- Across projected chapter-item placements: 0 lack review metadata; 4178 lack certainty metadata; 4178 lack dispute metadata; 12662 require human review; 7137 are explicitly disputed and 42 explicitly marked plausible, speculative, or insufficiently evidenced. A further 4178 have unknown or unestablished interpretation state.
- These are chapter-placement totals, so one CKL item can appear in more than one chapter. The CSV has chapter-local source and review fields.
