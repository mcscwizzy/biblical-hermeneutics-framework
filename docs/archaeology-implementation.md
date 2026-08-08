# BHF Archaeology Visual Evidence System

This document is the implementation checkpoint for the archaeology visual evidence work. Update it at the end of every phase so a later session can resume without repeating the architecture audit.

## Current status

**Last completed phase:** Phase 10 — Seed data and documentation  
**Next phase:** None; maintain through reviewed manifests and follow-up work  
**Overall status:** Complete for the planned initial implementation

## Phase checklist

- [x] Phase 1 — Audit existing archaeology architecture
- [x] Phase 2 — Add evidence/media/licensing models and validation
- [x] Phase 3 — Implement deterministic passage resolver and tests
- [x] Phase 4 — Expose safe archaeology APIs
- [x] Phase 5 — Add the archaeology study action and evidence packet
- [x] Phase 6 — Add archaeology presentation, chapter refresh, and map linking
- [x] Phase 7 — Add guarded AI synthesis guidance
- [x] Phase 8 — Add optional offline archaeology support
- [x] Phase 9 — Add provider-neutral curated import tooling
- [x] Phase 10 — Add verified seed data and contributor documentation

## Phase 1 — Archaeology domain audit

### Existing systems to reuse

| Concern | Existing implementation | Reuse boundary |
| --- | --- | --- |
| Curated interpretation/context | `framework/canonical_library/objects/archaeology/*.json`, canonical schema, loader, and context builder | Keep CKL objects as semantic/context records; do not put a media catalog into CKL prose. |
| Archaeology storage | SQLite tables created in `bhf_agent/study_db.py` (`archaeology_sites`, `archaeology_items`, `archaeology_scripture_links`) | Extend the existing schema additively; do not create a second archaeology database. |
| Repository reads | `bhf_agent/db/repositories/archaeology.py` and wrappers in `bhf_agent/study_db.py` | Add evidence/media serialization and passage reads here or in a focused repository module. |
| Sources | `sources` table and `bhf_agent/db/repositories/sources.py`; archaeology records already carry `source_id` | Keep evidence-source rights distinct from media/image rights. |
| Map integration | `bhf_web/map_service.py`, `bhf_web/routes/maps.py`, map serializers/matching, and `bhf_agent/map_tools.py` | Extend existing archaeology markers and stable IDs; do not build another map implementation. |
| Study actions | `bhf_agent/study_actions.py` and existing `/api/study/actions` route | Add `archaeology` as a deterministic action and preserve the no-AI path. |
| Offline | `bhf_web/offline.py` and `bhf_web/static/offline/db.js`; current `maps` and `study` packs | Add archaeology as an optional pack or extend an existing pack only after rights filtering is available. |
| UI | Bible reader/study panel templates and `htmx-study-panels.js` | Follow existing study-panel and workspace navigation patterns. |

### Important current findings

- The database schema is versioned (`SCHEMA_VERSION = 15`) and migrations are applied from `bhf_agent/study_db.py`.
- Existing archaeology items have site IDs, periods, Scripture links, confidence, cautions, source metadata, and map-compatible site coordinates.
- Existing map passage matching is useful for map markers but is not yet the bounded, ranked evidence-card resolver described by this plan.
- `DETERMINISTIC_ACTIONS` does not yet include `archaeology`.
- Existing offline packs include maps, but there is no rights-aware archaeology media pack.
- The browser has archaeology JSON fixtures under `bhf_web/static/data/archaeology/`, but these are a separate presentation dataset and must not become a competing server-side knowledge store.
- CKL archaeology objects are already searchable through the canonical library and should receive stable links to evidence IDs only where needed.

### Phase 1 decision

Use the existing SQLite archaeology records as the canonical deterministic evidence index. Add media and rights metadata as related tables, preserve existing fields and IDs, and expose a focused resolver that ranks Scripture-linked records before place/CKL/context matches. Keep CKL as the interpretation layer and the map service as the map layer.

### Phase 2 implementation

- Added `bhf_agent/archaeology.py` with supported rights states, attribution rendering, fail-closed bundling policy, and record/batch validation.
- Added migration 16 and `archaeology_media`, keyed to exactly one existing archaeology item or site.
- Added explicit media creation/listing through `bhf_agent/study_db.py` and repository serialization, while preserving existing site/item IDs and source fields.
- Added tests for unknown rights, remote metadata, attribution-required licenses, broken relationships, duplicate/invalid targets, migration, and serialization.
- No media were seeded because no source/license review was performed.

### Phase 3 implementation

- Added `bhf_agent/archaeology_resolver.py` as a bounded deterministic evidence resolver.
- Whole-chapter requests cover the complete chapter; verse ranges use inclusive overlap with existing Scripture links.
- Exact Scripture relationships rank above named contextual matches, and results are capped at eight cards.
- Candidate text matching is limited to canonical item/site names; generic item-type and relationship words are excluded.
- Evidence cards carry stable IDs, site coordinates, Scripture relationships, confidence/cautions, sources, and rights-aware media metadata.
- Added tests for exact passage lookup, chapter lookup, verse-range overlap, result bounds, ranking, and generic keyword collision avoidance.

### Phases 4–5 implementation

- Added `GET /api/archaeology/for-passage` for bounded deterministic evidence packets.
- Added `GET /api/archaeology/items/{item_id}` and `GET /api/archaeology/sites/{site_id}` with controlled 404 responses.
- Kept existing `/api/maps/archaeology-for-passage` and map marker routes intact.
- Added the `archaeology` deterministic study action, presentation shape, compact fact-packet serialization, and stable archaeology IDs in metadata.
- Archaeology results do not allow agent fallback; AI synthesis remains a later, explicitly requested layer.
- Added API route coverage where the web dependency set is available and a direct study-action regression test.

### Phase 6 implementation

- Added the Archaeology reader action to the existing context menu and deterministic client action registry.
- Added visual archaeology cards to the existing study-panel result flow, with legal-media filtering, no-image fallback, attribution, confidence/dispute labels, cautions, source links, and View on Map actions.
- Added chapter-aware refresh: after an archaeology study view is active, changing chapters replaces it with a deterministic full-chapter lookup rather than retaining stale cards.
- Reused the existing map workspace entry point and stable archaeology IDs; no second map implementation was added.
- Added responsive card styling for desktop and narrow/mobile layouts.
- Verified `htmx-lite.js` syntax and focused archaeology/action/media tests.

### Phases 7–10 implementation

- Added archaeology-specific fact-packet guardrails: distinguish evidence/text/interpretation, preserve uncertainty, avoid unsupported proof claims, do not invent details or image contents, and cite supplied sources.
- Added an explicit Explain with BHF path from the archaeology card; images are not sent to the model by default.
- Added the optional `archaeology` offline pack. It includes text/site/item/source metadata and filters media through the fail-closed rights policy.
- Added `ArchaeologyMediaProvider`, a fixture provider, manifest-driven import workflow, CLI entry point, and importer tests. No provider is called during application startup.
- Added `docs/archaeology.md` and linked it from `docs/README.md`.
- Retained the existing curated SQLite archaeology seed as the initial validation dataset; no new media was bundled without source/license review.

### Resume point

Future work can add reviewed Wikimedia/Open Context/Met/Smithsonian provider implementations and verified media manifests. Any such work must use existing IDs, explicit licenses, attribution, and the validation/import/offline boundaries recorded above.

## Verification checkpoint

- `pytest -q tests/test_archaeology_media.py tests/test_archaeology_resolver.py tests/test_archaeology_ai_packet.py tests/test_archaeology_import.py tests/test_study_actions.py tests/test_notes.py tests/test_map_tools.py tests/test_web_app.py` — **79 passed, 78 skipped** on 2026-08-08.
- The skipped tests are the optional web/UI cases because `fastapi` and related web dependencies are not installed in this environment.
- Dependency-free archaeology/media/import/offline-focused checks — **5 passed, 1 skipped**; the skipped test is the FastAPI-dependent offline-pack integration test.
- `node --check bhf_web/static/htmx-lite.js` — passed.
- `git diff --check` — passed.

## Change log

| Date | Phase | Result |
| --- | --- | --- |
| 2026-08-08 | Phase 1 | Completed architecture audit and recorded reuse boundaries/resume point. |
| 2026-08-08 | Phase 2 | Added rights-aware archaeology media storage, validation, attribution, and focused tests; schema version is now 16. |
| 2026-08-08 | Phase 3 | Added bounded deterministic passage resolver and regression tests for ranking, overlap, chapter behavior, and keyword-collision avoidance. |
| 2026-08-08 | Phases 4–5 | Added safe archaeology APIs and the deterministic archaeology study action/evidence packet. |
| 2026-08-08 | Phase 6 | Added reader action, visual cards, rights-aware media fallback, map action, and chapter-refresh behavior. |
| 2026-08-08 | Phases 7–10 | Added archaeology AI guardrails, optional offline pack, explicit fixture importer, and contributor documentation; retained the existing verified text seed and bundled no unreviewed media. |
