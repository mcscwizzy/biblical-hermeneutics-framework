# NE-6R3 — Validation and Next Preview Plan

Audit date: 2026-10-16  
Starting commit: `cb1be01559a4d56a1858ee8807d6b34eb989a9a7`  
Branch: `perf/narrative-explorer-ne6r3-bundle-audit`

## Current validation evidence

| Area | Result |
|---|---|
| Failed deployment record | Confirmed Python 3.12, successful CKL build hook, 116,334,592-byte database, 687 objects, 317.82 MB post-optimization bundle, 225 MB enforced limit, and `LAMBDA_SIZE_EXCEEDED` |
| Local source manifest | Enumerated 20,855 tracked files; `.vercelignore` excludes 18,549 files, exactly matching the deployment log; 2,306 retained tracked files total 80,074,267 bytes |
| Rebuilt CKL database | 116,334,592 bytes; 687 objects; 2,329 claims; 1,297 evidence records; 5,232 source rows; local database matches the recorded inventory fingerprint, source-inventory signature, and source-manifest fingerprint |
| SQLite integrity | `PRAGMA integrity_check` returns `ok`; page size 4,096, 28,402 pages, zero free pages |
| Runtime mode | Repository uses read-only SQLite retrieval on Vercel, requires the built index, and performs stale-index checks; no request-time build/download fallback was introduced |
| Application import | `bhf_web.app` imports successfully as FastAPI and exposes 101 routes |
| Narrative Explorer flag | Code default remains false; project environment key was absent from the read-only key list; OFF state was not changed |
| Targeted tests | 313 passed, 1 skipped, 5 failed, and 10 subtests passed; 5 failures are baseline mismatches on the unchanged NE-6R2 tree, detailed below |
| Actual function artifact | Unavailable: failed deployment file-tree API returned 404 and local Vercel CLI/output artifact was not present |

### CKL identity values

The local build produced these exact values, matching the recorded Vercel
build-hook output:

- Inventory fingerprint: `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`
- Source inventory signature: `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea`
- Source manifest fingerprint: `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`

The local index was generated under `/tmp`; no authoritative CKL source,
claims, citation, relationship, or index schema was modified. Source and
database projections were verified by the existing database builder's full
identity verification and the tests below.

### Reader resources and unresolved Tyndale availability

The measured package inputs retain all tracked CKL JSON sources and the
generated database, lexical SQLite gzip, translations, maps/archaeology data,
Commentary v1.2 release files, frontend/static assets, routes, and templates.
No reader code, feature flags, generated Commentary, or evidence was changed.

The Tyndale Study Notes SQLite is not a tracked package-data file. The current
Vercel runtime default resolves it under `/tmp/bhf-data/commentary.sqlite`.
The project has environment keys for a Commentary release and Tyndale archive
URL/checksum in Preview and Production, but the URL/checksum values are
credential-backed and not needed or printed for this audit; available code
does not consume those two URL/checksum keys. Their existence therefore does
not prove that the Tyndale database is provisioned in a deployed function.
Large Functions would solve a bundle-size constraint, not this separate
runtime-resource question. Before declaring full-reader Preview parity,
verify Tyndale loading through the app's supported resource mechanism without
printing secrets or changing evidence. Do not silently omit Tyndale data.

## Tests run

One targeted pytest invocation covers CKL index build/storage/lifecycle and
retrieval, Scripture/evidence integrity, Narrative Explorer API/projection/map
matching/configuration, Commentary projection/runtime/v1.2, reader and lexical
routes, Maps, archaeological services/corpus/import, provenance projections,
and Tyndale evidence. Completed with **313 passed, 1 skipped, 5 failed, and 10
subtests passed** in 410.96 seconds. No tests were added or modified.

The five failures occurred on the starting commit's unchanged source tree; the
only worktree changes are these audit documents. They are outside the bundle
investigation and were not “fixed” by changing rights, commentary data, or
prompt behavior:

- `test_expansion_preserves_visible_uncertainty_and_reviewed_media_rights`:
  the two reviewed records `wm-ekron-excavations` and `wm-jerusalem-mikveh`
  explicitly have `can_redistribute=false` and `can_cache=false` in the
  archaeology source manifest. The test expects all media to allow both. The
  rights flags were retained.
- `test_revelation_21_dense_projection_compresses_without_forcing_count`,
  `test_revelation_20_control_projection_is_smaller_and_ancestry_complete`,
  and `test_sparse_exodus_control_does_not_inflate` expect 119, 21, and 34
  source synthesis units; the unchanged compiler currently supplies 7, 4, and
  6. No synthesis or evidence data was changed.
- `test_prompt_1_7_frozen_packet_is_unchanged` computes a different prompt
  SHA-256 (`0f9d1e98943d939ced4f90b3bfbf4f47b3ee0f537705b13965409951a4994c26`)
  than the frozen packet expects (`6d6331aef8c7b445f434b07cf407f2e6e181efe2fcc3ff0398f0142c6f2a5dd0`).
  No prompt, packet, or Commentary archive was changed.

The archaeology rights failure was independently reproduced in isolation.
The other four were observed in the full run. Their source inputs and
assertions should be audited separately before deciding whether fixtures,
expectations, or implementation need correction; preserve reviewed rights and
do not modify certified Commentary as part of this bundle work.

The local test suite cannot establish Vercel artifact size, account eligibility
for Large Functions, or hosted Tyndale provisioning. Those require a later
authorized Preview check.

## Recommended next deployment path

1. Keep all data, code, dependencies, flags, and Production settings from
   `cb1be015` unchanged for the first size-path check. The five audit documents
   are excluded by `.vercelignore` and do not alter the function source set.
2. Before authorizing the build, check in Vercel whether Fluid Compute is
   enabled, Active CPU is available, Secure Compute is off, the team plan is
   eligible, and the framework metadata discrepancy is understood. Confirm
   that the opt-in is scoped to Preview only.
3. With explicit approval, push the isolated audit branch to the connected
   repository and set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` only for Preview.
   Also set `VERCEL_ANALYZE_BUILD_OUTPUT=1` only for Preview to capture
   uncompressed size and the largest function contributors. Do not set either
   key for Production.
4. Run one Preview deployment. Confirm the build recognizes Large Functions,
   record its actual bundle size and file/package contributors, and confirm
   there is no `LAMBDA_SIZE_EXCEEDED` error. If eligibility is rejected or the
   analyzer still shows a problem, stop and design a separate split-runtime
   proposal; do not remove evidence or loop deployments.
5. Before accepting reader parity, check function startup and read-only CKL
   retrieval with source fingerprint/stale-index verification. Compare the
   Narrative Explorer API response and provenance projection to the existing
   expected results. Check Maps and archaeology, lexical lookup, Commentary,
   Tyndale availability, Bible translation routes, offline/static resources,
   Ask BHF, and notes/highlights. Verify the Narrative Explorer feature flag
   remains OFF unless separately authorized.
6. Inspect Vercel deployment files/analyzer output for duplicate source and
   installed package paths. If considering any source-set or database change,
   first quantify bytes saved and repeat CKL identity, database integrity,
   retrieval parity, and affected reader tests.

Vercel documents `VERCEL_ANALYZE_BUILD_OUTPUT=1` as a way to expose uncompressed
function size and largest contributors in build output. The failed deployment
does not provide that breakdown. See [Vercel's function-size
troubleshooting](https://vercel.com/kb/guide/troubleshooting-function-250mb-limit)
and [Large Functions announcement](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistvS/eadf06d6c3).

## Remaining blockers and boundary

- Actual Vercel per-file function artifact and resolved dependency tree are
  unavailable; local source/dependency totals are estimates, not a deployed
  bundle breakdown.
- Five existing targeted compatibility assertions fail on the starting
  source tree (one archaeology media-rights test and four Commentary reader
  projection/prompt tests); see the test results above. This audit made no
  changes to those sources.
- Large Functions eligibility is conditional until account/project dashboard
  state is checked.
- Tyndale archive provisioning in the deployed function is unverified.
- No code or package reduction is implemented; measured savings are 0 bytes.
- No push, deployment, project setting, environment variable, billing setting,
  production resource, evidence, or feature flag was changed.

The next hosted action needs separate explicit authorization to (a) push
`perf/narrative-explorer-ne6r3-bundle-audit`, which can trigger a connected
Preview build, and (b) set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` plus
`VERCEL_ANALYZE_BUILD_OUTPUT=1` in **Preview scope only**. This authorization
would not include any Production change or a merge.
