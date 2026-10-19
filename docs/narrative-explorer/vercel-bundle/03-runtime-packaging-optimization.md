# Runtime Packaging Optimization

- Date: 2026-10-18
- Project: `mcscwizzy/biblical-hermeneutics-framework` (`prj_15SaSVJykrPDrncFg6jehwGzr3j9`)
- Branch: `investigation/vercel-lambda-size-2026-10-17`
- Baseline revision and failed Preview: `551a998f5c40d6cb4d5e8a1f41db1bfe8f307096`, `dpl_CEpyVY4zmbv6wyV2dRss6CABkSMN`

## Finding and implementation

The failed Preview's analyzer measured `/fastapi` at **363.85 MB** and rejected it at the **250 MB** sandbox limit. Its build log first said `Function "bhf_web/app.py" exceeds the standard size limit; enabling large functions (beta)`, then failed with `NOW_SANDBOX_WORKER_MAX_LAMBDA_SIZE`. The Large Functions flag reached the Python builder; the reason the later sandbox stage enforced 250 MB is still unknown.

The packaging duplication has a reproducible cause. Vercel's Python builder invokes `uv sync --no-dev --no-editable` against this repository's `pyproject.toml`. With a build system declared, uv builds and installs the project itself in addition to the four runtime dependencies. Setuptools produces `build/lib` during that build. Vercel gathers application files after dependency installation, so the source-upload `.vercelignore` rule for `build/` does not remove this newly generated directory. The builder then mirrors installed distributions into `_vendor`, including the installed BHF package. The function therefore carries checked-out source, `build/lib`, and a second installed project package. [Vercel's Python builder](https://github.com/vercel/vercel/blob/main/packages/python/src/index.ts), [uv sync implementation](https://github.com/vercel/vercel/blob/main/packages/python/src/uv.ts), and [uv virtual-project setting](https://docs.astral.sh/uv/concepts/projects/config/) explain the stages.

Two changes address the cause:

1. `vercel.json` now applies the single brace glob `"{.bhf-data/bhf-commentary-candidates/**,build/**}"` through `excludeFiles` on `bhf_web/app.py`. The current Vercel schema requires one glob string, and Vercel's function guidance documents brace alternation for grouping exclusions. The local `build/lib` artifact matches the `build/**` arm; CKL SQLite and lexical runtime paths do not match either arm. Vercel's Python builder applies this pattern when it globs the post-install work tree, after `.vercelignore` has been applied to the original upload. The broad CKL `includeFiles` rule and `git.deploymentEnabled.master = false` remain.
2. `pyproject.toml` now sets `[tool.uv] package = false`. uv still resolves and installs the declared runtime dependencies, but it does not build or install BHF during Vercel's sync. Checked-out source remains the application's import and asset root. This uv setting does not change the setuptools wheel or source distribution contracts; a fresh wheel and sdist were built and inspected.

No import path, runtime asset path, CKL record, retrieval index schema, application route, or Python distribution package-data rule changed. `MANIFEST.in` and setuptools package-data remain appropriate for separately distributed wheels and source archives. The CKL `includeFiles` glob overlaps the normal source glob, but the builder's file map is keyed by path; this is not evidence of a second physical CKL copy. It remains in place because it includes the build-generated SQLite index.

## Confirmed copies and limits of the evidence

| Item | Evidence | Conclusion |
|---|---|---|
| `build/lib` | The local tree has 1,049 files and 73,887,548 bytes. Every file has a byte-identical source counterpart. uv 0.10.11 recreates the same size from the baseline metadata. | Confirmed redundant build copy; now excluded from the function and not created by the optimized uv sync. |
| Installed BHF package | Baseline uv sync installs 73,887,548 bytes of `framework`, `bhf_agent`, and `bhf_web` into site-packages, plus 149,662 bytes of project dist-info. Optimized sync installs none of those. Vercel's builder mirrors installed distributions into `_vendor`. | Confirmed local duplicate and confirmed Vercel mechanism. The failed deployment's `_vendor` tree cannot be hashed directly because its file-tree API returns 404. |
| Lexical archive | `framework/lexical/database/lexicon.sqlite.gz` is 39,946,432 bytes and has the same SHA-256 (`76c393b6…5e6ccff6250ea0ff`) in source, `build/lib`, and the baseline installed package. The optimized source import resolves it. | Confirmed three local copies before optimization; only the source copy is needed by the deployed app. |
| CKL JSON | `manifest.json`, a sampled `objects/books/genesis.json`, and the complete `build/lib` tree match source by hash. The baseline installed package carries the same project files. | Confirmed local duplication, while one source inventory remains required for runtime freshness verification. |
| CKL SQLite | The 116,334,592-byte `framework/canonical_library/data/ckl.sqlite` is generated after dependency installation. The source tree and installed package made before this step contain no CKL SQLite index. | One required generated index is confirmed locally; the analyzer's 110.95 MB entry is the same asset in MiB-scale reporting, not proof of another copy. |
| `includeFiles` | The CKL glob covers source JSON and the generated index, while the Python builder also collects app files. | Overlapping selection rules are confirmed; duplicate physical output from this overlap is unproven. |
| `_vendor/pip/_vendor` | The analyzer lists 7.53 MB. Vercel's dependency externalizer can ship runtime installation tooling. | Its removability is unproven; it was retained. |

Runtime imports and filesystem paths were checked in a copy of the optimized project using only the 15 third-party distributions installed by uv. CKL, lexical, and Bible modules imported from checked-out source; the lexical gzip, ASV/KJV JSON, web service worker, and generated CKL SQLite index resolved. The shared provider opened the index read only and retrieved `genesis`. Removing the source CKL JSON, lexical gzip, translations, web assets, or Tyndale service would break supported behavior, so none was excluded.

## Size measurements

The local reproduction used the **same uv 0.10.11** version named in the failed build log, Python 3.12, and isolated copies of the deployment source under `/tmp`. It ran the builder's `--no-dev --no-editable` sync mode, then placed the verified CKL index in each copy. Both inventories exclude transient Python bytecode. They include source, generated index, `build/lib` when present, and installed site-packages; they omit Vercel's runtime wrapper and platform packaging overhead. These numbers are **not** a Vercel function measurement.

| Local uncompressed staging component | Baseline | Optimized | Change |
|---|---:|---:|---:|
| Source copy with generated CKL index and any `build/lib` | 264,850,893 B | 190,963,526 B | −73,887,367 B |
| Installed site-packages | 84,723,684 B | 10,686,474 B | −74,037,210 B |
| **Local staging total** | **349,574,577 B** | **201,650,000 B** | **−147,924,577 B** |
| `build/lib` alone | 73,887,548 B | 0 B | −73,887,548 B |
| Installed app package files alone | 73,887,548 B | 0 B | −73,887,548 B |

The one-stage `build/**` exclusion targets 73,887,548 local bytes if the build tree exists. The uv change independently removes the installed project copy and prevents that build tree from being made. The source-row difference is 181 bytes smaller than the build-tree size because the two `pyproject.toml` variants differ by 181 bytes. Their benefits overlap: **do not add the two stage reductions** to estimate the final function. The earlier 308.39 MB versus 225 MB result and the latest 363.85 MB versus 250 MB analyzer result come from different build stages and are not directly comparable. A fresh Preview must supply the actual post-change function size. The local 201.65 MB staging result makes the 250 MB gate plausible, but leaves unknown runtime and bytecode overhead; it does not establish the 200–210 MB engineering target.

## Verification

### Packaging, config, and runtime imports

- `vercel.json` parses as JSON and `pyproject.toml` parses as TOML. The current Vercel schema defines `excludeFiles` as one string glob; Vercel's function guidance shows brace alternation for grouped patterns. The configured pattern matches both the candidate workspace and generated `build/**` files while leaving `framework/canonical_library/data/ckl.sqlite` and `framework/lexical/database/lexicon.sqlite.gz` included. `git diff --check` passes. ([Vercel configuration reference](https://vercel.com/docs/project-configuration/vercel-json), [Vercel function guidance](https://github.com/vercel/vercel-plugin/blob/main/skills/vercel-functions/SKILL.md))
- A fresh setuptools wheel and sdist built successfully with `python -m build --no-isolation --wheel --sdist`. The wheel is **47,897,467 B** and the sdist **46,962,331 B**. Both contain the CKL manifest and Genesis object, lexical archive, ASV/KJV Bible JSON, Narrative Explorer static assets, and Tyndale service. The wheel's package entries total **73,887,548 B** uncompressed. The generated CKL SQLite index was intentionally built separately because it is a Vercel build output and is absent from the source tree before that build hook runs. The unchanged setuptools metadata emitted deprecation warnings for the license table and license classifier.
- With uv **0.10.11**, an offline `uv sync --no-dev --no-editable` against the optimized source checked **15 third-party packages** and installed no BHF distribution or BHF package directories into site-packages; no `build/lib` directory was created. uv reports that the project's console-script entry points are skipped because the project is not packaged. Vercel invokes the CKL build with `python -m framework.canonical_library.vercel_build`, and the app imports from checked-out source, so those entry points are not part of runtime startup.
- In that optimized source and environment, `bhf_web.app` imported with title `BHF Bible Reader`; CKL JSON, lexical archive, Bible JSON, service worker, and Tyndale source resolved. The generated SQLite index resolved at `framework/canonical_library/data/ckl.sqlite`; the Vercel-mode repository opened it read-only, retrieved `genesis`, and matched inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.

### Focused checks

- `tests/test_vercel_packaging.py` and `tests/test_vercel_startup.py`: **10 passed**.
- CKL Vercel index, verified provider, provider consumers, and Narrative Explorer API: **44 passed**.
- Frontend Node suite: **12 passed**, including Narrative Explorer, maps, backend routing, and service-worker contracts.
- A fresh disposable CKL index at `/tmp/bhf-vercel-artifacts-check/ckl.sqlite` passed the build-time structural and source-freshness verification. It is **116,334,592 B** and reports **687 objects, 2,329 claims, 5,232 sources, and 1,297 evidence rows**. Inventory fingerprint: `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`; source manifest fingerprint: `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`; source inventory signature: `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea`.

### Open local test failures

- **Pre-existing archaeology assertion:** `tests/test_notes.py::StudyDatabaseTests::test_archaeology_seed_and_passage_resolution_load_from_database` fails because a seeded site has `source_id == ""` (`tests/test_notes.py:224`). It fails both in the working tree and in an extracted, unmodified `551a998f5c40d6cb4d5e8a1f41db1bfe8f307096` baseline. Both runs used Python **3.12.3** and pytest **9.1.1**. The test, seed loader, and archaeology data are unchanged by this branch; this is a documented baseline failure.
- **Isolated Selenium timeouts:** `tests/gui/test_pwa_offline.py::test_pwa_reader_search_context_and_sync_status_work_offline` and `tests/gui/test_pwa_offline.py::test_clear_rebuildable_offline_cache_preserves_queue` time out while the async browser script awaits `BHFPWA.installOfflinePack`. The harness sets a **20-second** script timeout and runs a local loopback app in headless Chrome. The available run artifacts show the reader rendered and no browser-console error that explains the stall; the browser/driver build was not captured. The same two tests failed in an isolated rerun. The current audit shell has no `BHF_WEBDRIVER_URL`, Chrome, or ChromeDriver, so an additional baseline browser run is unavailable here. These tests and their app/offline assets are unchanged from the base commit. Classify these as isolated Selenium timeouts with an undetermined cause, not as a demonstrated packaging regression; keep offline browser acceptance open for Preview-only testing.

The protected `.bhf/ckl.sqlite` hash was `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182` before and after the checks. No CKL source inventory, protected database, credential, or unrelated source file changed. `git.deploymentEnabled.master` remains `false`; the Commentary v1.1 pipeline state remains `CORPUS_COMPLETE`.

## Large Functions entitlement

The project is on Hobby, `vercel.json` has `fluid: true`, Static IPs were previously observed disabled, and the failed Preview used Python 3.12/FastAPI. Project environment records show both `VERCEL_SUPPORT_LARGE_FUNCTIONS` and `VERCEL_ANALYZE_BUILD_OUTPUT` scoped to Development, Preview, and Production; their configured value is `1` per the project setting supplied for this task. The new build log proves the Large Functions flag was recognized by the Python builder, but the sandbox worker still enforced 250 MB. The available project/deployment APIs do not expose effective beta enrollment, Active CPU activation, or Secure Compute attachment. Project metadata says `framework: container` while source configuration says `fastapi`; no evidence establishes that this metadata difference caused the rejection. Vercel documents 250 MB standard, 500 MB Python, and up to 5 GB for eligible Large Functions with Fluid Compute and Active CPU; Secure Compute and Static IPs are excluded. [Functions limits](https://vercel.com/docs/functions/limitations), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [memory and CPU](https://vercel.com/docs/functions/configuring-functions/memory).

### Draft support request — do not submit without authorization

> Subject: Large Functions enabled in Python builder, then Preview rejected at 250 MB
>
> Project `biblical-hermeneutics-framework` (`prj_15SaSVJykrPDrncFg6jehwGzr3j9`), team `team_OIjeUT7LxEQvrDBdYmV8ysVP`, Hobby plan. Preview `dpl_CEpyVY4zmbv6wyV2dRss6CABkSMN` from branch `investigation/vercel-lambda-size-2026-10-17` failed at buildStep with `NOW_SANDBOX_WORKER_MAX_LAMBDA_SIZE`. The analyzer measured `/fastapi` at 363.85 MB and enforced 250 MB. The build log first said `Function "bhf_web/app.py" exceeds the standard size limit; enabling large functions (beta)`, then `Build Completed in /vercel/output`, followed by the sandbox rejection. The project has `fluid: true`; the build used Python 3.12; `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` and `VERCEL_ANALYZE_BUILD_OUTPUT=1` are configured for Preview. Static IPs appear disabled. Could you confirm this project's Large Functions beta entitlement, effective Active CPU and Secure Compute settings, whether Hobby and this Python/FastAPI build path qualify for the 5 GB limit, and why the sandbox still applied 250 MB? Project metadata reports `framework: container` while the repository config says `fastapi`; please clarify whether this affects the limit.

## Preflight and Preview outcome

The requested local preflight gates pass. The known archaeology failure reproduces on the unmodified base commit; the two browser-only offline-pack timeouts remain isolated and are eligible to stay open for Preview-only testing. The packaging changes are limited to the Vercel uv sync setting and function exclusion, with one focused packaging test update. No CKL SQLite externalization or architecture change was made.

The Vercel project is linked to `mcscwizzy/biblical-hermeneutics-framework`. Its previous deployment list contains no optimized commit. A push to this non-production branch should create a Preview through the existing Git integration; the remote deployment list will be checked before any manual deployment is considered. The single optimized Preview and hosted checks are pending.

For the Preview, record the exact deployment ID, URL, commit, target, final state, measured function size, analyzer output, and warnings. If it reaches READY, verify startup, CKL identity and integrity, Genesis 1 and Genesis 2:8 evidence, Narrative Explorer, Maps, Compare Translations, Tyndale Study Notes, Notes and Highlights where testable, retired Commentary routes returning HTTP 410, offline/service-worker behavior, and representative startup and response timings. Do not interpret the local 201,650,000-byte staging size as Vercel's function size or as production-readiness evidence.
