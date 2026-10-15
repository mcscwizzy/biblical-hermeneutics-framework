# Narrative Explorer NE-4 implementation notes

## Branch and baseline

- Branch: `feat/narrative-explorer-ne4-ui`
- Base: verified remote branch `origin/feat/narrative-explorer-ne3-api`
- Base commit: `5a986e88bff9b79e0efea95583965d7045506487`
- NE-1 (`a924d9ee68bf20d1076d3113ee86f90524d31562`) and NE-2 (`b2182561fcc518d49601fdcd965f877270373b57`) are ancestors of NE-3. NE-3 is not an ancestor of the known master commit `b9812fd0236cc2341fd4b777fe92b009dfb05c8b`, so this branch uses NE-3 as its base and does not rewrite its commits.

## Feature flag

The runtime setting `narrativeExplorerEnabled` is read from
`BHF_NARRATIVE_EXPLORER_ENABLED`. It defaults to `false`; unrecognized values
also leave the feature off. With the flag off, the entry button and conditional
script are absent, and ordinary passage selection makes no Narrative Explorer
API request. The NE-3 API route remains registered and its contract is
unchanged.

Enable it in local development with:

```bash
BHF_NARRATIVE_EXPLORER_ENABLED=1 uvicorn bhf_web.app:app --reload
```

For preview testing, set the same environment variable to `1` on the preview
server and restart that preview. No query-string or broad test-mode bypass is
used. This pilot does not change the public reader default.

## Reader integration

The feature is an additional native Study Companion resource launched by
**Explore the Narrative**. It uses the selected chapter or verse range, the
existing resource host, desktop dock, mobile sheet, focus restoration, and
Companion history. Tyndale, BHF Context, notes, Ask BHF, and the other existing
resources retain their own routes.

The initial view renders six projection sections, the section coverage state,
source-domain coverage, differentiated CKL parent/claim/evidence counts, and at
most two previews per section. Inspecting a section creates at most 12 more
records at a time. Records without an authored summary fall back to their
source title or identity. Text is added with DOM `textContent`; source strings
are not interpreted as HTML and are never used to manufacture external links.

Source identity, CKL subject, claim/evidence identity, available passage
anchors, evidence category, assertion and claim types, confidence, certainty,
dispute/review state, original relationship types, recorded rationale, and
available source bibliography appear in expandable provenance. Counts separate
CKL parents, claims, evidence entries, interpretive notes, maps, and archaeology
service records.

## Pilot projection review

All seven results below came from the local NE-3 route against the committed
CKL corpus and the existing current study database. No demonstration records
were used. The study database SHA-256 before and after retrieval was
`2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.

- **Genesis 1:** actual literary claims and authored theme connections appear
  in the Biblical Narrative and Themes sections. The UI does not call or
  substitute the Commentary renderer. Ancient textual-comparison records are
  shown under Archaeology & Ancient History with their evidence categories.
- **Genesis 2:** passage-anchored Garden/rivers evidence and map records appear
  in Biblical Geography. The Garden map point has
  `coordinates_displayable: false` and is withheld with the projection's
  identification reason. The authored record retains disputed identification
  status. No Garden marker is opened automatically.
- **Genesis 3:** the projected Eden map record is also non-displayable and has
  no direct-selection action; its full record remains inspectable. The
  projection includes a sacred-space evidence record in the cosmic section.
- **Genesis 6:** the section renders the passage-anchored cultural-background
  and ancient-text evidence present in CKL, although the legacy Companion
  theme count was zero. The UI does not restore unrelated book-level
  cross-references.
- **Deuteronomy 32:** the 32:8 manuscript-variation claim/evidence and CKL
  source identities appear under Archaeology & Ancient History while the
  completed archaeology-service lookup reports zero linked records. The UI
  preserves the projection's `direct` passage relationship as a relationship
  label; it does not call it a direct quotation.
- **Psalm 82:** the explicit wording, disputed interpretation, and Ugaritic
  comparison remain separate records and statuses. The cosmic section does not
  choose one interpretation.
- **Exodus 3:** actual place records appear in Biblical Geography; Mount Horeb
  has a non-displayable point and the record retains `possible` map confidence.
  Presence Theme and Divine Presence source identities appear in Themes &
  Biblical Connections. The current projection does not place an Exodus 3
  sacred-space record in the separate Divine Council & Cosmic Geography
  section; see the NE-5 dependency below.

The response covers every category even when it contains no records. An
unknown section remains labeled unknown, with source-domain coverage shown;
failed/partial retrieval is not rendered as an empty successful result. A
completed empty archaeology-service lookup is explicitly scoped to linked
records and is not presented as disproof. The CKL coverage line keeps manuscript
records visible independently of archaeology-service coverage.

## Navigation and limits

- CKL and archaeology records use their existing BHF detail handlers.
- Map records with a physical geography kind and explicitly displayable
  geometry use their actual `target_id` through the existing Maps focus
  mechanism. When a projected map record cannot safely be selected, the button
  is labeled **Open general Maps Explorer**. A focus attempt is labeled as an
  attempt because the current map controller can fail to find a stale or
  unavailable ID.
- Cosmic/conceptual records never receive physical-map navigation.
- Source references without a supported detail route show their available
  bibliography without a link. No KML download or collection URL is described
  as an item detail screen.
- The existing Companion history preserves the originating passage and
  supports back/forward navigation. Full bibliography navigation, deeper
  relationship trails, source-detail screens, and confirmed map-focus
  acknowledgements remain NE-5 work.

## Loading, performance, and offline behavior

No API request starts when the feature is off or while a passage changes with
the explorer inactive. An explicit open makes one chapter or range request.
Identical pending URLs are shared, range URLs preserve exact verse bounds, and
`AbortController` plus a request sequence guard rejects stale results. Closing
the resource aborts the active subscriber. Fetch uses `cache: "no-store"` so
browser HTTP caching does not become an undocumented projection cache. The
module reports response/body
time, JSON parsing time, payload bytes, request count, initial view-building
time, and created DOM node count through
`bhf:narrative-explorer-metrics`.

Local measurements used the actual application and API over loopback with the
current study database. Response time is Node Fetch through body read; parse
and view construction are measured by the NE-4 module. The Node render pass
used a DOM API shim, so render numbers exclude browser layout and paint.
Measurements are observations, not performance guarantees.

| Passage | Response/body ms | Parse ms | Initial overview ms | DOM nodes | Payload bytes | API requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Genesis 1 | 32,033.3 | 2.967 | 27.641 | 360 | 260,088 | 1 |
| Genesis 2 | 3,919.9 | 5.990 | 4.857 | 474 | 420,593 | 1 |
| Genesis 3 | 3,014.4 | 1.327 | 3.039 | 471 | 154,071 | 1 |
| Genesis 6 | 3,585.9 | 2.044 | 2.448 | 466 | 246,897 | 1 |
| Deuteronomy 32 | 5,454.6 | 3.570 | 2.348 | 314 | 459,990 | 1 |
| Psalm 82 | 2,112.9 | 0.464 | 0.557 | 297 | 44,556 | 1 |
| Exodus 3 | 5,066.1 | 4.721 | 1.031 | 363 | 562,061 | 1 |

The cold Genesis 1 response took about 32 seconds, and Exodus 3 returned about
562 KB in just over five seconds. The explicit loading state keeps this work
visible, but a cold wait of that length is too slow for a comfortable reader
interaction. NE-5/NE-7 should evaluate a bounded read-only overview endpoint or
query-path optimization that preserves the complete authoritative evidence for
deeper inspection; NE-4 does not hide the cost by truncating backend evidence.

The service worker cache version is `v46`; the small reader module is in the
static asset precache. The Narrative Explorer API is not added to cacheable API
prefixes and projections are not persistently cached. An offline miss displays
an explicit unavailable state without stale evidence and retries after the
browser reports that it is online. Existing service-worker caches are retired
through the versioned activation path. A bounded cache keyed by schema version
and exact passage scope, with visible retrieval time and explicit size/LRU
limits, is a proposal for NE-7 rather than part of this pilot.

## Verification and remaining NE-5 dependency

The focused frontend tests cover flag-off request suppression, exact route
construction, in-flight request sharing, stale-response suppression,
cancellation, online retry after an offline miss, bounded rendering, safe text,
provenance, navigation gates, cosmic-to-physical map protection, service-worker
precache upgrade, and Narrative Explorer API exclusion from service-worker
caching. The Python route tests cover the seven NE-3 projections and existing
projection validation. The optional headless Firefox run opened the feature
against real John 1 API records, observed one passage request and both module
metrics, rendered six sections with actual projected items, then checked
keyboard entry, browser Back/Forward, focus return, mobile sheet entry/close,
the 44 px launch target, and no horizontal overflow at desktop and phone
widths. It saved `/tmp/ne4-narrative-explorer-desktop.png` and
`/tmp/ne4-narrative-explorer-mobile.png`. The seven-pilot timing run used the
same real route/module against the committed CKL and current study database.

Service-worker offline behavior was checked in the frontend harness: the new
module is precached, the Narrative Explorer API is left to the browser network,
an offline fetch rejection renders the explicit unavailable state, and an
`online` event retries. A browser network-disconnect simulation was not part of
the Firefox run.

NE-5 must review the projection coverage for Exodus 3 sacred-space evidence:
CKL contains `presence-theme` and `divine-presence` identities, and the pilot
projection returns them in Themes & Biblical Connections, but returns no item
for Divine Council & Cosmic Geography. NE-4 preserves the schema's section
assignment rather than inferring a new cosmic classification in the browser.
The projection also marks some category states `unknown` when a source lookup
completed but no item was assigned to that category; coverage details remain
visible so unknown is not mistaken for a completed empty result.

The pre-existing `WebUiSeleniumTests` class has three failures on this branch:
the mobile Maps workspace tab cannot be interacted with, the legacy
`app-dock-ask` selector is absent, and Bible search returns no local result.
The same three failures reproduce unchanged on the exact NE-3 base commit
`5a986e88bff9b79e0efea95583965d7045506487`; the first two have the same DOM and
interaction traces, and the search test times out on both revisions. They are
baseline smoke-test/setup failures, not regressions from NE-4. The dedicated
flag-enabled Narrative Explorer browser test passes against actual John 1
records.
