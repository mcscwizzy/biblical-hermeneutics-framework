# NE-6R1 — Maps Payload and API Contract

## Intentional response change

`GET /api/maps/places-for-passage` now accepts `include_related_passages` as an explicit boolean query parameter. Its default remains `true`, preserving the existing full response shape for API consumers. The exported `loadPlacesForPassage()` helper also retains that default when existing callers omit the option; only the Maps passage panel passes `includeRelatedPassages: false` for its initial lookup.

Compact mode keeps the complete marker object except for the expanded `related_passages` object. Stable record IDs, display names, aliases, coordinates, confidence and identification metadata, source attribution, periods, current passage match, rationale, counts, and `related_references` remain in the initial response. There is no hard-coded relationship or result-count limit.

Passage mode also uses the explicit `/api/maps/catalog?include_records=false` catalog mode because it needs only timeline period metadata before drawing passage markers. That response contains the unchanged `timeline` object and omits the browse record arrays. The default catalog response remains complete; Maps browse mode and offline-pack generation continue to request the full catalog. Period options and canonical-period metadata are preserved in the timeline-only response.

## Lazy detail loading

When a user selects a marker whose complete relationships were not loaded, Maps calls the existing `/api/maps/related-passages-for-place` endpoint for that exact stable place ID and historical-period context. It renders the returned complete grouped passages using the existing detail renderer. The details are retained in a page-memory map for repeat selections in that session; the complete graph is not copied to local storage.

The detail panel exposes an accessible loading status. A failed request identifies the details as incomplete and offers retry; it does not claim there are no related passages. The retry clears only the failed in-memory detail state and issues the same exact-ID request again. A browser fixture forced the first detail response to fail and verified the retry fetched and rendered the full relationship object. A Service Worker cached result is labeled as cached/offline, and the online retry uses the network-first map policy.

## Exactness check

The original full John 2 response and the compact-plus-detail result were compared for all 69 marker records. Every marker's returned `related_passages` object from the existing place-detail endpoint exactly equaled its embedded baseline object. Marker IDs, source names/URLs, authored reference IDs, relationship types, confidence, identification status, periods, coordinates, and other base marker fields were identical. The source study database remains untouched.

## Route and uncertainty behavior

Route response shape and geometry handling are unchanged. The compact query affects only passage-place relationship expansion. No route/place identification status, confidence, coordinates, geometry, cosmic-geography classification, or uncertainty state is recomputed or promoted by this change.

## Compatibility

Callers that omit `include_related_passages` continue to receive the existing full object. The Explorer panel opts into compact mode explicitly. Legacy Maps, map catalog, search, route, archaeology, KML, and Narrative Explorer projections continue to use their existing contracts. The Acts 7 additive reference retrieval used by Narrative Explorer remains separate and unchanged.
