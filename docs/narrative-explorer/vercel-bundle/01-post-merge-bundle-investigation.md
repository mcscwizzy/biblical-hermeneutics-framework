# Post-Merge Vercel Function Bundle Investigation

- Audit date: 2026-10-17
- Project: biblical-hermeneutics-framework
- Investigation branch: investigation/vercel-lambda-size-2026-10-17

## Executive finding

The merged NE7R3 tree is intact, but its Vercel Python function still exceeds the limit enforced for the failed deployment. The build produced a verified 116,334,592-byte CKL SQLite index, then Vercel measured the function at 340.46 MB before dependency optimization and 308.39 MB afterward, against a 225 MB limit. The optimized bundle is 83.39 MB over.

The build log and source tree establish the large known assets, but the failed deployment does not expose its function file tree. Vercel's deployment-files API returned 404 File tree not found, and this workspace has no Vercel CLI or .vercel/output/functions artifact. Therefore the ranked file list below is the exact measured source/build input inventory and a ranked list of known runtime assets; it is not an invented per-file attribution of all 308.39 MB. An analyzer-enabled Preview build is needed for the exact installed-package, dependency, bytecode, and duplicate-copy breakdown.

The least risky route to a working Preview is to check project eligibility for Vercel Large Functions and, if eligible, opt in for Preview only. That keeps the shared CKL provider, data, and reader architecture unchanged. If the standard 225 MB limit must remain, the first architecture candidate is to move only the immutable CKL SQLite artifact outside the function bundle while keeping the source JSON in the bundle and preserving the provider's full source and database verification. Removing known files through packaging rules alone cannot provide the required reduction.

## 1. Baseline and deployment status

- Local origin/master is 551a998f5c40d6cb4d5e8a1f41db1bfe8f307096, the supplied verified master revision. The NE7R3 commit 483611ceef4a44fb34b4e2d8c62d737fd4cf192f is an ancestor of master. Both commits have tree 962193d6f3ec2986abbcb7feb5bd65b8ba06714a, so the failed NE7R3 source tree is byte-for-byte the same Git tree as merged master.
- A remote fetch could not refresh the local ref because .git/FETCH_HEAD is read-only in this environment. The branch therefore uses the locally available origin/master ref at the user-supplied verified hash.
- The investigation branch was created from origin/master. No changes were made to master.
- Deployment dpl_7FfDEarUciyFzfa2vvGubSmYnk4f is in ERROR with LAMBDA_SIZE_EXCEEDED at buildStep. Vercel built Python 3.12 from branch refactor/narrative-explorer-ne7r3-commentary-retirement, commit 483611c. No functioning deployment resulted from this build.
- The Vercel build log reports 340.46 MB before optimization, 308.39 MB after optimization, and a 225 MB enforced limit. Vercel removed 32.07 MB during dependency optimization; 83.39 MB remains above the enforced limit.
- Vercel's Python runtime page currently documents a 500 MB standard maximum for Python functions, but this deployment explicitly failed at 225 MB. This report treats the observed deployment limit as authoritative for the current project and calls out the difference for verification before another build.
- The earlier NE6R2 Preview measured 317.82 MB after optimization. NE7R3 reduced that result by 9.43 MB, but did not resolve the pre-existing issue.
- vercel.json still has git.deploymentEnabled.master set to false. This investigation did not alter it or trigger a deployment.
- Vercel's deployment API labels the project framework container, while the repository config says fastapi and the failed build log identifies Python 3.12. The successful Python build is direct evidence of the runtime used; clarify the metadata difference before another hosted build.

## 2. Packaging inputs and ranked known contents

### Source upload, before Python packaging

The .vercelignore matcher over the Git-tracked tree gives the following source-side sizes. Its ignored-file count exactly matches the deployment log. These are uncompressed file bytes in the Git deployment source, not the final function size or the compressed network upload size.

| Source stage | Files | Bytes | Decimal MB |
|---|---:|---:|---:|
| Full tracked tree | 19,908 | 591,400,459 | 591.400 |
| Removed by .vercelignore | 18,710 | 517,221,190 | 517.221 |
| Retained tracked inputs | 1,198 | 74,179,269 | 74.179 |
| CKL index generated during the Vercel build | — | 116,334,592 | 116.335 |
| Retained source plus one generated CKL index | — | 190,513,861 | 190.514 |

The ignore rules already remove .bhf-data/**, .bhf/, tests, docs, scripts, tools, GUI dependencies, local environments, and build caches. In particular, the local .bhf/ckl.sqlite is excluded. Vercel instead builds a separate index at framework/canonical_library/data/ckl.sqlite from the checked-in JSON inventory.

### Known runtime assets, largest first

| Rank | File or group | Bytes | Decimal MB | Runtime role and evidence |
|---:|---|---:|---:|---|
| 1 | Generated framework/canonical_library/data/ckl.sqlite | 116,334,592 | 116.335 | Build-hook output and read-only indexed CKL retrieval. The deployment log confirms this exact path and size. |
| 2 | framework/lexical/database/lexicon.sqlite.gz | 39,946,432 | 39.946 | Packaged lexical database; runtime expands it to /tmp/bhf-data/lexicon.sqlite on first use. |
| 3 | CKL manifest plus 687 object JSON files | 15,163,112 | 15.163 | Source inventory used for source manifest, content signature, and inventory fingerprint verification. |
| 4 | bhf_agent/data/asv_bible.json | 5,792,762 | 5.793 | Bundled translation. |
| 5 | bhf_agent/data/kjv_bible.json | 5,344,643 | 5.344 | Bundled translation. |
| 6 | bhf_agent/data/openbible_places.json | 2,114,783 | 2.115 | Reader/map place data. |
| 7 | bhf_web/templates and bhf_web/static | 1,598,962 | 1.599 | Reader UI, maps, offline client, and supporting assets. Includes a 225,544-byte Leaflet source map. |
| 8 | Remaining retained Python, configuration, and package files | 4,009,335 | 4.009 | Application and subsystem source plus retained root/package metadata. |
| 9 | frontend static files | 158,657 | 0.159 | Served from the existing /frontend mount. |
| 10 | CKL schema and benchmark JSON | 35,811 | 0.036 | Package data matched by the CKL package-data rule. No meaningful bundle reduction. |

The exact tracked package-data matches declared in pyproject.toml total 70,011,277 bytes before the generated CKL index: 15,198,923 bytes for CKL manifest/objects/schema/benchmarks; 39,947,799 bytes for lexical data/schema; 13,265,593 bytes under bhf_agent/data; and 1,598,962 bytes for web templates/static. These groups are source-side package-data matches, not a claim that every byte is duplicated in the final function.

### Dependencies and final bundle accounting

The Vercel log says it installed required dependencies from pyproject.toml using uv 0.10.11 and force-bundled two packages without compatible wheels, both logged as cffi. The four declared runtime dependencies are:

| Runtime package | Constraint |
|---|---|
| fastapi | >=0.115,<0.116 |
| jinja2 | >=3.1,<4 |
| python-multipart | >=0.0.9 |
| uvicorn | >=0.30,<0.35 |

The optional dev and gui extras are not declared as runtime dependencies. The build-system requirements setuptools and wheel are separate from the four project runtime dependencies. There is no root uv.lock or equivalent Python lock file, so this commit does not pin Vercel's resolved versions. A prior local Python 3.12 inventory measured 16,000,116 bytes across the direct runtime dependency closure and 15 distributions; that is a local reference, not the Vercel dependency footprint. The deployment log provides no cffi parents, paths, or per-package sizes.

| Final attempted function measurement | Size |
|---|---:|
| Before Vercel dependency optimization | 340.46 MB |
| After Vercel dependency optimization | 308.39 MB |
| Enforced on this deployment | 225 MB |
| Remaining excess | 83.39 MB |

Retained source plus one generated CKL index total about 190.51 MB, leaving a rough 117.88 MB difference from the 308.39 MB optimized bundle. That difference is not an exact dependency measurement: it may include Python runtime files, dependency files, generated bytecode, traced files, and/or copies introduced during packaging. The function artifact was not available to separate them.

## 3. Root cause and CKL data path

### Root cause

The root cause is a single Python function whose combined application source, runtime dependencies, reader assets, and build-generated CKL index exceed the limit actually enforced for this project. This is supported by the failed deployment log and by the earlier NE6R2 failure. Vercel's own Python runtime documentation states that Python has no automatic dead-code tree shaking and recommends explicit file exclusions and runtime-only dependencies; the source rules already exclude most development and authoring data.

The oversized CKL SQLite database is the largest single known file, but the deployment log does not prove that it is the sole or even largest source of the 83.39 MB excess. The separate lexical gzip database is another large runtime asset. Dependency optimization already removes 32.07 MB and still leaves the function over limit. The repeated cffi bundling and lack of an artifact manifest leave the residual unattributed.

### CKL build, runtime, and duplication

framework.canonical_library.vercel_build builds from the checked-out framework/canonical_library/manifest.json and objects/ tree, writes the index to framework/canonical_library/data/ckl.sqlite, and runs verify_database against those same sources before the build succeeds. The deployment log reports 687 objects, 2,329 claims, 5,232 sources, and 1,297 evidence rows, along with the expected inventory fingerprint 90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6, source manifest fingerprint e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40, and source inventory signature 5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea.

The shared VerifiedCKLProvider uses the SQLite repository for retrieval and also validates the packaged JSON manifest and object inventory. On Vercel it requires SQLite, read-only access, required identity metadata, matching source fingerprints/signatures, and fail-closed behavior. It does not rebuild or fall back to JSON. The source JSON and SQLite index are semantically overlapping representations, but both are required by the current runtime verification contract.

The generated database path is covered both by includeFiles = "framework/canonical_library/**" in vercel.json and by the setuptools data/*.sqlite package-data pattern in pyproject.toml. These rules overlap on the same source path; that alone does not mean two physical copies are emitted. The CKL JSON paths similarly match both the broad includeFiles glob and the package-data rule. No second database path or byte-identical duplicate CKL JSON/database file was found in the Git inputs. Whether Vercel also carries an installed-project copy in addition to the included source files is unconfirmed because the failed function file tree is unavailable.

A prior read-only allocation report on the source-verified 116,334,592-byte CKL index found 55,439,360 bytes of table pages, 60,866,560 bytes of index pages, 28,672 unassigned allocated bytes, and zero free pages. Indexes account for about 52.3% of the database. VACUUM has no free pages to reclaim. The existing keyword indexes are part of the required retrieval schema; any index change is a separate, explicitly approved database proposal and is not part of this recommendation.

### Historical and retired assets

- .bhf-data/**, including Commentary authoring/candidate history and freeze evidence, is already excluded from Vercel source inputs. docs/**, tests, scripts, and tools are also excluded. Those records remain in the Git tree.
- The generated BHF Commentary v1.2 reader payload under bhf_agent/data/commentary-v1.2/ is already absent after NE7R3 and must not be restored or counted as a new reduction. The separate Tyndale Study Notes service under framework.commentary, /api/commentary/*, and its reader assets remain supported and must stay.
- The freeze record's .bhf/ckl.sqlite byte hash discrepancy remains documented: the frozen 19c66f… value differs from the locally recorded 847960… database hash, while the latter has the source inventory identity 90fa7547…. It is unrelated to bundle size and must not be rewritten as a packaging fix. This investigation did not rebuild the protected database, edit CKL records, or run/advance the Commentary v1.1 pipeline.

## 4. Remediation options by safety, effect, and complexity

| Rank | Option | Measured or estimated size effect | Safety | Complexity | Assessment |
|---:|---|---:|---|---|---|
| 1 | Preview-only Vercel Large Functions opt-in, if the project is eligible | No reduction; current 308.39 MB is below the documented 5 GB Large Functions ceiling | Very high: no source data or runtime behavior changes | Low to moderate: verify account/project requirements and Preview-scoped settings | Recommended first. The failed build proves Large Functions was not active/effective for that deployment. Confirm Fluid Compute, Active CPU, plan eligibility, Secure Compute/Static IP exclusions, and billing before use. |
| 2 | Externalize only the immutable CKL SQLite index; keep manifest and all 687 JSON objects packaged | One visible DB copy is 116.335 MB. Arithmetic estimate: 308.39 − 116.335 ≈ 192.06 MB, about 32.94 MB below the 225 MB limit (14.6% margin). Actual savings require analyzer confirmation. | High if asset version/hash is pinned, verified before use, and the existing source checks/read-only provider contract remain | Medium to high: versioned asset publication, cold-start fetch/cache, checksum verification, and provider path support | Best standard-limit fallback. It preserves runtime recomputation of source fingerprints from bundled JSON and does not reduce evidence or indexes. |
| 3 | Externalize CKL SQLite plus source JSON as one immutable CKL asset set | Known inputs total 131.498 MB. Arithmetic estimate: about 176.89 MB, 48.11 MB below 225 MB (21.4% margin), assuming one copy of each. | High only if the external manifest and data are pinned and all source attestations are still checked | High: source-root materialization, attestation validation, atomic /tmp caching, offline study-pack behavior, and cold-start checks | Provides more headroom, but changes more of the provider's current source-verification path. Consider only if Large Functions is unavailable or the DB-only path misses the analyzer target. |
| 4 | Narrow the broad CKL includeFiles glob to a verified allowlist | Unmeasured. The entire checked-in CKL tree is 16.220 MB before the generated DB; 15.199 MB is manifest/object/schema/benchmark package data needed or plausibly needed by the current provider. Clearly optional schema/benchmark files total only 35.8 KB. | Medium until file tracing proves all imports/resources remain available | Low to moderate | Correct as a follow-up hygiene change, not a standalone size fix. It cannot explain or safely save 83.39 MB. |
| 5 | Remove duplicate packaged copies | No physical duplicate proven. Prior exact content hashing found at most 151,625 bytes in extra copies across tracked files; several are served under distinct URLs. | Medium after route/path verification | Low to moderate | Negligible even if every copy were safely removable. The overlapping setuptools/includeFiles rules are not proof of duplicate artifacts. |
| 6 | Trim Python dependencies | Local direct runtime closure was 16.000 MB; Vercel's exact dependency/runtime size and cffi parent packages are unknown | High only for dependencies proven unused in the actual runtime | Moderate | No direct dependency is proven unused. Even the whole local closure is too small to explain the gap, and the Vercel trace is required before removal. |
| 7 | SQLite compression/index/schema changes | No approved or measured safe reduction. Prior DB has zero free pages; one suspected redundant index represented 7.594 MB but has not been proven removable without retrieval/performance impact. | Low until separately reviewed | High | Do not include in the minimal implementation. This requires the explicit separate database proposal requested by the user. |

The lexical gzip asset is not an unused build artifact: the runtime materializes it on first lexical lookup. Historical files and development artifacts are already excluded. Removing these would either provide no new savings or remove supported reader behavior.

## 5. Recommended minimal implementation

1. Keep the merged NE7R3 code, CKL records/index schema, shared provider, translations, maps, Tyndale Study Notes, offline behavior, retired Commentary endpoint responses, and master deployment setting unchanged.
2. Before modifying Vercel settings, verify the project/team's Large Functions eligibility and billing implications. Vercel documents up to 5 GB for Node.js/Python Large Functions on Fluid Compute, enabled for existing projects with VERCEL_SUPPORT_LARGE_FUNCTIONS=1; its build troubleshooting guidance recommends VERCEL_ANALYZE_BUILD_OUTPUT=1 for package analysis. The current 225 MB result remains the active limit until an eligible Preview build proves otherwise.
3. If eligible and approved, run one Preview-only build with both variables scoped to Preview. Record the analyzer output, confirm Vercel recognizes Large Functions, and run the acceptance checks below. Do not change Production scope or re-enable automatic master deployment.
4. If Large Functions is unavailable or the 225 MB limit must be retained, design a versioned immutable CKL SQLite asset outside the function bundle. Keep all JSON source objects in the function, and have the existing shared provider use a locally cached, atomically materialized database only after verifying its pinned hash, database integrity, source manifest, source signature, and inventory fingerprint. The provider must remain read-only, single-flight, and fail-closed on Vercel. The target should be at most 200 MB (25 MB below the measured cap); the simple subtraction estimate is about 192.06 MB but is not an artifact measurement.
5. If the actual analyzer shows insufficient margin, stop and separately design externalization of the JSON source inventory. Do not remove the source attestations to fit the bundle. Any database size/index work remains a separate proposal requiring explicit approval.

The current single-function package cannot deploy under its enforced 225 MB limit. It is comfortably below the documented 5 GB Large Functions limit if the project qualifies. Under the 225 MB path, CKL database externalization is a plausible architecture with estimated headroom, but only an analyzer-backed Preview build can establish that it actually fits. The source-file exclusions alone do not provide a safe, sufficiently large reduction.

## 6. Acceptance checks required before a deployment is accepted

### Bundle and deployment

- Preview analyzer output identifies the function's largest files, dependencies, generated bytecode, and any installed-project duplicates.
- If using Large Functions, Vercel reports the Preview deployment READY, recognizes Large Functions, and the function is below 5 GB. If retaining the standard limit, the measured function is at most 200 MB, leaving at least 25 MB below the deployment's 225 MB cap.
- vercel.json keeps automatic master deployments disabled. No production setting changes are made during Preview validation.

### CKL integrity and provider behavior

- Build or materialize the index without touching .bhf/ckl.sqlite; verify PRAGMA integrity_check = ok, no foreign-key errors, and required indexes.
- Verify the exact counts: 687 CKL objects, 2,329 claims, 5,232 sources, and 1,297 evidence rows.
- Compare the index's inventory fingerprint, source manifest fingerprint, and source inventory signature with the corresponding immutable source inputs and pinned build attestation.
- Confirm the shared provider is SQLite-backed, read-only/query-only, single-flight, fail-closed on missing/stale/modified assets, and does not rebuild or fall back to JSON on Vercel. Exercise a CKL retrieval and a Narrative Explorer request through that same provider.

### Reader and retirement regressions

- Run the existing focused suites: tests/test_vercel_ckl_index.py, tests/test_verified_ckl_provider.py, tests/test_ckl_provider_consumers.py, tests/test_narrative_explorer_api.py, tests/test_narrative_explorer_map_matching.py, tests/test_commentary_retirement.py, tests/test_translation_registry.py, tests/test_notes.py, tests/test_optional_offline_pack_runtime.py, tests/gui/test_maps.py, and tests/gui/test_notes_highlights.py.
- Confirm Tyndale Study Notes still work through /api/commentary/*; the retired generated Commentary routes still return their established HTTP 410 feature_retired response; Compare Translations remains usable.
- Install and reload Study and Maps offline packs; exercise offline Bible translation access, maps, notes/highlights, and persisted saved work.
- Confirm Maps/geography, archaeology, Narrative Explorer, and lexical lookup still work, including the lexical gzip extraction to the supported runtime directory.
- Verify historical v1.2 freeze records and the documented CKL fingerprint discrepancy are unchanged. Do not run any Commentary regeneration or v1.1 pipeline stage as part of this acceptance work.

These are future acceptance requirements, not tests run by this investigation. No implementation, database rebuild, deployment, push, merge, or authoring pipeline operation was performed.

## References

- [Vercel Python runtime and bundle controls](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Large Functions changelog](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistvS/eadf06d6c3)
- [Vercel function size troubleshooting](https://vercel.com/kb/guide/troubleshooting-function-250mb-limit)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)
- [Earlier source and SQLite allocation inventory](../ne6r3/01-bundle-size-inventory.md)
- [NE7R3 CKL fingerprint discrepancy record](../ne7r3/02-ckl-fingerprint-investigation.md)
- [NE7R3 reader preservation results](../ne7r3/04-reader-regression-results.md)
