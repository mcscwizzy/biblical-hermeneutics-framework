# Narrative Explorer NE-5A classification audit

**Status:** Exodus 3 is an evidence-coverage gap in CKL, not a projection defect. The cosmic/sacred-space section remains empty for Exodus 3 and its state remains `unknown` while the relevant map lookup is partial. No CKL records, claims, evidence, or commentary were edited.

## Scope and baseline

NE-5A is based on NE-4 commit `8c1ae5643ebe679633cb7b5cb7616b3c13bf4279`, on the stacked feature branch `fix/narrative-explorer-ne5a-classification`. The latest fetched `origin/master` was `b9812fd0236cc2341fd4b777fe92b009dfb05c8b`; NE-4 was not merged into master at the time of the audit. NE-1 through NE-4 ancestry remains intact.

The six section identifiers and schema version `1.0` are unchanged. Classification policy is versioned in code as `SECTION_ASSIGNMENT_POLICY_VERSION = "ne5a-1"`. A section is a presentation lens over an authored record; assignment does not alter CKL identity, evidence kind, claims, or source relationships.

## Exodus 3 finding

The read-only SQLite CKL repository returned 28 passage-eligible source objects for `Exodus 3`; the projection contained 33 items. Reviewing the eligible objects and their nested records found no authored passage-specific claim or evidence item establishing sacred space for Exodus 3:1–6.

| Existing record | Passage support | What it establishes | Decision |
| --- | --- | --- | --- |
| `ckl:presence-theme` (`theme`) | Parent anchor Exodus 3:1–6; no passage-eligible nested claims or evidence | General Presence Theme membership | Keep in `themes_biblical_connections` |
| `ckl:divine-presence` (`theology`) | Parent anchor Exodus 3:1–6; no passage-eligible nested claims or evidence | General Divine Presence topic membership | Keep in `themes_biblical_connections` |
| Burning bush event | Passage-eligible parent record; no authored nested sacred-space claim/evidence | Event identity and narrative context | Keep in its supported narrative/passage sections |
| Mount Sinai place | Passage-eligible physical-place record | A physical place with identification uncertainty | Keep in `biblical_geography`; do not recast as a heavenly/cosmic relation |
| Exodus 3 map candidates | Text-first result was partial; 12 raw place candidates, 3 directly anchored projected items | Physical place records, including uncertain Horeb identification | No authored `sacred_space` map record was returned |
| Archaeology lookup | Completed, zero eligible records | No passage-eligible archaeology result in this lookup | Completed empty lookup, not a retrieval failure |

The CKL records' titles, general descriptions, broad related-object links, and non-passage-specific interpretive notes do not establish an Exodus 3 sacred-space relation. The explicit `sacred_space` map classification is also absent for this passage. The evidence supports conclusion **3: CKL has no sufficiently specific authored evidence for the Exodus 3 cosmic/sacred-space section**. It does not support conclusions 1 or 2.

The API therefore keeps Presence Theme and Divine Presence in Themes & Biblical Connections and leaves Divine Council & Cosmic Geography empty with `unknown` coverage because passage-map coverage is incomplete. This state means passage-specific availability could not be established from all configured sources. It does not claim that sacred-space evidence is absent from Scripture or scholarship. This is not a frontend rendering defect. A separate CKL curation transaction may add evidence only after an author supplies a scoped claim/evidence record and its source support.

### Reproduction

The source-backed regression is `test_exodus_3_does_not_promote_presence_or_physical_places_to_sacred_space` in `tests/test_narrative_explorer_projection.py`. The API-level check is `test_exodus_3_keeps_physical_places_uncertainty_and_conceptual_language_separate` in `tests/test_narrative_explorer_api.py`. Both assert that the two Presence records remain in Themes, neither enters the cosmic section, the cosmic section has no item IDs, and its state is `unknown`. The API test uses the read-only CKL fixture and verifies physical-place identification uncertainty and coordinate safety.

To repeat the test-backed audit:

```sh
.venv/bin/python -m pytest -q \
  tests/test_narrative_explorer_projection.py::test_exodus_3_does_not_promote_presence_or_physical_places_to_sacred_space \
  tests/test_narrative_explorer_api.py::test_exodus_3_keeps_physical_places_uncertainty_and_conceptual_language_separate
```

For the production-shaped local lookup, the route uses `SQLiteCanonicalRepository` in read-only mode and its fingerprint/stale-index check before passage retrieval. It does not rebuild the index. The query is `retrieve_by_scripture_reference("Exodus 3", limit=687, include_placeholders=True)`; inspect the resulting records' `scripture_references`, `claims`, `evidence_items`, and `interpretive_notes`, then compare them with the projected section IDs and domain coverage. The recorded result was 28 eligible source objects, 33 projected items, zero qualifying sacred-space CKL evidence items, no sacred-space map record, and zero eligible archaeology records.

## Mapping defects and corrections

1. **Generic worldview evidence was sent to the cosmic section.** `_child_sections` treated every `worldview-concept` as divine-council/cosmic-geography evidence. This put ordinary Genesis 1 worldview observations, Eden/serpent records, and Genesis 6 violence there based on a broad evidence type. Generic `worldview-concept` now maps to Themes & Biblical Connections. Only the small, explicit policy below can add the cosmic lens.
2. **A typed sacred-space map record lacked the cosmic lens.** An external map result with its authored `geography_kind="sacred_space"` was previously assigned only to Biblical Geography. Such a record now joins Biblical Geography and Divine Council & Cosmic Geography. It remains conceptual and is not projected as physical map geometry.
3. **Cosmic section coverage omitted maps.** Its coverage domains were CKL alone even though explicit sacred-space records can come from maps. The section now reports both CKL and passage maps. A failed/partial map lookup cannot be hidden by a successful CKL lookup.
4. **Section state aggregation confused complete-empty lookups with incomplete coverage.** A section containing items was called partial whenever a required domain had zero records. It is now `available` when every required lookup completed without missing subdomains, even if one completed lookup found no eligible item. It is `partial` when an input lookup did not complete or reports missing subdomains. An empty section is `not_represented` only when every required lookup completed and no passage-eligible item exists; otherwise it is `unknown`.
5. **Passage-eligible but unclassified CKL material is not declared complete for a specialized section.** Such an item remains in the response with its stable CKL identity and an empty `section_ids` list; because CKL did return an eligible record while the specialized section has no item, that section remains `unknown`, not `not_represented`. Regression coverage protects this distinction.

These are presentation classifications only. No new API fields or schema version were added. Stable item IDs remain derived from CKL parent ID, record kind, and local child ID. Multi-section membership is stored on one projected item; section lists refer to that same ID. Output and section ordering remain deterministic.

## Complete section assignment policy (`ne5a-1`)

All CKL child assignments require a passage-applicable authored anchor. Ineligible children do not enter the projection. Parent objects use their original CKL `type`; child items retain their original record kind. A child with a specialized rule must also match its exact parent ID, local child ID, authored evidence type, and an eligible anchor relationship listed below.

| Authored record kind / type | Presentation section(s) |
| --- | --- |
| Parent `theme`, `theology`, or `doctrine` | `themes_biblical_connections` |
| Parent `person`, `people_group`, `group`, or `institution` | `people_events_relationships` |
| Parent `place` | `biblical_geography` |
| Parent `event` or `timeline` | `biblical_narrative`, `people_events_relationships` |
| Parent `archaeology` | `archaeology_ancient_history` |
| Parent `book` | `biblical_narrative` |
| Other parent type | No section from the parent type alone |
| Claim `biblical_text`, `textual`, or `textual_observation` | `biblical_narrative` |
| Claim `historical_cultural`, `historical`, `social`, or `political` | `archaeology_ancient_history` |
| Claim `literary`, `composition`, or `rhetorical` | `biblical_narrative`, `themes_biblical_connections` |
| Other claim type under a theme/theology/doctrine parent | `themes_biblical_connections` |
| Evidence `worldview-concept` | `themes_biblical_connections` by default |
| Evidence `ancient-text`, `manuscript`, `artifact`, `archaeological-site`, `inscription`, `material-culture`, `primary-source`, `secondary-source`, or `historical-period` | `archaeology_ancient_history` |
| Evidence `geography-environment` | `biblical_geography` |
| Evidence `historical-event`, `person`, `people-group`, or `institution` | `people_events_relationships` |
| Evidence `literary-convention` | `biblical_narrative`, `themes_biblical_connections` |
| Other evidence type | No section from evidence type alone |
| Interpretive note `ancient_near_east_context`, `second_temple_context`, or `historical_context` | `archaeology_ancient_history` |
| Interpretive note `canonical_connection`, `later_reception`, or `literary_observation` | `biblical_narrative`, `themes_biblical_connections` |
| Interpretive note `textual_observation` | `biblical_narrative` |
| Interpretive note `theological_interpretation` or `interpretive_caution` | `themes_biblical_connections` |
| External archaeology result | `archaeology_ancient_history` |
| External map with authored `geography_kind="sacred_space"` | `biblical_geography`, `divine_council_cosmic_geography` |
| External map with another known geography kind | `biblical_geography` |
| External map with unknown geography kind and marker type `manuscript`, `historical_layer`, or `political_context` | `archaeology_ancient_history` |
| External map without one of the authored typed cases above | No section from title or prose matching |

A child under a `theme` parent also receives the Themes lens; its claim/evidence/note type can add another independently typed section. Parent objects with passage-eligible children are assigned the union of their own type lens and their eligible children's sections. This is a presentation union: each child still has one authoritative source object and one stable projected ID.

The six section identifiers are `biblical_narrative`, `archaeology_ancient_history`, `biblical_geography`, `divine_council_cosmic_geography`, `themes_biblical_connections`, and `people_events_relationships`. Generic title, summary, generated prose, shared vocabulary, or related-object text is never searched to assign a specialized section.

### Explicit CKL specialized evidence rules

These mappings add `divine_council_cosmic_geography` on top of the ordinary evidence-type lens; they do not alter the CKL record or state a new claim.

| Source object ID | Child ID / record kind | Eligibility and authored basis | Resulting memberships | Preserved source/uncertainty |
| --- | --- | --- | --- | --- |
| `genesis` | `g2-garden-planting-presence` / evidence | `geography-environment`; direct Genesis 2:8–10 anchor. The description expressly says Eden-as-sacred-space or temple is interpretation, not explicit identification. | `biblical_geography`, `divine_council_cosmic_geography` | `genesis-1-50`, `sarna-genesis`, `g1-amit-eden-exposition`; `plausible`; `interpretive_uncertainty` |
| `genesis` | `g3-cherubim-biblical-sacred-space-context` / evidence | `worldview-concept`; direct Genesis 3:24 anchor. Authored guarding role and later sanctuary context; no physical appearance claim. | `themes_biblical_connections`, `divine_council_cosmic_geography` | `genesis-1-50`, `g1-exodus-text`, `g1-kings-text`, `g1-lexham-cherubim`; `strong_consensus`; `minor_scholarly_disagreement` |
| `mesopotamian-creation-and-flood-comparisons` | `enuma-elish-cosmic-ordering-comparison` / evidence | `ancient-text`; comparative Genesis 1:1–2:3 anchor; CKL explicitly limits this to comparison and does not claim direct borrowing. | `archaeology_ancient_history`, `divine_council_cosmic_geography` | `lambert-babylonian-creation-2013`, `sarna-genesis-comparison`; `probable`; `major_scholarly_disagreement` |
| `ancient-divine-assembly-imagery` | `psalm-82-assembly-language` / evidence | `worldview-concept`; direct Psalm 82:1–8 anchor; explicit assembly-language observation with other interpretations retained. | `themes_biblical_connections`, `divine_council_cosmic_geography` | `psalm-82-hebrew-text`, `smith-origins-biblical-monotheism-2001`, `lewis-origin-character-god-2020`; `textually_explicit`; `interpretive_uncertainty` |
| `ancient-divine-assembly-imagery` | `ugaritic-council-comparison` / evidence | `ancient-text`; comparative Psalm 82 anchor; authored note says Ugaritic material is comparative evidence, not direct evidence for the biblical author/audience. | `archaeology_ancient_history`, `divine_council_cosmic_geography` | `smith-ugaritic-baal-cycle-1994`, `smith-origins-biblical-monotheism-2001`, `lewis-origin-character-god-2020`; `probable`; `major_scholarly_disagreement` |
| `genesis-flood-postflood-context` | `g6-sons-of-god-interpretive-positions` / evidence | `worldview-concept`; direct Genesis 6:1–4 anchor; the identity of the figures and reading remain disputed. | `themes_biblical_connections`, `divine_council_cosmic_geography` | `g2r2-local-genesis-1-50`, `g2r2-local-sarna-genesis`, `g2r2-local-hamilton-genesis-1-17`, `g2-doedens-sons-god`; `disputed`; `major_scholarly_disagreement` |

The stable projected ID for each child is `ckl:<source-object-id>#evidence:<child-id>`. Applicable passage anchors, source IDs, certainty, dispute status, and parent identity are copied from the source record. Repeated section membership does not duplicate an item. No new rule creates map coordinates. The Genesis 6 violence record is intentionally not in the specialized table: `g6-evil-intention-and-violence` remains a general theme, not cosmic evidence.

## Seven-passage regression and negative controls

| Passage | Source-backed result |
| --- | --- |
| Genesis 1 | The direct creation/worldview observation remains in Themes and out of the cosmic section. The Enuma Elish item is both comparative ancient-text context and cosmic/geography exploration; its comparative anchor, source IDs, probability, and major disagreement remain intact. |
| Genesis 2–3 | Direct Eden planting and the qualified sacred-space interpretation remain discoverable in Biblical Geography and the cosmic section. Cherubim guarding context is discoverable from Genesis 3:24. Eden's physical location remains unresolved; the serpent characterization does not become cosmic evidence. |
| Genesis 6 | The sons-of-God interpretations remain discoverable with disputed status. Violence remains a general theme, and no Genesis-wide book references are inherited as passage evidence. |
| Deuteronomy 32 | The `deuteronomy-32-8-manuscript-variant` remains under ancient history/textual evidence with `textual_variant` dispute status. Nations language alone does not add a territorial divine-council conclusion. |
| Psalm 82 | Direct assembly-language evidence and the Ugaritic comparison remain available in the cosmic section. The direct textual observation and comparative interpretation retain separate IDs, source ancestry, and dispute statuses. |
| Exodus 3 | Presence, Divine Presence, Burning Bush, and Mount Sinai remain in their supported existing sections; none is promoted to cosmic geography. The section remains empty/unknown as described above. |

Negative title-only controls cover general Presence, Divine Presence, Glory, Worship, Kingdom, Temple, Mountain, and the physical Mount Sinai place. Each remains in its authored broad topic/geography lens and out of the cosmic section absent a typed passage-specific relationship. Ordering and duplicate-ID assertions cover same-item multi-section membership.

## Coverage-state checks

- Domain lookup states retain the distinction between complete, partial, failed, and not-run. A completed lookup with no eligible item is `not_represented`, not `unknown`.
- A section with items and all required lookups complete is `available`, even if one completed lookup is empty. If a required lookup failed, was not run, is partial, or reports missing subdomains, an item-bearing section is `partial`.
- An empty section is `not_represented` only when each of its own required lookups completed and none returned passage-eligible items. If a lookup is incomplete, or a completed CKL query returned passage-eligible but unclassified material, the empty section remains `unknown`.
- Sections use their own source-domain list. A maps/archaeology failure does not erase available CKL items elsewhere; CKL availability does not make a map-dependent specialized section available.
- A partial upstream result cannot be presented as complete. The API shape has no new fields; existing query status, missing-subdomain, state, and source-domain fields carry this distinction.
- Empty cosmic coverage is only a statement about the configured passage lookups and current classification taxonomy. It is not a universal negative claim about Scripture or scholarship.

## Integrity boundaries

No CKL JSON, CKL manifest/fingerprint, SQLite file, generated commentary, commentary candidate state, frontend reader, feature flag, route contract, production configuration, map record, or archaeology record was changed. No CKL mutation or database rebuild was run. The reader, seven-passage pilot rendering, Study Companion navigation/history, and existing manual handoff remain outside the patch. The work is limited to deterministic presentation classification, its regression tests, and these audit/profile documents.
