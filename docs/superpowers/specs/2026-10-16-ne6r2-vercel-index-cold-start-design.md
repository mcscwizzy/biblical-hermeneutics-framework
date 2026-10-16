# NE-6R2 Vercel CKL Index and Cold-Start Design

## Goal

Provision a current, read-only CKL SQLite index during Vercel's supported Python build phase, prove that the deployed function bundle contains and selects it, and measure Maps and Narrative Explorer first-request work without changing reader behavior or evidence.

## Accepted constraints

- Work on `perf/narrative-explorer-ne6r2-vercel-index`, based directly on NE-6R1 `60b582764092ba920f34aa97ee77e56a3b44d18b`, in the isolated worktree `/tmp/bhf-ne6r2`.
- Do not merge or deploy. Do not commit a generated SQLite binary.
- CKL JSON remains authoritative. Do not change CKL records, fingerprints, evidence relationships, study DB contents/schema, or reader behavior.
- Vercel requests must not build, rebuild, migrate, or mutate the CKL database.
- Preserve NE-6R1 Maps compact/full response behavior, offline cache behavior, protected geography uncertainty, and the disabled-by-default feature flag.
- Do not change production project settings, environment variables, domains, or Vercel plan.

## Deployment and repository design

Use the official FastAPI Python build hook, `[tool.vercel.scripts].build`, to run a repository-owned CKL provisioner after dependencies install and before Vercel assembles the function. The provisioner builds from the checked-out `framework/canonical_library` JSON inventory into the package-owned path `framework/canonical_library/data/ckl.sqlite`; it never reads `.bhf/ckl.sqlite` or other local databases as build inputs. The existing `*.sqlite` Git ignore remains in force, so the generated file is not committed.

The function entry in `vercel.json` explicitly includes the generated database, `framework/canonical_library/manifest.json`, and `framework/canonical_library/objects/**/*.json`. The existing `.vercelignore` remains responsible for excluding local `.bhf/` state and private commentary candidate artifacts. The package-owned path is resolved from the installed module location; local and Docker path behavior remains as configured today.

The provisioner computes the expected identity from the checked-out JSON root before generation, then invokes the existing verifier against that same root. Verification must confirm the complete source inventory content signature, stable manifest identity, inventory fingerprint, schema and retrieval index versions, object/claim/source/evidence counts, required indexes, SQLite integrity, and foreign key integrity. Extend `verify_database` only where needed so it compares manifest identity and inventory content signature with the supplied JSON root, rather than merely checking that metadata fields exist.

When Vercel's documented `VERCEL=1` runtime variable is present, Narrative Explorer selects the package-owned index as SQLite, opens it read-only, and uses an error policy for missing or stale data. Conflicting `BHF_CKL_BACKEND` or `BHF_CKL_DATABASE_PATH` overrides fail clearly instead of changing the release runtime's backend or artifact path. It must fail visibly on an absent, unbundled, incompatible, or stale index; it must not fall back to JSON or rebuild. Local and Docker configuration and fallback policy remain unchanged. A separately configured JSON fallback is tested only as a separate mode and is not accepted as proof of indexed startup.

## Cold-request diagnostics

Add opt-in diagnostics behind one environment flag, disabled by default. With diagnostics enabled, record structured wall-clock timestamps, process-relative elapsed time, process ID, a generated request correlation ID, a static route label, phase name, elapsed milliseconds, HTTP status, response byte count, first-request status, and in-process active-request count. Never log request path parameters, query values, headers, authentication values, selected passages, response bodies, evidence, or source text. Do not add a diagnostic endpoint.

Measure module import completion, application construction, route registration, first ASGI dispatch and middleware-stack initialization, request entry, response construction, and response-header emission. On applicable paths also time study DB acquisition and place loading, CKL repository construction and fingerprint/freshness validation, passage text resolution, place/route text matching, scripture-reference lookup, marker serialization, archaeology service initialization and lookup, and Narrative projection. Process launch-to-import/app readiness is measured by the bounded local benchmark runner; in-process events use a process-relative monotonic clock. Record overlapping first requests in one PID so request serialization or shared-lock waits can be distinguished from independent process cold starts.

Diagnostics must have no effect when disabled other than a cheap feature check and must not alter scheduling, caches, database policy, or response bodies. The Maps wait remains unresolved unless timings identify an attributable phase and a narrow correction passes matched remeasurement.

## Verification design

Use the same committed JSON inventory, protected study DB copy, and runtime configuration for matched process-cold and process-warm runs. Report conditions explicitly, with sequential and concurrent calls distinguished. Include compact John 2 Maps, John 2 routes, Maps timeline metadata, and Genesis 2:8 Narrative Explorer, with bounded repetitions, medians/ranges, response sizes/hashes, and cache/backend settings. Do not merge the NE-6V and NE-6R1 historical baselines.

For parity, compare complete JSON and SQLite Narrative Explorer projections serialized deterministically for Genesis 1, Genesis 2, Genesis 2:8-14, Genesis 3, Genesis 6, Genesis 6:1-4, Deuteronomy 32, Deuteronomy 32:8-9, Psalm 82, Exodus 3, Exodus 3:1-6, Acts 7, Joshua 1, and Joshua 1:1-9. Require exact response hashes and the requested identity, evidence, anchor, uncertainty, geography, coverage, and navigation fields. Preserve the indexed/JSON backend selection as a deterministic assertion, and verify read-only behavior and no hidden fallback.

Regression verification covers the existing John 2 compact delivery and legacy full-response compatibility, lazy related-passages retrieval, bounded caches, offline behavior, focus acknowledgments, cache target integrity, Acts 7 Nile and Joshua 1 Negeb associations, and Eden/Horeb/Sinai uncertainty. Run Firefox integration checks and the complete web-app suite with per-test timing. Investigate the first non-progressing test under the local harness; do not suppress stale or failing tests. Record any known harness-specific heartbeat workaround separately from application changes.

For deployment packaging, run the supported local Vercel build workflow if it is available without pulling project secrets or changing project settings. Inspect the resulting function artifact for the generated DB, source JSON inventory, runtime imports, bundle size, and absence of local `.bhf` and unrelated `.bhf-data` files. Exercise runtime selection from that artifact where possible. Do not substitute the developer's local SQLite file. If Vercel's local builder is unavailable or a remote function cold-start is needed to complete acceptance, record the exact validation gap and request a specific preview authorization; do not deploy under this work item.

## Documentation and completion

Write the six requested NE-6R2 reports under `docs/narrative-explorer/ne6r2/`. They must distinguish historical baseline, fresh local measurements, actual artifact evidence, and unresolved remote/browser limitations. Include source and manifest identities, tests, bundle size, safety checks, changed files, final remote commit, worktree state, and remaining NE-7 screen-reader acceptance.

The final branch is committed and pushed without merging or deployment. Report `BHF_NARRATIVE_EXPLORER_NE6R2_VERIFIED` only if the build artifact, runtime backend, integrity, parity, browser, and regression evidence are complete. Otherwise report `BHF_NARRATIVE_EXPLORER_NE6R2_VALIDATION_PENDING` or `BHF_NARRATIVE_EXPLORER_NE6R2_BLOCKED` with the precise unresolved evidence.
