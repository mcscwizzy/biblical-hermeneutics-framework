# Contextual Presentation Architecture

BHF's reader context follows one rule: CKL stores knowledge, BHF retrieves and
ranks it, and an optional model turns a small grounded subset into an
exploratory presentation. Generated prose is disposable. Evidence and its
provenance are permanent.

This is separate from the general ask/answer pipeline and from the older
reader context narration. It is intentionally incremental: existing context,
map, archaeology, canonical-browser, and study-action views remain available.

```text
passage selection
  -> CKL/map/archaeology resolvers
  -> EvidenceBundle V1
  -> deterministic salience ranker
  -> cache / bundled packet / deterministic presentation
  -> validated PresentationPacket V1
  -> Did You Know? / Walk the Land / Why It Matters Here / Dig In

optional browser request
  -> POST /api/study/presentation with the evidence fingerprint
  -> cache / bundled packet / provider / deterministic fallback
  -> strict validation
  -> replace cards only if passage and evidence fingerprint still match
```

## EvidenceBundle V1

`bhf_agent.presentation.build_evidence_bundle()` normalizes passage-scoped CKL
claims and evidence items, map places/routes, archaeology summaries, entity
references, and sources. The bundle has no UI or provider dependency.

Evidence items retain existing CKL evidence or claim IDs whenever available.
Older CKL objects without atomic evidence use deterministic field-derived IDs
as a compatibility bridge. Those broad book-level records receive an explicit
ranking penalty and may produce no card. A fact enters a passage bundle only
when its authored Scripture anchor overlaps the selection, except for map and
archaeology records already returned by passage-specific resolvers.

Passage-indexed map summaries become atomic geography evidence with stable
`map-place:<id>` or `map-route:<id>` evidence IDs. Their dataset attribution is
retained in provenance, while stable place and route IDs remain separate from
the current map renderer.

CKL evidence items may also supply an explicit `passage_relevance` statement.
The normalizer preserves that as a separate atomic significance item with a
stable `<evidence-id>:passage-relevance` ID and a link back to the factual
evidence it interprets. BHF does not synthesize significance from an unrelated
fact. Passage-indexed archaeology summaries use the same significance role
because their underlying database field is already `why_it_matters`.

The bundle hash is SHA-256 over a canonical, grounding-focused serialization.
Only contributing evidence, eligible entity identity, used geography, and
relevant source/canonical provenance enter that payload. Unrelated broad
retrieval results and presentation-only entity metadata therefore do not
invalidate packets, while changes to claims or their relevant provenance do.

## Ranking

`rank_evidence()` uses deterministic signals before a model sees data:

- passage relationship, anchor specificity, and verse distance;
- confidence, source availability, and CKL retrieval relevance;
- linked entities, historical/geographic significance, distinctiveness, and
  available exploration paths;
- penalties for book-wide fallback text, weak relationships, distant anchors,
  broad tags, low-information records, and near duplicates.

The default provider candidate pool is at most eight evidence items. The
default presentation is at most three cards. Retrieval can remain broad while
presentation stays narrow.

## Presentation provider and validation

`PresentationProvider` is independent of OpenRouter, Ollama, or any other
runtime. `AdapterPresentationProvider` can use any existing BHF `ChatAdapter`.
It sends only ranked evidence, exact evidence IDs, entity identity/navigation
fields, minimal map action targets, expected version fields, and strict grounding
instructions. It requests schema-constrained JSON when the adapter supports
that feature and never requests Markdown.

Model output is untrusted. Validation rejects unknown fields, stale hashes,
invalid enums, unsupported evidence/entity IDs, unavailable actions or map
targets, overlong content, too many cards, confidence inflation, disputed
evidence presented as fact, and new clearly era-marked dates not found in cited evidence.
Validation never guesses or repairs an evidence ID.

An empty card list is valid. The instruction to providers is explicit: if the
evidence cannot support a genuinely useful discovery, return no card.

## Cache and fallback

Presentation fingerprints include passage reference, evidence hash,
EvidenceBundle version, PresentationPacket version, and prompt version. The
engine accepts cache and bundled-packet interfaces so browser/PWA stores can
use the same identifiers.

The Study Companion uses a lazy `SQLitePresentationCache` by default. Its file
is `<study-db-stem>.presentation-cache.sqlite`, separate from both CKL and the
study database, and can be overridden with `BHF_PRESENTATION_CACHE_PATH`.
Only validated provider-generated packets are written. Deterministic cards are
rebuilt from permanent evidence and are not persisted as authored knowledge.
The cache retains the 512 most recently accessed entries by default; invalid
packets are discarded. Read, write, corruption, and cleanup failures are
diagnostic-only and cannot interrupt Bible reading.
Presentation failures retain only their stage and exception type, not arbitrary
exception payload text. These diagnostics remain available on the internal
`PresentationResult` for troubleshooting, but ordinary reader serialization
excludes them. A caller must explicitly opt into diagnostic serialization;
the companion API returns only the presentation mode and grounded packet
metadata.
When BHF debug mode is enabled, `/api/debug/runtime-storage` reports
content-free cache health and entry counts; the endpoint remains hidden in
normal reader mode.

### Pre-generated bundles

Deployments may provide offline pre-generated packets with
`BHF_PRESENTATION_BUNDLE_PATH=/path/to/presentation-bundle.json`. Bundle files
use this versioned envelope:

```json
{
  "format": "bhf.presentation-bundle",
  "version": "1.0",
  "packets": [
    {
      "passage_ref": "Mark 5:1-20",
      "cards": [],
      "generated_from": {
        "evidence_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "evidence_bundle_version": "1.0",
        "presentation_schema_version": "1.0",
        "prompt_version": "presentation-v3",
        "model": "pre-generated"
      }
    }
  ]
}
```

The zero hash above is illustrative; a usable packet must contain the exact
current EvidenceBundle hash. BHF derives cache
fingerprints from that metadata rather than accepting keys from the file. The
loader rejects malformed, unsupported, oversized, or duplicate packs
atomically. When a packet is selected, the normal grounding validator still
checks it against the current EvidenceBundle before rendering it. A missing or
invalid optional bundle cannot interrupt Bible reading and is reported only in
debug runtime-storage diagnostics.

Validated generated packets can be exported from the disposable presentation
cache without contacting a model or network service:

```bash
python tools/export_presentation_bundle.py \
  --cache .bhf/study.presentation-cache.sqlite \
  --output deployment/presentation-bundle.json
```

The exporter reads a stable cache snapshot without updating cache recency,
checks each stored fingerprint against the packet's version metadata, enforces
the normal bundle count and size limits, writes through a same-directory
temporary file, and reloads the result before reporting success. It refuses to
replace an existing file unless `--force` is explicit, and it rejects missing,
empty, corrupt, or fingerprint-inconsistent caches. The output can never be
the source SQLite cache itself, even with `--force`. Exported prose remains
disposable presentation output; the file does not become CKL evidence. Full
evidence grounding is checked again when each packet is selected at runtime.

The generation order is:

1. a validated cache entry;
2. a validated bundled/pre-generated packet;
3. a newly generated and validated packet;
4. deterministic cards from the highest-ranked evidence.

The Study Companion uses the deterministic provider-free path by default. To
opt in to model-generated discovery cards on a server with an already
configured BHF model adapter, set:

```bash
BHF_PRESENTATION_ENABLED=true
BHF_PRESENTATION_TIMEOUT_SECONDS=20
BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS=2
```

The presentation deadline defaults to 20 seconds and is capped at 30 seconds,
even when the general model timeout is higher. Enabling this option can send
the passage reference, ranked evidence claims, provenance IDs, related entity
metadata, and available exploration targets to the server-configured model
provider. It never sends the full CKL payload. It can incur provider usage or
cost. Browser-only/transient credentials are not used for automatic cards;
the backend must already have valid adapter configuration and credentials.

The enable flag accepts `true`, `false`, `1`, `0`, `yes`, `no`, `on`, and
`off`. An absent or invalid value fails closed to deterministic rendering. A
missing model or invalid provider configuration also leaves Bible reading on
the deterministic path. Adapter construction performs no network request.
Provider errors, timeouts, malformed JSON, or grounding validation failures
cannot interrupt the reader.
The Companion context endpoint never calls the provider. It returns validated
cache or bundled output when present and otherwise renders deterministic cards.
Its compact `presentation_evidence` contains only claims and source summaries
cited by those visible cards; the full internal EvidenceBundle stays on the
server. When enhancement is configured, the browser makes a separate lazy
request after rendering this local result. A slow or failed provider therefore
cannot delay Scripture or initial Companion context.

The lazy request rebuilds local evidence and requires the browser's evidence
hash to match before generation. The browser also checks selection and hash
again before replacing cards, so a late response from an earlier chapter is
ignored. Unexpected local presentation errors still return a valid zero-card
packet while the rest of the passage context remains available.
Provider generation is also limited to two simultaneous requests per server
process by default. The limit can be set from 1 through 16 with
`BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS`. Requests above the limit skip the
provider immediately and continue through the bundle and deterministic
fallback path, preventing optional discovery cards from exhausting workers or
creating an unbounded provider-cost burst. An invalid limit uses the safe
two-request default.

When enabled, the runtime checks the versioned presentation cache before
making a model call. Valid packets are reused across requests; evidence or
prompt changes, eviction, or explicit cache removal naturally allow a new
generation. Concurrent cache misses for the same fingerprint are coalesced
within each server process so simultaneous page loads do not duplicate model
requests. The cache remains lazy while model generation is disabled.
`BHF_PRESENTATION_CACHE_PATH` still overrides its location. Debug-only
runtime-storage diagnostics report whether generation was enabled and
successfully configured. They also report process-local request outcomes,
provider attempts, failures, saturation, current/peak concurrency, cache
failures, coalesced requests, and
aggregate latency. These diagnostics retain no passage references, evidence,
prompts, generated prose, or credentials.

## Presentation slices

The first UI slice renders `did_you_know` cards. “Dig In” expands the exact
cited claims and source labels. Other action buttons appear only when BHF has a
real target and route to existing canonical entity, maps, archaeology,
language, history, or related-passage views. Dig In does not trigger another
long-form model answer.

The next incremental slice, `walk_the_land`, selects at most one salient
passage-linked place or route. Its action opens the existing map workspace,
selects the referenced marker or route, focuses the map, and displays the
existing curated details. A map-only evidence set produces one geography card
rather than repetitive map trivia. If no useful map evidence is available, the
section stays hidden.

The third slice, `why_it_matters`, appears only when CKL or archaeology has
authored an explicit passage-significance statement. It cites both that
statement and its supporting factual evidence when available, is labeled as
inference or disputed rather than fact, and offers only existing evidence,
entity, map, archaeology, language, or history exploration actions. It does
not generate devotional application, doctrine, ethical instruction, or a
model-created conclusion.

The provider prompt permits all three current card types, with at most one
`walk_the_land` and one `why_it_matters` card. Validation independently checks
the card count, stable targets, evidence roles, confidence, interpretation
level, and actionable resources. Geography contracts have slots for regions,
political territories, ancient names, modern identification, terrain,
elevation, and archaeology metadata without coupling cards to Leaflet.

## Evaluation passages

`tests/fixtures/presentation_passages.json` and
`tests/test_presentation_pipeline.py` exercise:

- 1 Samuel 25: culture, hospitality/provisioning, economics, people;
- Mark 5:1-20: geography, boundary setting, and place significance;
- 1 Corinthians 8: social/cultural context without requiring geography.

The tests also cover stable IDs and hashes, small candidate pools, unrelated
entity suppression, packet parsing, unsupported evidence IDs and dates, cache
versioning, and invalid-generation fallback.

The fixture also carries presentation-level expectations for required and
forbidden card types, cited evidence IDs, action types, category coverage,
card counts, and rendering mode. Run the complete provider-free path locally:

```bash
python tools/eval_presentation.py
python tools/eval_presentation.py --reference "Mark 5:1-20"
python tools/eval_presentation.py --json
```

The evaluator rebuilds each EvidenceBundle to check stable identities, checks
source coverage and ranking/card limits, validates the final packet, and then
applies the fixture expectations. Its report exposes IDs, salience scores,
card-to-evidence links, interpretation levels, and action types without making
a model or network call. Exit codes are `0` for a passing suite, `1` for an
evaluation failure, and `2` for invalid input or arguments.

## Offline bundle deployment checks

After exporting a pre-generated bundle, validate the exact deployment artifact
without making a provider or network call:

```bash
python tools/validate_presentation_bundle.py \
  --bundle deployment/presentation-bundle.json \
  --expect-prompt-version deterministic-v3 \
  --expect-model deterministic
```

The validator fails closed for malformed, oversized, duplicate, unsupported,
or empty bundles and can emit a content-free JSON summary with `--json`. This
check validates the envelope, fingerprints, and version metadata. Full card
grounding remains runtime work because it requires the current EvidenceBundle;
the engine performs that validation before a bundled packet can be displayed.
