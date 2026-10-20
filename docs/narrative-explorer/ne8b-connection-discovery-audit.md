# NE-8B connection-discovery audit

## Baseline and method

This audit uses the fetched `origin/master` tip `19abacc4`, which merges NE-8A PR #37. It reviews the NE-5C interaction, navigation, and source-display contracts; the NE-8A reader-experience results; the current Narrative Explorer renderer and projection; and the CKL records returned for Genesis 6:1–4, Psalm 82, Deuteronomy 32:8–9, and Genesis 2.

The passage counts below come from a read-only CKL-only projection using the committed CKL inventory. The isolated worktree does not contain `.bhf-data/study.sqlite`, so this audit does not claim live Maps or archaeology coverage for Genesis 2. No CKL record, generated Commentary artifact, or database was changed.

## Passage findings

| Passage | Relevant available records and limits | Reader-facing finding |
| --- | --- | --- |
| Genesis 6:1–4 | The CKL projection returns separate items for the disputed “sons of God” readings and Nephilim notice, a Watchers-reception record, and a Gilgamesh flood comparison. The Watchers record is titled “Second Temple Watchers reception of Genesis 6” and its sources include 1 Enoch and Jubilees, but its Genesis anchor is marked `direct` / `contemporary`; NE-8A already documents this temporal-metadata ambiguity. The Gilgamesh record is explicitly comparative and says it does not establish direct chronological priority. | The preview layer can distinguish interpretation, later reception, and ancient comparison, but does not show a connection basis or other destinations before “Inspect evidence and connections.” The temporal mismatch needs to stay qualified. |
| Psalm 82 | The projection returns “Psalm 82 divine-assembly language” as a disputed interpretive item and a separate “Ugaritic council imagery comparison.” Its basis says the comparison does not decide the poem’s referents. The parent `ancient-divine-assembly-imagery` has a one-way authored edge to `deuteronomy` labelled `textual-variant-context`, with a note that Deuteronomy 32:8–9 requires manuscript-specific handling. | The reader can distinguish the biblical observation from the Ugaritic comparison after opening the records. The Deuteronomy relationship is on the parent subject, so finding it requires another trail step; it is not visible in the passage overview. |
| Deuteronomy 32:8–9 | One passage-specific CKL evidence item is “Deuteronomy 32:8 manuscript variation.” It retains `textual_variant` dispute status and a direct anchor to Deuteronomy 32:8–9. Its parent relationship is a one-way `textual-critical-context` edge. | The manuscript witness is available and qualified, but the overview gives no direct cue that this is textual evidence, and the edge label alone does not explain its scope. No divine-assembly conclusion should be inferred from this manuscript item. |
| Genesis 2 | The CKL projection includes “Garden planting and divine presence” and “Four rivers and limits of Eden identification.” The latter is disputed and the record says the rivers do not establish a recoverable garden location. The selected Eden seed set has no direct authored inter-object link in the existing narrative-trails audit. | The preview can show geography and interpretive labels, but the connection basis and the absence of a recorded cross-object path are not apparent before opening a record. Physical coordinates must remain withheld unless an existing Maps record establishes displayability. |

## Verified experience deficiencies

1. **No connection preview at the passage entry.** `renderOverview` starts with a general explanation and renders up to two items per section. `orderForPreview` sorts by stable ID, not connection relevance. The section named “Themes & Biblical Connections” is an evidence-item category; it does not preview the authored edges themselves.
2. **The reason for a connection is hidden until after selection.** Preview cards place provenance in a collapsed “Evidence and source details” disclosure. The full edge basis, direction, and navigable destination appear only in `renderEvidenceDetail`, after the reader has chosen an item.
3. **The detail renderer can make unlike links look alike.** The projection assigns `uncategorized` to source-anchor edges such as `direct` and `comparative`, as well as to CKL relationships whose label is not mapped. `renderConnection` presents the former with an unavailable category and the same descriptive-association caution used for unclassified authored relationships. Readers therefore do not get a clear first-glance distinction between a passage anchor, an ancient comparison, later reception, and an unclassified CKL association.
4. **Some useful paths take an extra hop.** For example, Psalm 82’s Deuteronomy 32 relationship is recorded on the parent CKL subject. The existing trail makes that path navigable and preserves one-way direction, but the overview does not surface it as a route to explore.

The existing detail view does preserve stable IDs, source provenance, dispute state, edge direction, reverse-edge validation, and the three-hop/cycle limits. The audit found no need to rebuild those contracts or create edges. NE-8A’s Psalm navigation fix and reader labels remain applicable.

## Source locations reviewed

- `docs/narrative-explorer/ne5c/01-interaction-contract.md`
- `docs/narrative-explorer/ne5c/02-navigation-and-history.md`
- `docs/narrative-explorer/ne5c/03-source-and-evidence-display.md`
- `docs/narrative-explorer/ne8a-reader-experience-results.md`
- `docs/narrative-explorer/03-evidence-and-connection-contract.md`
- `docs/narrative-explorer/coverage-audit/06-narrative-trails.md`
- `bhf_web/static/narrative-explorer.js`
- `bhf_agent/presentation/narrative_explorer.py`
- `framework/canonical_library/objects/cultural_background/genesis-flood-postflood-context.json`
- `framework/canonical_library/objects/cultural_background/ancient-divine-assembly-imagery.json`
- `framework/canonical_library/objects/books/genesis.json`
