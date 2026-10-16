# NE-6 Physical Identification and Display Safety

## Reader contract

The physical geography panel reports authored map records and their passage links. It presents source fields when available: original map ID, place or route name, ancient and modern names, region or territory, period, original relation type, passage association, identification status and confidence, dispute, bibliography, and related passages. Missing details stay missing.

Three claims are kept separate:

- A passage names or describes a place.
- A source catalog stores a point or geometry for that record.
- A biblical place has been identified with enough confidence for precise physical display.

The first two do not establish the third. Stored coordinates and geometry remain in the projection as source metadata, but the reader uses them only when the existing projection returns `coordinates_displayable: true` or `geometry_displayable: true`. When a record is withheld, the detail view gives the authored status and the projection's reason. It does not print stored numeric coordinate values.

The projection keeps `geography_kind`, `place_identification_confidence`, `stored_coordinates`, `coordinates_displayable`, `coordinate_display_reason`, `stored_geometry`, `geometry_displayable`, and `geometry_display_reason`. Existing strict checks for valid coordinate pairs, identified physical locations, disputed identifications, and identified routes remain in force. No name geocoding or coordinate synthesis is used. A map action for a withheld point opens the general Maps browser and does not request a precise focus.

## Database review and geographic pilots

The existing study database configured through `BHF_STUDY_DB_PATH` was used without rebuilding, migration, or writes. The live API and Firefox test verified the following:

| Pilot | Observed source data | Reader treatment |
| --- | --- | --- |
| Genesis 2 | Eden map record `openbible-af3daeb`, linked to Genesis 2:8, 2:10, and 2:15; garden evidence and rivers remain in their respective source records. | Eden stays inspectable with unknown physical-identification confidence and no map point. Garden and river records retain their own authored passages and relations. |
| Genesis 3 | Eden remains physically unidentified; a cherubim evidence record qualifies under the authored sacred-space guarding rule. | Cherubim is shown as literary/sacred-space evidence, separate from a physical Eden site. |
| Genesis 6 | Sons-of-God interpretation record remains disputed; no physical map record is derived from it. | Preserve the recorded interpretive options and dispute; do not make a site. |
| Deuteronomy 32 | Passage-linked map names and textual-witness evidence remain in the projection; physical identification is not established by the catalog links. | Retain textual witnesses; do not impose a settled cosmic territorial system on nations language. |
| Psalm 82 | Explicit assembly-language evidence and comparative Ugaritic evidence qualify as separate authored roles. | Label the biblical assembly-language and ancient comparison separately; no literal heavenly map. |
| Exodus 3 | Midian and Horeb/Sinai are represented as physical-geography records; the presence record is conceptual evidence. Horeb/Sinai identification remains uncertain. | Preserve the physical/conceptual distinction. No passage-specific sacred-space evidence was found for this passage; it remains a CKL curation gap. |
| Acts 7 | `maps:openbible-a012705` has an explicit Acts 7:19 link and stored source coordinates, but physical identification confidence is unknown. | Keep the item and provenance; withhold coordinate display and precise map focus. |
| Joshua 1 | `maps:openbible-a1cb244` (Negeb) has an explicit Joshua 1:4 link and stored source metadata, but physical identification confidence is unknown. | Keep the recovered reference and provenance; withhold coordinate display and precise map focus. |

The Acts 7 and Joshua 1 explicit-reference records are retrieved additively by Narrative Explorer's existing `include_reference_matches=True` path. The shared Maps resolver was not broadened. A record returned by Explorer but absent from Maps' passage result receives a not-found acknowledgment and a general Maps fallback.

## Controls and data gaps

Projection tests cover an explicitly identified physical point as a synthetic test fixture, a verified route geometry test fixture, a route with geometry but no established identification, an unidentified place, an invalid latitude/longitude pair, and a conceptual record carrying no reader-visible geometry. The synthetic point fixture is test-only and is not CKL or authoritative geographic evidence.

The reviewed map catalog contains stored representative points for some uncertain records, including Eden, and one route record. The current source set did not provide a passage-linked, strictly displayable physical target suitable for a positive Selenium selection test. The route's stored geometry does not carry the required route-identification status, so Explorer withholds it. These are present-source limitations; NE-6 does not upgrade them.

General historical and political layers remain source-defined Maps context. The current Explorer projection does not have a passage-specific historical/political source contract that would justify promoting such a layer to an event or place record. Uncertain reconstructed borders are not shown as surveyed modern boundaries.

## Verification boundary

Live map resolver behavior was verified for the required Acts 7 and Joshua 1 lookups and the browser pilots documented in `04-map-focus-and-database-validation.md`. The NE-A1 audit enumerated passage links across the corpus; it did not verify live resolver results for every chapter. No claim of complete map-service coverage across 1,189 chapters is made. The 330 unclassified CKL records and 132 no-material chapters remain separate coverage matters.
