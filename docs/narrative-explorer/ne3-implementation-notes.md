# Narrative Explorer NE-3 implementation notes

## Route contract

NE-3 registers one endpoint:

```text
GET /api/narrative-explorer/v1/passages/{book}/{chapter}
    ?verse_start={integer}&verse_end={integer}
```

Both verse parameters are optional. `verse_end` requires `verse_start`; invalid books or chapters return a safe `404`, and invalid verse scopes return a safe `422`. A CKL lookup that cannot initialize or complete returns `503` with `{"error":"canonical_lookup_unavailable"}`. Unexpected projection failures return a generic `500` envelope. Provider messages, stack traces, paths, and configuration are not returned.

Successful responses are produced by `bhf_agent.presentation.narrative_explorer.project_narrative_explorer(...)` and validated with `validate_projection(...)`. They retain schema version `1.0` and include `schema_version`, `passage`, `coverage`, `sections`, `items`, `connections`, and `navigation`.

## Retrieval and scope

- **CKL:** Uses the configured canonical repository and its existing `retrieve_by_scripture_reference` implementation. Any existing SQLite index is opened read-only; a missing or stale index falls back to the committed JSON repository. Even if the environment requests a rebuild, the GET path falls back to JSON and never builds an index. The per-route service retains one loaded library instance. The request limit is derived from the full loaded inventory, not a fixed small result cap; each parent, claim, and evidence record is then filtered by the NE-2 passage applicability logic. An empty successful lookup is represented as `not_represented`. An unavailable provider or failed retrieval aborts the request instead of appearing as an empty, complete CKL result.
- **Maps:** Uses `resolve_places_for_passage` and `get_map_routes_for_passage` from `bhf_web.map_service`. Chapter lookups use a full-chapter reference window; verse lookups use the requested bounds. Results retain their stored IDs, anchors, coordinates, periods, identification status, and source metadata. NE-2 performs the final anchor applicability check, so a name match without a supported passage anchor does not become a projected item. Text-first resolver results are marked partial because the existing resolver can skip anchor-only matches when it finds a name in the text. Place and route subqueries fail independently.
- **Archaeology:** Uses `ArchaeologyService.for_passage` against the already-current study database. Its 25-record bound is exposed as partial when reached, with `remaining_archaeology_items` named as missing. CKL literary and manuscript evidence remains in the CKL domain and is unaffected by an empty archaeology lookup.
- **Study database:** Map and archaeology access first call `require_current_study_database`; they do not initialize a missing or stale database. These source domains are independent. A failed map or archaeology query is `unknown` with `failed` query status while successfully retrieved domains remain available.

CKL I/O is cached within the route service, so repeated passages on the same application worker do not reload the corpus.

## Navigation audit

The target IDs are preserved in every generated navigation destination. The destinations resolve against routes already registered by BHF:

| Target | Destination | Resolution |
| --- | --- | --- |
| Passage | `/api/study/companion-context` with book/chapter/verse query fields | Existing passage-context route |
| CKL object | `/api/canonical/objects/{object_id}` | Direct object detail route |
| Map place | `/api/maps/biblical-places` | Collection route; `selection_required: true` tells the client to select the item using `target_id` |
| Map route | `/api/maps/routes/{route_id}.kml` | Existing route-specific KML export preserves the route ID; a client that wants to display it in its own map still selects the returned route |
| Archaeology item | `/api/archaeology/items/{item_id}` | Direct item detail route |
| Source reference | No navigation destination is emitted | Source IDs and any bibliographic metadata remain on the projected item; NE-2 has no source-detail route contract |

The optional `selection_required` boolean is an additive field on NE-2 navigation destinations. It is emitted only when true, leaving existing projection serialization unchanged. It marks collection/KML targets that need client-side item selection and does not claim a collection URL is an item-detail page. No frontend route was introduced.

NE-4/NE-5 should define a client selection contract for map-place and map-route items and a source-detail destination only if BHF adds an authoritative source route. Those changes are outside NE-3.

## Read-only and compatibility boundaries

The default CKL provider uses an existing SQLite index in read-only mode when configured and current; its missing/stale fallback reads the committed JSON repository without creating or rebuilding an index. Map and archaeology helpers are called only after a read-only current-schema preflight. The route does not call a model provider, commentary renderer, Companion narration path, CKL editor, personal-study repository, or write/migration helper. No frontend, Ask BHF, Commentary, reader, source record, or existing route response was changed. The only schema addition is the optional navigation selection marker described above.

The study database used for local production-default measurements had the same SHA-256 before and after retrieval: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`. Integration tests use injected CKL, map, and archaeology providers; legacy web tests run with `BHF_DATA_DIR` directed to `/tmp/bhf-ne3-test-data`.

## Measured local pilot cost

Measurements use the real committed CKL JSON corpus and the local current study database. Elapsed time is one local request per chapter, including initial CKL load on the first request. Response size is serialized JSON bytes. These are observations, not performance targets.

| Pilot | Elapsed time | Response bytes | Items | Connections |
| --- | ---: | ---: | ---: | ---: |
| Genesis 1 | 32,073 ms | 260,088 | 34 | 134 |
| Genesis 2 | 3,924 ms | 420,593 | 44 | 129 |
| Genesis 3 | 3,028 ms | 154,071 | 23 | 61 |
| Genesis 6 | 3,564 ms | 246,897 | 26 | 56 |
| Deuteronomy 32 | 5,465 ms | 459,990 | 29 | 82 |
| Psalm 82 | 2,274 ms | 44,556 | 6 | 15 |
| Exodus 3 | 5,085 ms | 562,061 | 36 | 188 |

The cold request is dominated by loading and indexing the complete CKL JSON inventory. Warm passage requests in this sample range from about 2.3 to 5.5 seconds. A bounded read-only follow-up optimization is to use the current indexed CKL SQLite repository when it is already present and passes the existing schema/fingerprint checks, with a JSON fallback and no rebuild path. NE-3 adds no persistent cache and does not cap CKL candidates.

## Validation record

The NE-3 integration tests cover Genesis 1, 2, 3, and 6; Deuteronomy 32; Psalm 82; and Exodus 3 at chapter and verse-range scope. They validate every serialized projection with the NE-2 validator, check repeated-request determinism, and cover independent source failures, empty CKL success, CKL unavailability, large CKL payloads, cap disclosure, unresolved source IDs, personal-study exclusion, and route registration. The focused projection suite also covers unknown relationships, reciprocal-edge integrity, missing map identification confidence, and coordinates without established physical identification.

See the final NE-3 branch test and integrity report for the complete test totals and repository state.
