# Narrative Explorer: Commentary Transition Plan

## Separate systems that share the reader

“Commentary” labels three different reader dependencies in this repository. A transition must keep them distinct.

| System | Current implementation | Role |
|---|---|---|
| BHF-generated chapter Commentary / BHF Context | bhf_web/static/bhf-commentary-card.js, the data-bhf-commentary-card section in templates/index.html, and /api/bhf-commentary/{book}/{chapter} plus /evidence in bhf_web/routes/bhf_commentary.py | Read-only renderer for published chapter projections and evidence disclosure. This is the primary feature being transitioned. |
| Tyndale Study Notes / Tyndale Companion | bhf_web/static/commentary.js, resource-router.js, /api/commentary/{book}/{chapter}, framework/commentary/service.py, and commentary SQLite store | Separately licensed study notes in the reader workspace. Preserve it and its notes. |
| Ask BHF | assistant-handoff.js and the Ask BHF dialog | User-authored interpretive question copied to the configured external BHF assistant. It is not the static Commentary renderer. Preserve its prompt/model handoff and principles. |

## Dependencies to preserve during rollout

- **Reader template:** BHF Context card markup, evidence disclosure, verse-reference buttons, and note/highlight/translation actions are wired in bhf_web/templates/index.html.
- **Runtime renderer:** bhf-commentary-card.js fetches a chapter projection and its evidence projection. It has per-chapter response caches and availability/error states. Do not confuse it with commentary.js or the Tyndale workspace.
- **API consumers:** the BHF card uses /api/bhf-commentary/{book}/{chapter} and /evidence; BHF Commentary search/diagnostics have separate consumers. resource-router.js uses /api/commentary for Tyndale notes.
- **Release resolution:** bhf_agent/runtime_paths.py defaults to Commentary v1.1 and supports a configured release. It knows the commentary-v1.2 artifact path, but v1.2 is not the default in this checkout.
- **Release artifacts:** .bhf-data/bhf-commentary-v1.2/ currently contains its release manifest, checksum manifest, and 972 chapter JSON artifacts, including all six pilot chapters. The manifest reports a 1,189-chapter canonical population, 972 published chapters, and 217 not published. Repository tests and Commentary v1.2 code use this release path. Do not regenerate, rewrite, or delete it during a UI transition.
- **Offline:** bhf_web/static/sw.js pre-caches bhf-commentary-card.js, caches /api/bhf-commentary/, /api/commentary/, /api/study/companion-context, canonical, and map routes, and maintains a versioned API cache. Offline packs separately support maps, sources, archaeology, and study data. The existing card script is also registered as a static asset. Retiring it requires a cache-version and offline behavior review.
- **Tests:** frontend coverage includes tests/frontend/bhf-commentary-card.test.js, bhf-commentary-offline.test.js, companion-discoveries.test.js, and assistant-handoff.test.js; backend/runtime coverage includes tests/test_bhf_commentary_projection.py, test_commentary_v12_reader_integration.py, test_commentary_production_runtime.py, test_companion_context.py, and Commentary v1.2 release/lineage tests. tests/gui/test_study_companion.py and tests/gui/test_pwa_offline.py cover reader and offline workflows.
- **Docs/config:** docs/architecture.md describes deterministic reader and Commentary v1.2 as an evidence domain; runtime path code defaults to v1.1. Future rollout work should reconcile this detail without changing frozen artifacts.

## Feature-flagged transition

### Phase 1 — Introduce alongside the current card

Add Narrative Explorer behind a default-off reader feature flag. Keep BHF Context and all existing APIs live. Both features may read the same immutable release and evidence contracts. The default view should make the distinction clear: Narrative Explorer browses evidence and connections; BHF Context remains an archived chapter presentation while the new flow is evaluated.

**Gate:** contract checks pass for all six pilots; every displayed claim has resolvable evidence/source references or an explicit unavailable state; no cosmic record is treated as a map point; notes and Ask BHF behavior remain unchanged.

### Phase 2 — Pilot validation

Use Genesis 1, Genesis 2–3, Genesis 6, Deuteronomy 32, Psalm 82, and Exodus 3 to validate coverage labels, direct/inferred links, sources, uncertainty, reciprocal navigation, mobile navigation, keyboard access, and offline cache/miss states. Compare only stored evidence. Record missing source links and category gaps; do not add speculative CKL objects to improve a demo.

**Gate:** reviewers can reach the source record from every claim; missing, disputed, and not-established states are distinguishable; empty sections say which lookup was empty; map identity limitations are visible.

### Phase 3 — Make Narrative Explorer the default after approval

After explicit product approval and pilot acceptance, flip the runtime feature flag so a selected passage opens Narrative Explorer by default. Keep the BHF Context card available through an **Archived chapter Commentary** link, preserving its original release and evidence route.

**Gate:** feature-flag rollback to the previous default is verified; service-worker cache behavior does not strand the old or new reader; existing /api/bhf-commentary clients remain supported.

### Phase 4 — Retain archived access during migration

Keep the static renderer, immutable Commentary artifacts, manifests, checksums, v1.1/v1.2 release resolution, Tyndale Companion, and Ask BHF available. Archive access remains read-only. Monitor usage and support requests before considering removal.

### Phase 5 — Separate decommission transaction

Only a later, separately authorized transaction may remove unused renderer code or API surface. It must inventory runtime, test, offline, archive, and release consumers, retain immutable release artifacts, and include rollback or an alternate archive reader.

## Compatibility and rollback

- Do not point Narrative Explorer at Commentary JSON as its evidence database. Its source of truth is CKL, map, archaeology, source, and passage APIs.
- Do not treat BHF Context availability as availability of evidence categories. They are different resources with different release populations.
- During coexistence, cache keys include route and projection version. Invalidate cached API payloads on a version change; retain source IDs in offline records.
- The default-off flag provides rollback without API or CKL rollback. If a projection/schema defect appears, turn off the new view and return to the current BHF Context/Companion path.
- Never switch or rewrite the Commentary release as part of enabling Narrative Explorer. Release promotion and reader UX transition remain independent.
- Tyndale notes, local personal notes, highlights, saved passage behavior, lexicon, and translation comparison retain their current routes and storage.
- Ask BHF keeps its current manual copy/open flow. An evidence-aware handoff is a separate opt-in design and implementation.

## NE-1 scope confirmation

This plan documents a safe future transition only. NE-1 does not change the feature flag, reader template, Commentary APIs, renderer, service worker, Tyndale records, Commentary releases, Ask BHF prompts, or deployment configuration.
