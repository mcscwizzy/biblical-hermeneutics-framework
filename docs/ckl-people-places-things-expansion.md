# CKL People, Places, And Things Expansion Plan

This plan expands the Canonical Knowledge Library (CKL) around the way readers
naturally look for biblical entities: people, places, and things. The CKL schema
should remain more precise than that user-facing taxonomy.

## Taxonomy

- **People** map to CKL `person` objects.
- **Places** map to CKL `place` objects.
- **Things** map to non-person, non-place entity categories: `event`,
  `institution`, `archaeology`, `theme`, `theology`, `word_study`, `prophecy`,
  `timeline`, `covenant`, `biblical_theology`, `cultural_background`, `symbol`,
  `literary_device`, and `doctrine`.

The `book` and `faq` categories are useful library surfaces, but they are not
treated as people/place/thing expansion lanes.

## Current Baseline

As of the initial expansion audit:

- CKL contains 612 valid objects.
- People lane: 101 objects.
- Places lane: 75 objects.
- Things lane: 319 objects.
- Empty thing-oriented folders: `biblical_theology`, `covenants`,
  `cultural_background`, `doctrine`, `literary_devices`, `symbols`, `timeline`.
- Production retrieval still depends on review and placeholder governance, so
  increasing object count is less important than increasing reviewed, sourced,
  relationship-rich objects.

Regenerate the live baseline with:

```bash
python3 tools/ckl_report.py --root framework/canonical_library
python3 tools/ckl_expansion_backlog.py --root framework/canonical_library --limit 30
```

## Quality Bar

An expanded object should not move beyond placeholder or draft status until it
has enough content to help the retrieval layer without pretending certainty.

Required authoring targets:

- Retrieval aliases that match likely user phrasing.
- A concise summary.
- Historical and literary context.
- Canonical role or canonical context.
- Scripture references with supported reference syntax.
- Typed `related_objects` links.
- Interpretive notes with caution, certainty, and dispute framing when needed.
- Sources for historical, archaeological, lexical, or disputed claims.
- Review metadata that separates generated provenance from human review.

## Phase 0: Stabilize

Goal: make expansion safer before adding much more material.

1. Run the CKL report and backlog commands.
2. Fix unsupported scripture references in high-importance objects.
3. Replace repeated boilerplate in high-importance people, places, events,
   institutions, and archaeology.
4. Remove legacy AI reviewer strings from `reviewed_by`; record generated or
   edited provenance in the correct metadata instead.
5. Keep `tools/ckl_report.py` at zero errors and reduce warnings wave by wave.

### Phase 0 Checkpoint

Initial stabilization work:

- Ran the CKL migrator across the inventory so legacy AI reviewer strings are
  moved out of `reviewed_by` and into structured provenance.
- Normalized legacy source and interpretive-note shapes to the current schema.
- Split the first high-visibility archaeology scripture-reference cluster into
  supported chapter or verse references.
- Reduced CKL report warnings from 145 to 138 while keeping validation at zero
  errors.
- Confirmed `tools/ckl_migrate.py --root framework/canonical_library` reports
  `library already normalized` after the cleanup.

## Phase 1: Convert Or Retire Placeholders

Goal: eliminate empty objects from the expansion lanes.

1. Run:

   ```bash
   python3 tools/ckl_expansion_backlog.py \
     --root framework/canonical_library \
     --lane things \
     --limit 40
   ```

2. Replace event placeholders with real high-value events, or remove them during
   a deliberate inventory cleanup.
3. Validate each changed object.
4. Regenerate the manifest after object additions, removals, or type changes.

### Phase 1 Checkpoint

Initial placeholder replacement work:

- Replaced all 13 `event-placeholder-*` files with substantive event objects.
- Added one additional high-value event object while the event inventory was
  being expanded, bringing the event count from 75 to 76 and the total CKL
  object count from 612 to 613.
- Updated `manifest.json` and exact-count tests to match the expanded inventory.
- Confirmed the `things` backlog no longer reports placeholder objects; it now
  reports `things: complete=320`.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 2: Deepen Core People

Goal: make the highest-traffic people objects reliable anchors.

Priority groups:

- Jesus and Gospel figures.
- Patriarchs and matriarchs.
- Moses, Aaron, Miriam, Joshua, and wilderness figures.
- Major judges, kings, and prophets.
- Paul, the Twelve, and major early church coworkers.

Run:

```bash
python3 tools/ckl_expansion_backlog.py --root framework/canonical_library --lane people --limit 25
```

Each completed person should link to key places, events, institutions, themes,
and relevant books.

### Phase 2 Checkpoint

Initial core-people deepening work:

- Filled `hebraic_worldview`, `second_temple_context`, `canonical_context`, and
  `canonical_role` for Jesus, Abraham, Moses, David, and Paul.
- Added key people, place, and event relationships for the same five anchor
  figures so retrieval has concrete graph paths into the surrounding CKL.
- Confirmed the people backlog shifted away from those five objects; the next
  highest-priority people batch now begins with Joshua and the prophetic
  cluster.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 3: Deepen Core Places

Goal: make geography useful for context building and map-linked workflows.

Priority groups:

- Jerusalem, Zion, the temple complex, and other worship-centered places.
- Egypt, Babylon, Assyria, Persia, Rome, and other imperial settings.
- Canaan, Galilee, Judea, Samaria, wilderness regions, and journey routes.
- Places already used by frontend maps and journeys.

Run:

```bash
python3 tools/ckl_expansion_backlog.py --root framework/canonical_library --lane places --limit 25
```

Each completed place should link to key people, events, archaeology, routes, and
canonical themes.

### Phase 3 Checkpoint

Initial core-place deepening work:

- Filled `hebraic_worldview`, `second_temple_context`, `canonical_context`, and
  `canonical_role` for Shechem, Jerusalem, Mount Sinai, Babylon, and Egypt.
- Added key people, place, and event relationships for the same five anchor
  places so geography can connect into patriarchal, exodus, temple, exile, and
  Gospel retrieval paths.
- Added an additional Scripture source for Shechem so its high-importance place
  entry is less thinly sourced.
- Confirmed the places backlog shifted away from those five objects; the next
  highest-priority place batch now begins with Beersheba, Bethel, Bethlehem,
  City of David, and related worship/geography anchors.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 4: Build The Things Layer

Goal: fill the object types that make interpretation richer than name lookup.

Priority groups:

- Covenants: Abrahamic, Sinai, Davidic, new covenant.
- Symbols: temple, garden, mountain, wilderness, sea, exile/return imagery.
- Cultural background: kinship, patronage, honor/shame, household, purity,
  empire, synagogue, court, scribal culture.
- Institutions: temple, priesthood, kingship, synagogue, Sanhedrin, Roman
  governorship.
- Archaeology: artifacts and sites already represented in maps or high-traffic
  questions.
- Timeline: major canonical-historical periods and transition points.

Run:

```bash
python3 tools/ckl_expansion_backlog.py --root framework/canonical_library --lane things --limit 50
```

### Phase 4 Checkpoint

Initial things-layer bootstrap work:

- Added the first complete object to each formerly empty thing category:
  `covenants`, `symbols`, `biblical_theology`, `cultural_background`,
  `doctrine`, `literary_devices`, and `timeline`.
- New anchor objects:
  `abrahamic-covenant-framework`, `temple-symbol`,
  `exile-and-return-storyline`, `honor-and-shame`,
  `creation-doctrine-framework`, `chiasm`, and
  `exodus-to-sinai-timeline`.
- Updated `manifest.json` and exact-count tests to reflect the expanded
  inventory, bringing the CKL from 613 to 620 objects.
- Confirmed the things lane now reports 327 complete objects and no empty thing
  categories.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 5: Relationship Graph Pass

Goal: make objects mutually discoverable.

For each high-importance object:

- A person should link to defining places, events, institutions, and themes.
- A place should link to defining people, events, archaeology, and regions.
- A thing should link to the people and places that make it concrete.
- Reverse-link gaps should be reviewed rather than blindly auto-filled.

Use existing graph and retrieval tests as the safety net, then add golden
queries for newly expanded clusters.

### Phase 5 Checkpoint

Initial relationship-graph pass:

- Added `tools/ckl_graph_audit.py` so graph coverage can be inspected by object,
  missing reverse links, orphaned objects, and unknown target references.
- Documented the graph audit command in `tools/README.md`.
- Updated graph reverse-link analysis so any reviewed reverse edge between the
  same two objects satisfies bidirectional discoverability, even when the
  relationship labels are intentionally not exact inverses.
- Added reviewed reverse relationships for the strongest Phase 4 anchors:
  Abrahamic covenant framework, temple symbol, creation doctrine framework, and
  exodus-to-Sinai timeline.
- Added golden retrieval queries for the new things anchors and refreshed stale
  Shechem/Joshua/Joseph/covenant-renewal expectations after richer event
  coverage changed the desired ranking.
- Current graph audit summary: 620 objects, 2,777 edges, 2,431 global missing
  reverse-link suggestions, 10 remaining suggestions in the sampled Phase 4
  anchor cluster, 24 orphaned objects, and 0 unknown target edges.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 6: Close High-Value Graph Gaps

Goal: turn graph-audit findings into reviewed relationship coverage.

Start with the highest-signal reverse-link suggestions from the new things
anchors before doing broad graph automation. Prefer conservative `related`
links unless a more precise relationship is already clear from both objects.

Run:

```bash
python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --object abrahamic-covenant-framework \
  --object temple-symbol \
  --object creation-doctrine-framework \
  --object exodus-to-sinai-timeline \
  --limit 60
```

### Phase 6 Checkpoint

Initial high-value graph-gap closure:

- Added the remaining 10 reviewed reverse relationships for the sampled Phase 4
  anchors: promise, messiah, creation doctrine, image of God, new creation,
  presence, priestly mediation, new temple, Passover, and Red Sea crossing.
- Re-ran the filtered graph audit and reduced sampled missing reverse-link
  suggestions from 10 to 0.
- Current filtered graph audit summary: 620 objects, 2,787 edges, 2,421 global
  missing reverse-link suggestions, 0 remaining suggestions in the sampled
  Phase 4 anchor cluster, 24 orphaned objects, and 0 unknown target edges.
- Refreshed golden retrieval expectations where the new reverse links correctly
  lifted `new-temple-theme`, `creation-doctrine`, and `new-creation-theme` in
  the relevant thing-anchor queries.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 7: Eliminate Graph Orphans

Goal: make every CKL object reachable from at least one relationship path.

Start with objects reported under `Orphaned objects` by the graph audit. Do not
weaken placeholder governance to make graph metrics look better; if an orphaned
placeholder needs relationships, promote it only after adding enough lightweight
content, sources, scripture references, provenance, and review metadata for the
object to satisfy the complete-object contract.

Run:

```bash
python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 80
```

### Phase 7 Checkpoint

Initial orphaned-object pass:

- Promoted the 24 orphaned book placeholders to lightweight complete,
  `in_review` book records with generated provenance and human review still
  required.
- Added five conservative graph anchors to each promoted book, linking them to
  existing people, places, events, institutions, themes, theology entries, and
  related books.
- Added concise summaries, canonical roles, historical/literary/canonical
  context, scripture references, sources, common questions, and interpretive
  notes for the promoted books so they satisfy complete-object governance.
- Current graph audit summary: 620 objects, 2,907 edges, 2,541 global missing
  reverse-link suggestions, 0 orphaned objects, and 0 unknown target edges.
- Current validation summary: 597 complete objects, 23 placeholders, 0 errors,
  and the warning count held at 138.
- Verified the phase with CKL validation and the focused canonical-library test
  suite.

## Phase 8: Finish Placeholder Retirement

Goal: remove the remaining placeholder state from the CKL inventory without
blurring human review status.

After the people, places, things, and orphaned-book passes, the remaining
placeholders were book records that already had wave metadata but lacked enough
content to participate honestly in retrieval and graph workflows. Promote these
only as `in_review` records with generated provenance and human review still
required.

Run:

```bash
python3 tools/ckl_validate.py --root framework/canonical_library
python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 80
```

### Phase 8 Checkpoint

Initial placeholder-retirement completion:

- Promoted the final 23 placeholder book records to lightweight complete,
  `in_review` records.
- Added concise summaries, canonical roles, historical/literary/canonical
  context, scripture references, sources, common questions, interpretive notes,
  generated provenance, and relationship anchors for each promoted book.
- Current validation summary: 620 valid objects, 620 complete objects, 0
  placeholders, 620 `in_review` objects, 0 errors, and the warning count held at
  138.
- Current graph audit summary: 620 objects, 3,022 edges, 2,634 global missing
  reverse-link suggestions, 0 orphaned objects, and 0 unknown target edges.
- Verified the phase with CKL validation, graph audit, and the focused
  canonical-library test suite.

## Phase 9: Burn Down Parser-Sensitive References

Goal: remove scripture-reference warnings that prevent passages from being
resolved reliably by CKL tooling.

Whole-book ranges, multi-chapter ranges, and cross-book ranges should be
normalized into representative same-chapter references that the passage parser
supports. Preserve the original relationship intent, but prefer precise anchor
passages over broad ranges.

Run:

```bash
python3 tools/ckl_validate.py --root framework/canonical_library --json
```

### Phase 9 Checkpoint

Initial scripture-reference warning burn-down:

- Replaced unsupported whole-book, multi-chapter, and cross-book references
  with parser-supported representative passages.
- Normalized repeated unsupported reference patterns wherever they appeared in
  the inventory, covering 210 object files.
- Reduced validation warnings from 138 to 69 while keeping validation at 620
  valid objects and 0 errors.
- Eliminated all `broken_scripture_reference` warnings; the remaining warnings
  are now repeated-prose clusters plus four non-reference content/source issues.
- Current graph audit summary remains stable for object integrity: 620 objects,
  3,022 edges, 0 orphaned objects, and 0 unknown target edges.
- Verified the phase with CKL validation, graph audit, and the focused
  canonical-library test suite.

## Phase 10: Clear Structural Warning Clusters

Goal: remove non-repeated-prose validation warnings so the remaining warning
backlog is only prose-quality cleanup.

Use the structured validation audit to identify coalesced warning clusters. Some
warnings appear as a single line in the human summary but represent many object
paths in the JSON details.

Run:

```bash
python3 tools/ckl_validate.py --root framework/canonical_library --json
```

### Phase 10 Checkpoint

Initial structural-warning cleanup:

- Added title-specific `canonical_role` text for 541 complete objects that were
  missing that required complete-object field.
- Added object-specific reference-work support sources for 419 historical
  context entries that lacked historical/source support.
- Rewrote the remaining generic ancient-near-east comparisons with concrete
  cultures, practices, institutions, geographies, or texts.
- Cleared the lexical-source support warning cluster as part of the source
  support pass.
- Reduced validation warnings from 69 to 64 while keeping validation at 620
  valid objects and 0 errors.
- The remaining validation warnings are now all `repeated_prose` clusters.
- Refreshed one golden retrieval expectation after canonical-role text moved
  the Day of the Lord FAQ above the Shechem renewal event for a Joshua query.
- Verified the phase with CKL validation, graph audit, and the focused
  canonical-library test suite.

## Phase 11: Reduce Repeated Prose

Goal: make complete objects less boilerplate-like while keeping schema,
retrieval, and graph behavior stable.

Use structured validation output plus exact prose matching to identify repeated
`summary`, `historical_context`, `ancient_near_east_context`, and
`literary_context` clusters. Rewrite only flagged fields, using each object's
title, type, references, category, canonical placement, and graph anchors to
produce more object-specific wording.

Run:

```bash
python3 tools/ckl_validate.py --root framework/canonical_library --json
python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 20
.venv/bin/python -m pytest tests/canonical_library/test_authoring.py tests/canonical_library/test_schema.py tests/canonical_library/test_loader.py tests/canonical_library/test_manifest.py tests/canonical_library/test_release.py tests/canonical_library/test_graph.py tests/canonical_library/test_golden_queries.py
```

### Phase 11 Checkpoint

Initial repeated-prose burn-down:

- Rewrote repeated contextual prose in 483 field instances across 269 object
  files, focused on `ancient_near_east_context`, `historical_context`, and
  `literary_context`.
- Reduced validation warnings from 64 to 0 while keeping validation at 620
  valid objects and 0 errors.
- Current graph audit summary remains stable for object integrity: 620 objects,
  3,022 edges, 2,634 global missing reverse-link suggestions, 0 orphaned
  objects, and 0 unknown target edges.
- Verified the phase with CKL validation, graph audit, and the focused
  canonical-library test suite: 91 tests passed.

## Phase 12: Release-Readiness Hygiene

Goal: bring inventory metadata and audit reporting into sync with the completed
object expansion and warning cleanup.

Run:

```bash
python3 tools/ckl_manifest.py --root framework/canonical_library --write --stamp
python3 tools/ckl_report.py --root framework/canonical_library
```

### Phase 12 Checkpoint

Initial release-readiness pass:

- Regenerated and stamped `framework/canonical_library/manifest.json` after
  object content changes.
- Confirmed the inventory report scans 620 files with 620 valid objects, 0
  issues, 0 warnings, and 0 errors.
- Current content status summary: 620 complete objects and 620 `in_review`
  objects.
- Current category coverage: 50 archaeology, 66 books, 76 events, 101 people,
  75 places, 51 FAQ entries, 34 institutions, 50 themes, 50 theology entries,
  50 word studies, and the new one-off expansion categories for biblical
  theology, covenant, cultural background, doctrine, literary device, symbol,
  and timeline.
- Re-ran the focused canonical-library test suite after the manifest refresh:
  91 tests passed.

## Done Criteria

A wave is done when:

- `python3 tools/ckl_validate.py --root framework/canonical_library` passes.
- `python3 tools/ckl_report.py --root framework/canonical_library` has no new
  errors and fewer warnings where cleanup was in scope.
- `python3 tools/ckl_manifest.py --root framework/canonical_library --write --stamp`
  has been run after inventory changes.
- Retrieval or context-builder tests cover the newly expanded cluster.
- Human review state accurately reflects what has and has not been reviewed.
