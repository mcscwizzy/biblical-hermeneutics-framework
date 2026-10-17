# NE-7R2 Maps performance analysis

## Finding and change

The Jerusalem search repeatedly loaded the place-reference list once per place.
The process-cold profile showed 1,338 places causing 1,338 reference-list
lookups, 1,415 schema validations, and 7,267 SQLite execute calls. Maps now
loads references once, groups them by place ID, and passes those read-only
references into marker serialization. Marker ordering and the serialized API
shape remain unchanged.

## Search measurements

| Measure | NE-7R1 | NE-7R2 |
|---|---:|---:|
| Process-cold local API Jerusalem search | 2,314 ms direct in NE-7R1 | 635 ms (n=1) |
| Warm local API Jerusalem search | 2,350 ms direct in NE-7R1 | 617 ms median (578–617; n=2) |
| Firefox response body consumed and Jerusalem rendered | 4.86 s | 589 ms |
| Search response bytes | 1,681 | 1,681 |
| Response SHA-256 | `ba659afcf3f8bb4935875fa42e927c567627fe726775aec913e227a52cc0d994` | identical |

The direct API sample set used the default Jerusalem search query three times
in one fresh process. The first request took 634.6 ms; the two later requests
took 577.6 and 616.9 ms. All three returned the same body. These are observed
samples, not percentile estimates. In the earlier stage profile, catalog
loading took 378 ms cold and 339 ms warm; source and period
filtering took 49 / 43 ms; the batched reference lookup took 57 / 50 ms; place
matching took 219 / 218 ms; marker serialization took 5.2 / 5.4 ms; response
construction took 0.13 ms; and thread-pool wait was 25 ms cold and 0.3 ms warm.
The cold and warm requests remain close because Maps rebuilds the catalog and
reruns matching for each query. The previous 4.86-second browser search was
dominated by repeated N+1 reference reads; batching those reads is the
evidence-backed improvement. The remaining roughly 0.6 seconds is now
accounted for by catalog loading and matching. No persistent catalog cache was
added without a source-identity and invalidation contract.

## Compact Maps and details

The passage-first John 2 request remains compact: 69 markers, 187,007 bytes,
SHA-256 `991064790c1e215ce69f09b1885818419c49f90e0f3e71dd408e0d24eb35aa32`.
Three local API samples took 360.7, 269.4, and 271.3 ms (median 271.3 ms).
In the full Firefox geography run, the same response took 3.20 seconds while
reader, Companion, and Explorer requests were also active. The selected Angle
place (`openbible-aac6cda`) details endpoint remains on demand and returned
32,842 bytes in three samples taking 286.6–287.2 ms, SHA-256
`0255518e38e98c31cfe9b11340f479cc2f7e826fb40254484c4bb3e17abe0ca5`.
The ordinary UI continues to request `include_related_passages=false` before
the reader asks for a selected place.

The legacy expanded John 2 endpoint still returns about 21,687,196 bytes when
explicitly requested; the ordinary Maps panel does not make that request.
Existing marker IDs, uncertainty, map-focus acknowledgements, geography
safeguards, relationship expansion, and API response fields remain intact.
