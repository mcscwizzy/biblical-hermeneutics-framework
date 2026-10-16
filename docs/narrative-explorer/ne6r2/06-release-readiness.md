# NE-6R2 — Release Readiness

## Disposition

**`BHF_NARRATIVE_EXPLORER_NE6R2_VALIDATION_PENDING`**

The repository now has a source-built, identity-verified package CKL index path for Vercel, strict read-only runtime selection, bounded opt-in request diagnostics, and parity/integrity coverage. Local build and runtime behavior passed. Acceptance remains pending because the Vercel CLI and actual function artifact were unavailable, so function bundling, final bundle size, and hosted cold starts are not verified. The first John 2 Maps delay was measured in current runs but its historic 33-second cause was not established. Screen-reader acceptance remains NE-7 work.

This branch is not merged or deployed. Narrative Explorer remains disabled by default. No production migration, environment change, feature-default change, or domain change occurred.

## Requested release evidence

- **Baseline ancestry:** NE-A2 `3d406b6256a6064a35e0e567c8a1304bf3cba2e8`; NE-5C `b451428546b87b9cfb0912292f8e3906fa0e0803`; NE-6 `224f691feaa4a9ad3f4c921d6bda70941864b67f`; NE-6V `a36e0874449d069bfafd237d68cf0f459ce6b7df`; NE-6R1 `60b582764092ba920f34aa97ee77e56a3b44d18b`. NE-6R1 is the direct parent; the approved NE-6R2 design commit follows it. No chain merge was found or performed.
- **Cold Maps cause:** not established. The historic 33.728-second Firefox header wait was not reproduced. A separate first compact Maps browser request measured 3.837 seconds server-side and spent 3.134 seconds in map-place loading, but direct fresh-process runs measured 0.354–0.375 seconds. No speculative fix was introduced.
- **Matched local cold/warm results:** Genesis 2:8 JSON cold median 30,127 ms vs SQLite 1,968 ms; warm medians 1,546 ms vs 1,507 ms, with exact 131,228-byte body and matching SHA. John 2 compact Maps cold median 369 ms, warm 282 ms, 187,007 bytes. Detailed conditions and all request groups are in [the cold timeline](01-cold-request-timeline.md).
- **Vercel build strategy:** documented Python/FastAPI `[tool.vercel.scripts].build` hook generates `framework/canonical_library/data/ckl.sqlite` from committed CKL JSON; `vercel.json` explicitly includes it plus manifest and object JSON. No local DB copy or network download.
- **Index inclusion evidence:** generated local package index was 116,334,592 bytes and runtime could open it at the configured package path. `includeFiles` declarations and tests are present. An actual Vercel artifact was not available, so deployed inclusion is not proven.
- **Runtime backend:** deterministic test and local strict runtime probe selected `SQLiteCanonicalLibrary` backed by `SQLiteCanonicalRepository`; read-only query retrieval succeeded; JSON fallback was patched to fail if called; writes were rejected; database hash and package directory remained unchanged.
- **Integrity:** schema version 4, retrieval index version 3, 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, all required indexes, SQLite integrity and foreign-key checks passed. Manifest/inventory/source signatures are recorded in [integrity and parity](03-index-parity-and-integrity.md).
- **Indexed/JSON projection parity:** 14 pilot scopes passed canonical serialized equality across the specified identity, evidence, scripture, connections, section, bibliography, confidence/dispute, geography, uncertainty, coverage, and navigation fields, using both deterministic test providers and the real read-only study DB Maps/archaeology lookups.
- **Function bundle size:** actual size is unknown. The explicitly configured CKL source/index inputs total approximately 131.5 MB uncompressed; dependencies and other function files are not included in that estimate. A Vercel artifact build is required to verify the full function bundle against platform limits.
- **Local build verification:** project-owned source build and database verification passed. Local strict runtime check passed. `vercel build` was unavailable because the CLI was not installed/cached and the project was not linked.
- **Preview deployment:** remains unapproved and was not necessary for local code verification. If hosted function cold-start behavior must be measured, request separate authorization for a specific preview. No preview or production deployment occurred.
- **John 2 Maps payload:** compact remains 187,007 bytes and selection lazily obtains full detail. Legacy API full default remains 21,687,196 bytes. No oversized initial Maps response was reintroduced.
- **Browser TTFB:** first John 2 compact browser wait was about 3.9 seconds in one diagnostic run, then about 294 ms warm. Explorer first response was about 9.5–9.7 seconds with a measured 7.1-second CKL fingerprint stage in one captured run. Neither is a Vercel measurement. The 33-second Maps issue remains isolated but unresolved.
- **Full web-app suite:** completed with 78 passed, 55 skipped, two stale baseline failures, and four subtests in 243.92 seconds. Exact test names and reasons are in [browser and regression results](05-browser-and-webapp-regressions.md).
- **Other verification:** Firefox geography suite 9 passed; frontend 13 passed; parity 1 passed; Vercel CKL tests 10 passed; diagnostics 7 passed; storage tests 11 passed after the no-WAL fix. No paid AI calls.
- **Database/source safety:** protected study DB hash remained `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`, schema version 37, integrity `ok`. CKL source objects, manifest and fingerprints were unchanged. Generated SQLite remains untracked and will be removed from the worktree before push.
- **Remaining NE-7 blocker:** screen-reader assistive-technology acceptance is unavailable in this environment. Hosted Vercel bundle and function cold-start proof are also pending outside this transaction.

## Changed surface

The implementation adds the Vercel build provisioner and runtime selection, stronger CKL database identity verification, disabled-by-default timing diagnostics, WAL-free generated publication, focused tests, and the six NE-6R2 reports. It changes no CKL records, study schema/data, commentary content, reader study state, hermeneutical policy, Explorer classification, feature flag default, or deployment target.
