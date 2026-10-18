# NE-7.3 — Maps and Evidence Trail integration

## Evidence Trail

The NE-5C traversal and API checks passed for the established contract: at most three hops, at most twelve visited nodes, parent-qualified evidence identities, original CKL source/bibliography lookup, and only authored supported relationships. Relationship labels and types are preserved. No reciprocal edge is synthesized. Missing, repeated, unresolved, or unsupported targets remain unresolved rather than being converted to a connection. Browser breadcrumb, current step, trail navigation, return to the originating passage, and Back/Forward were exercised in the Firefox geography suite.

Primary source-backed pilot identities appear in `02-hermeneutical-and-source-parity.md`. No trail step created new biblical evidence. Full source records resolve through CKL; an unavailable lookup is not replaced by an invented description. A dedicated numeric timing for each breadcrumb action was not captured.

## Maps modes

### Ordinary Maps

Browser and Maps tests exercised catalog loading, search, place details, period filtering, route availability, and visible source/certainty metadata. The current mobile Maps navigator and search were exercised at Firefox's actual 500-pixel minimum viewport. The corrected smoke test opens Maps through the current Companion Explore resource list and opens its navigator; it no longer assumes the removed workspace Maps tab.

### Passage-first focus

Passage-linked markers were checked for Genesis 2, Acts 7, Joshua 1, and John 2. Isolated synthetic markers/routes verified positive exact-ID selection. Synthetic data lived in the browser fixture only and was not written to CKL. Actual status behavior distinguishes `selected`, `not_found`, `unsupported`, `unavailable`, and `failed`; only an exact requested kind and ID selected by the Maps controller can receive `selected`. Missing/uncertain geographic identification falls back without asserting a location. Browser return to the narrative preserved the original passage context.

Physical-location safeguards remain intact:

- Eden has no precise authorized point.
- Horeb/Sinai identification remains uncertain.
- Acts 7 Nile source is `openbible-a012705`, anchored to Acts 7:19, without an asserted precise point.
- Joshua 1 Negeb source is `openbible-a1cb244`, anchored to Joshua 1:4, without an asserted precise point.
- Conceptual/cosmic geography is not rendered as literal physical geography.

## Compact John 2 request and lazy details

The Maps-panel request stayed compact and retained the expected marker IDs and metadata. The observed compact places response was **187,007 bytes**; catalog response **713 bytes**; routes response **2,900 bytes**. Selecting a place retrieved its full detail response (**32,842 bytes**, about **323 ms** in the measured browser run), including deferred related-passage information. The legacy full-response API remains compatible and was not changed: its John 2 response was **21,687,196 bytes**, 69 markers, SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`. The Maps panel did not request that expanded payload initially.

Service Worker v49 behavior was covered in Firefox: cache use was bounded; the observed diagnostic cache had 11 entries and about 6,492,067 bytes. Browser tests covered offline pack access and reconnect/retry. A successful retry returned current detail, while the offline missing-evidence state remained explicit; no stale record was relabeled as a newly fetched response.

## Results and limits

Projection, map matching, Maps serialization, focus acknowledgment, and geography Selenium suites passed. Exact commands and totals are listed in `06-performance-and-regressions.md`. These are local Firefox results only; hosted Maps/CKL runtime was not reached. Source/certainty display was validated through the available fixture and tested service contracts, not a manual audit of every catalog entry.
