# NE-6 Map Focus and Database Validation

## Study database diagnosis and read-only validation

The earlier local lookup raised `StudyDataError` because the isolated NE worktree did not contain its default `.bhf-data/study.sqlite`. `require_current_study_database` correctly rejected that missing file instead of creating or migrating it. The existing database in the original checkout was available, so integration checks explicitly set `BHF_STUDY_DB_PATH` to that file before importing the app.

The browser and API runs additionally set `BHF_STUDY_DB_READ_ONLY=1`. Connections to that configured study database use SQLite `mode=ro` and `PRAGMA query_only=ON`; `_ensure_schema` validates the existing schema and returns without DDL. This environment switch is scoped to the configured study DB and leaves normal default behavior unchanged.

| Check | Result |
| --- | --- |
| Configured file | `./.bhf-data/study.sqlite`, 3,416,064 bytes |
| Current database check | `require_current_study_database` passed; latest `schema_migrations.version` is 37 |
| SQLite integrity | `PRAGMA integrity_check` returned `ok` |
| Read-only guard | SQLite URI mode `ro`; query-only verification and attempted-DDL rejection passed in the disposable unit fixture |
| Protected DB identity | SHA-256 `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`; browser integration checks the digest before and after |
| Mutation policy | No rebuild, migration, schema change, or study DB write was performed |

The database's `PRAGMA user_version` is 0; the current application schema is tracked in `schema_migrations`, whose latest version is 37. The database uses its existing schema validation rather than `user_version` as the current-schema test.

## Actual Acts 7 and Joshua 1 retrieval

Live API/browser integration against the configured database confirmed:

- **Acts 7:** `maps:openbible-a012705` (OpenBible.info Nile record) retains its explicit Acts 7:19 passage link and stored coordinates as source metadata. Identification confidence is unknown, `coordinates_displayable` is false, and the reader withholds precise map display.
- **Joshua 1:** `maps:openbible-a1cb244` (Negeb) retains the recovered Joshua 1:4 passage link and source metadata. Identification confidence is unknown, `coordinates_displayable` is false, and precise map display is withheld.

Both records are retrieved through NE-A2's additive `include_reference_matches=True` path in the Explorer service. The legacy Maps resolver defaults are unchanged. If a retrieved explicit-reference item is absent from the loaded Maps results, Explorer does not change shared resolver behavior; it reports that the target was not found and offers general Maps.

## Acknowledgment outcomes

An acknowledgment is opt-in. Existing callers that omit `acknowledgeFocus` retain the prior `undefined` result. For acknowledged requests, the current map controller must load the exact target ID and confirm the corresponding selection. Panel visibility alone never produces `selected`.

| Status | Meaning in the current integration | Verification |
| --- | --- | --- |
| `selected` | Exact requested kind and ID are loaded, the existing controller focuses/selects that item, and the selected details are rendered. | Exact identity contract tested in the frontend helper suite. |
| `not_found` | Supported map lookup completed, but the requested ID was absent. The message says it was not selected and offers Browse maps. | Actual Firefox Maps panel with a nonexistent target. |
| `unsupported` | Target kind is outside the current selectable map layer, such as a historical layer. | Actual Firefox Maps panel. |
| `unavailable` | Required map data is absent while offline, including when no existing cache can satisfy the request. The message offers retry and Browse maps. | Firefox with offline state and rejected map requests. |
| `failed` | A lookup or controller could not confirm selection. The message says it was not selected and offers retry and Browse maps. | Firefox with rejected map requests; online retry is also recorded below. |

The actual online retry made fresh HTTP 200 requests for the catalog, passage places, and passage routes, but the existing MapPanel/controller still returned `failed` for the deliberately nonexistent test ID. The UI truthfully reports that no selection was confirmed; this is retained as an integration verification gap. It did not report a false successful selection.

The current map database contains 1,338 places and one route; its `biblical_places` and `map_routes` schemas contain no physical-identification-status columns. The current source set therefore has no passage-linked, strictly displayable physical target for a positive real-data Firefox focus test. The actual route's geometry lacks the route-identification status required by Explorer. NE-6 does not weaken those gates or use a synthetic target to test MapPanel selection. The positive `selected` identity contract remains covered by the exact-kind-and-ID helper test.

## Map layer and compatibility boundary

The Maps controller lifecycle is reused. A missing/failed target leaves a visible status explanation and a working Browse maps action. Close Maps hides its panel and restores focus to the Browse maps button. Browse mode is tested through the actual `#map-search-results` area in the current Maps markup.

Historical and political context layers remain general, source-defined Maps layers. The Explorer projection has no passage-specific source contract for promoting them to event or place records, so NE-6 does not make that promotion. A general map layer is not presented as a passage-specific claim. Existing period and territory metadata are retained only where the source provides them.
