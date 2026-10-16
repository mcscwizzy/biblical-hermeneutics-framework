# NE-6R1 — John 2 Maps Response Size Analysis

## Measurement method

Measurements used the configured study SQLite database with `BHF_STUDY_DB_PATH` and `BHF_STUDY_DB_READ_ONLY=1`. The protected database was not rebuilt or modified. The baseline response was read as raw HTTP bytes from `GET /api/maps/places-for-passage?book=John&chapter=2`, parsed with Python's JSON decoder, and hashed before analysis. Resolver and Starlette `JSONResponse` serialization timings were measured separately against the same endpoint data.

## Baseline and compact response

| Measure | Existing full API response | Compact Maps-panel response |
|---|---:|---:|
| HTTP status | 200 | 200 |
| Raw body bytes | 21,687,196 | 187,007 |
| JSON parse | valid | valid |
| Marker records | 69 | 69 |
| Raw body SHA-256 | `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f` | `991064790c1e215ce69f09b1885818419c49f90e0f3e71dd408e0d24eb35aa32` |
| Resolver time | 36,398.201 ms | 268.705 ms |
| JSONResponse serialization | 465.623 ms | 3.669 ms |

The compact body is 21,500,189 bytes smaller (99.138%). This is a response-shape reduction: it omits only the repeated `related_passages` expansion from each marker in the initial Maps request. It does not cap, truncate, or filter relationships. The legacy API response remains the default for callers that omit the new query parameter.

## Field profile

| Field / measure | Baseline contribution |
|---|---:|
| `related_passages` | 21,498,809 bytes (99.13% of the full response) |
| `related_references` | 119,487 bytes |
| All other marker identity, coordinates, source, name, alias, description, confidence, location, period, and passage-match fields | 68,900 bytes combined |

The full response serialized 32,153 passage entries in marker relationship data, covering 4,445 distinct book/chapter/verse-span references. That is 27,708 repeated reference entries. Counting the repeated testament subgroup copies yields 32,665 serialized entries while the same 4,445 references remain unique. Relationship/source identity tuples total 5,639 unique values. Relationship labels in the response include `directly_named` (512), `same_region` (30,633), `same_route` (120), and `same_empire_period` (888).

Repeated `same_region` passage relationships dominate the payload. The cost was not marker coordinates, source attribution, aliases, or historical-period metadata.

## Separate initial-catalog transfer

The real Firefox trace found another unnecessary transfer during passage-mode startup: the Maps panel requested the complete browse catalog even though passage mode only reads the timeline period options. That catalog was 3,037,523 bytes in the observed request; its timeline-only counterpart is 713 bytes (3,036,810 fewer bytes, 99.9765% smaller). In the prior browser trace, waiting for the full catalog response headers took 37,060 ms and body read plus JSON parsing took 60 ms. After the explicit `include_records=false` mode, a real Firefox run received the 713-byte response in 87 ms and parsed it in 2 ms. Browse mode and offline-pack installation still request the complete catalog.

## Controls

The compact resolver returned the following matched control sizes; these are direct Python resolver/serialization measurements, not browser timings:

| Passage | Bytes | Markers | Resolver time |
|---|---:|---:|---:|
| Genesis 2 | 94,904 | 22 | 144.296 ms |
| Acts 7 | 450,080 | 53 | 255.091 ms |
| Joshua 1 | 176,308 | 15 | 128.842 ms |
| 3 John 1 | 1,813 | 0 | 127.242 ms |

## Detail parity

For all 69 John 2 markers, the existing `GET /api/maps/related-passages-for-place` data was compared with the corresponding `related_passages` value in the original full response. All 69 objects matched exactly; there were zero mismatches. Retrieving all 69 details sequentially took 37,882.533 ms in the measured Python path. The UI requests only the selected marker's complete detail object.

The browser acceptance run will report its selected-marker detail latency separately. A compact initial response is not counted as an end-to-end speedup unless the initial interaction and the selected full-detail request are both measured.

## Composition guarantees

All 69 marker IDs, names, aliases, coordinates, place identity, source names and URLs, confidence and identification status, historical periods, passage-match rationale, and `related_references` remained identical. Only the expandable relationship object is deferred. No study database record or authored relationship was changed.
