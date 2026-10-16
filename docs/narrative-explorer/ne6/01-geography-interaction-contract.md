# NE-6 Geography Interaction Contract

**Status:** Approved design for implementation on `feat/narrative-explorer-ne6-geography`.
**Baseline:** NE-5C `b451428546b87b9cfb0912292f8e3906fa0e0803`, directly descended from NE-A2 `3d406b6256a6064a35e0e567c8a1304bf3cba2e8`.

## Purpose and architecture

NE-6 presents the evidence already available through the Narrative Explorer projection, Study Companion, and Maps panel. It does not add a reader, map engine, evidence database, geocoder, CKL claim, or global map resolver behavior. Narrative Explorer remains passage-scoped and disabled by default.

Every geography view keeps three questions separate:

1. **Physical geography:** what the current source record says about a place, region, route, period, and passage association.
2. **Identification:** how strongly the biblical place is identified with a physical site. A catalog coordinate is not itself this identification.
3. **Sacred or cosmic geography:** what an authored source supports about literary, symbolic, sacred-space, comparative, or theological interpretation. This is conceptual evidence and is never a map of heavenly realms.

## Physical record presentation

For eligible records, render only values actually present in the projected source record: original map/CKL ID; place or route name; ancient and modern names; region or territory; historical period; passage associations; original relation labels; identification status and confidence; dispute status; source metadata and bibliography; related passages; and supported navigation actions. Omit absent values without filling them from general knowledge.

Retain projection fields `geography_kind`, `place_identification_confidence`, `stored_coordinates`, `coordinates_displayable`, `coordinate_display_reason`, `stored_geometry`, `geometry_displayable`, and `geometry_display_reason`. The reader never renders stored coordinates or geometry while the corresponding displayability flag is false. Map focus and precise geometry use the projection's existing strict checks. No name-based coordinate inference or automatic geocoding is permitted.

Describe uncertainty in terms of the source record and displayability reason. Do not call representative catalog points established biblical sites. An unidentified place may still be shown as a source record and explained; its hidden coordinates do not become reader-visible.

## Map selection acknowledgment

A request to open Maps with a place or route target returns an optional acknowledgment with one status:

- `selected`: the requested ID was found in the loaded supported map layer and that exact item became the current Maps selection.
- `not_found`: supported map data loaded successfully but did not contain that ID.
- `unsupported`: the requested target kind cannot be selected by the current Maps controller/layer.
- `unavailable`: map data or the requested cache-backed data is unavailable, including offline absence.
- `failed`: map lookup or controller selection failed.

Opening or revealing Maps alone is never `selected`. The result carries requested kind/ID and, when selected, selected kind/ID so callers can verify identity. A missing/failed focus acknowledgment is surfaced accurately with an action to open the general Maps browser. Existing callers that do not request acknowledgment keep their existing return behavior. Existing passage-context and map-controller lifecycles remain in use.

NE-A2's `include_reference_matches=True` remains scoped to Narrative Explorer. The global Maps resolver is unchanged. When an explicitly linked record is returned by the Explorer but absent from Maps' loaded result, NE-6 reports the inability to select it; no global resolver expansion or false success is allowed.

## Cosmic geography presentation

Cosmic/sacred-space sections use only the current source-specific identity, evidence-type, and anchor-relation classification policy. Presentation may label the authored role as sacred-space interpretation, sacred-space guarding context, ancient cosmology comparison, explicit divine-assembly language, comparative divine-assembly material, or disputed divine-beings interpretation. A role appears only when the existing exact rule qualifies the record and applicable authored passage anchor. Titles and descriptions are not classification inputs.

Show source text, source-backed relationships, provenance, passage navigation, and authored cautions. Keep biblical textual statements, physical background, ancient comparisons, proposed symbolic readings, later biblical reception, later Jewish/Christian interpretation, and scholarly disagreement visibly distinct. Comparison does not establish borrowing. The presentation adds no doctrinal conclusion or heavenly map.

## Relationship navigation and history

Preserve stable IDs, source identifiers, and original edge labels. Display only authored links; retain their direction and do not infer reciprocal edges. Passage-to-place/source/related-passage and passage-to-sacred-space/evidence/authored-connection/biblical-text navigation is available only where those edges exist. The existing three-hop limit, breadcrumb/history rules, Back/Forward restoration, and return-to-origin passage selection and translation remain authoritative.

## Map, coverage, and offline behavior

Use existing historical-layer and political-context services only as general, source-defined map context where their current contracts permit. Never silently attach a general layer or reconstructed border to a passage-specific record. Document unsupported source types as an integration gap.

Preserve coverage values `available`, `partial`, `not_represented`, and `unknown`. An incomplete lookup cannot say coverage is complete. An empty completed lookup says only that this lookup returned no record; it does not prove absence from CKL or the world. No all-chapter resolver-completeness claim is introduced.

Do not fetch map data during ordinary reading while Explorer is inactive or load heavy map layers before explicit user action. Offline UI retains the evidence trail, distinguishes cached content from missing content, never reports an unverified selection, and offers retry when online. No persistent map cache is added. The feature flag remains OFF by default.

## Required pilot acceptance

- **Genesis 2:** retain Eden/garden/rivers source material and physical-identification uncertainty; never show an established Eden map marker.
- **Genesis 3:** show cherubim as qualified guarding/sacred-space evidence, separately from physical geography.
- **Genesis 6:** retain disputed sons-of-God interpretations; do not project a site.
- **Deuteronomy 32:** retain textual witnesses; do not settle nations language into a cosmic territorial system.
- **Psalm 82:** distinguish explicit assembly-language evidence from Ugaritic comparison; no heavenly map.
- **Exodus 3:** separate Midian/Horeb/Sinai physical evidence from Divine Presence themes; retain uncertain Horeb/Sinai identification and leave missing passage-specific sacred-space evidence as a CKL curation gap.
- **Acts 7:** preserve `openbible-a012705` and Acts 7:19 link; explain insufficient identification confidence and suppress stored coordinate display/focus.
- **Joshua 1:** preserve recovered Negeb passage link, uncertainty, and provenance.
- **Controls:** identified physical point, valid route, unidentified place, invalid coordinate pair, and conceptual record without geometry. Any absent verified point may appear only as an explicitly labeled synthetic renderer test fixture.

## Protected inputs and verification

CKL records, fingerprints, study DB/schema, source relationships, archives/manifests, other study features, Ask BHF prompts/principles, manual GPT handoff, and deployment settings are out of scope. No model calls or generated commentary.

The valid existing study database is accessed read-only by `BHF_STUDY_DB_PATH`; no rebuild, migration, or write is allowed. Verification records automated tests, actual Firefox/Selenium desktop and mobile viewport checks, accessibility semantics checked in the DOM versus actual assistive-technology coverage, request/render measurements, and any unavailable checks separately.
