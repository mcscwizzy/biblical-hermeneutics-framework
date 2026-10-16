# NE-6V Positive Map Focus Validation

## Result

Real Firefox exercised the existing Maps controller selecting an exact place and an exact route. The place and route came from an isolated, labeled browser-response fixture. No CKL record, study database, map catalog, or release source was changed.

## Fixture boundary

`tests/test_ne6_geography_selenium.py` installs a `window.fetch` wrapper in the real application page. For the Genesis 2 passage only, the wrapper supplies synthetic place/route API responses and augments the passage projection. Other requests continue to the running application. The application still opens its actual Maps panel, Leaflet map, and existing map-selection controller. No fixture is written to SQLite, JSON, the application server, or any persistent directory.

The records use stable test-only IDs `ne6v_synthetic_place_001` and `ne6v_synthetic_route_001`. Their visible titles, descriptions, notes, provenance, and source name identify them as synthetic test data. Both use a Genesis 2:8 test anchor, `established` physical identification, high identification confidence, and test-only coordinate/route geometry. The place uses latitude `12.345678` and longitude `45.678901`. These are contract inputs, not claims about a biblical location.

The browser test also requests the unmodified server map catalog and Genesis 2 projection and checks that neither contains these IDs. It checks the committed CKL manifest as well. The IDs occur only in the isolated integration test and this validation document; they are absent from the source inventory, production map catalog, and release data.

## Firefox outcomes

Firefox 155.0.1 / Selenium exercised the normal reader → selected verse → Narrative Explorer geography section → item action path.

| Scenario | Observed result |
| --- | --- |
| Synthetic place | `selected`; requested kind/ID and selected kind/ID both equal `place` / `ne6v_synthetic_place_001` |
| Place details | Exact synthetic record title and ID rendered; its KML link contains the exact requested ID; corresponding Leaflet marker appeared |
| Synthetic route | `selected`; requested kind/ID and selected kind/ID both equal `route` / `ne6v_synthetic_route_001` |
| Route details | Exact synthetic route title rendered; its KML link contains the exact ID; Leaflet route path appeared |
| Wrong place ID | The available synthetic place was present, while the requested ID was deliberately overridden to a nonexistent ID. The controller returned `not_found`, displayed that it was not selected, and did not claim success. |
| Wrong kind | Frontend contract test confirms a place with a matching ID cannot satisfy a route request. Wrong selected kind or ID returns `failed`, never `selected`. |
| Close Maps | Focus returned to the Browse Maps trigger. Browser Back restored focus to the Explorer primary region. |

The MapFocus acknowledgment remains opt-in. No production focus behavior or evidence gate was relaxed to create this positive case.

## Real-source negative controls

Real records were tested separately from the fixture:

- Genesis 2 Eden remains inspectable but its uncertain identification does not produce a precise point.
- Acts 7 Nile (`maps:openbible-a012705`) retains Acts 7:19 and stored source coordinates, while `coordinates_displayable` remains false with reason `physical_identification_not_established`.
- Joshua 1 Negeb (`maps:openbible-a1cb244`) retains Joshua 1:4 and stored source coordinates, while precise display remains false for the same reason.
- The uncertain Horeb/Sinai identification remains disputed/uncertain under the existing projection tests and is not promoted to a precise pin.

The fixture does not enter any of these real-source results. Exodus 3's documented sacred-space evidence gap remains open; no evidence was added.

## Verification

The browser integration asserts the application is not in test mode and that the bundled Leaflet runtime is present. The specific map-focus tests passed in Firefox. The focused frontend acknowledgment suite also passed, including exact kind/ID matching, wrong-ID, wrong-kind, unsupported, unavailable, and genuine lookup-failure cases.
