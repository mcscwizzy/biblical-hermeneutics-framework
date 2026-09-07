# Vercel Function Bundle Audit

Audit date: 2026-09-06
Branch: `feat/commentary-v1.1-expansion`
Audited HEAD: `dd62adf70a0461a74d0769bf46f77b8db191c068`
Remote HEAD after fetch: `dd62adf70a0461a74d0769bf46f77b8db191c068`

## Before

The reported Vercel preview for `defde4d` measured approximately:

| Measurement | Bytes | Reported size |
| --- | ---: | ---: |
| Raw function bundle | 388,830,000 | 388.83 MB |
| Optimized function bundle | 397,270,000 | 397.27 MB |
| Allowed limit | 225,000,000 | 225 MB |

The local Vercel CLI is unavailable and this checkout has no `.vercel` project link, so no authenticated preview was attempted.

## Bundle composition

The checkout is 873,668,608 bytes. Tracked source is 326,992,985 bytes. The largest relevant populations are:

| Category | Bytes | Runtime classification |
| --- | ---: | --- |
| Tracked Commentary v1.1 scale candidate/audit work | 277,421,720 | `CANDIDATE/AUDIT_ONLY` |
| Local `.bhf` databases | 298,057,728 | `DEVELOPMENT_ONLY`, ignored by Git |
| Local `.venv` | 96,014,336 | `DEVELOPMENT_ONLY`, ignored by Git |
| Local `build/` | 32,866,304 | generated, ignored by Git |
| CKL JSON and source | 15,215,805 | `REQUIRED_AT_RUNTIME` |
| `bhf_agent/data` Bible and related data | 13,265,644 | `REQUIRED_AT_RUNTIME` |
| `framework` application/source tree | 16,144,027 | `REQUIRED_AT_RUNTIME` |
| `bhf_agent` application/source tree | 16,550,947 | `REQUIRED_AT_RUNTIME` |
| `bhf_web` application/source tree | 2,446,777 | `REQUIRED_AT_RUNTIME` |
| Certified Commentary v1.1 runtime corpus | 4,255,616 | `REQUIRED_AT_RUNTIME` |
| Legacy commentary compatibility corpus | 1,566,726 | required for explicit legacy release override |
| Tests | 9,507,043 | `TEST_ONLY` |
| Documentation | 550,647 | `DOCUMENTATION_ONLY` |
| Tooling used by the internal coverage route | 1,402,241 | `REQUIRED_AT_RUNTIME_FOR_INTERNAL_COVERAGE_ROUTE` |

The full working-tree candidate directory is 286,607,295 bytes. The certified runtime corpus contains 1,190 JSON files: 1,189 chapters plus its manifest, totaling 4,255,616 bytes.

## Root cause

The oversized package is dominated by tracked Commentary v1.1 generation/audit history, not by the certified runtime corpus. The candidate workspace contains repeated preflight manifests/reports, evidence bundles, Terra inputs/outputs, remediation records, quarantine/recovery artifacts, and certification history. Its tracked size alone is 277,421,720 bytes.

The existing `vercel.json` setting is valid for the Python runtime and is attached to the `bhf_web/app.py` function:

```json
"excludeFiles": ".bhf-data/bhf-commentary-candidates/**"
```

However, the reported preview still retained enough source to produce a 397.27 MB optimized function. Function-level tracing is therefore insufficient as the source-upload boundary for this repository. The narrow fix is a root `.vercelignore` entry for the proven candidate/audit workspace, with explicit exclusions for other non-runtime source. No broad `.bhf-data/**` exclusion is used.

## Runtime dependency proof

The production entrypoint is `bhf_web/app.py`, exposing the FastAPI `app`. Runtime paths are resolved by `bhf_agent/runtime_paths.py`.

| Path | Classification | Proof |
| --- | --- | --- |
| `.bhf-data/bhf-commentary-v1.1` | `REQUIRED_AT_RUNTIME` | Default `commentary-v1.1` package path; 1,189 chapter files and manifest remain present. |
| `.bhf-data/bhf-commentary` | `REQUIRED_AT_RUNTIME_FOR_LEGACY_RELEASE_OVERRIDE` | Explicit legacy release remains supported and is not ignored. |
| `.bhf-data/bhf-commentary-candidates/**` | `CANDIDATE/AUDIT_ONLY` | Runtime resolver never selects it; generation/audit code only. |
| `bhf_agent/data/asv_bible.json`, `kjv_bible.json` | `REQUIRED_AT_RUNTIME` | Bible loaders resolve these package-local datasets. |
| `framework/canonical_library/objects/**`, manifest, schema | `REQUIRED_AT_RUNTIME` | CKL JSON fallback is the production-safe source when the ignored local SQLite DB is absent. |
| `bhf_web/templates/**`, `bhf_web/static/**`, `frontend/**` | `REQUIRED_AT_RUNTIME` | App mounts templates/static/frontend paths. |
| `.bhf/**`, `.venv/**`, `build/**` | `DEVELOPMENT_ONLY` | Ignored local state, environment, and generated build output; none are required by the Vercel source tree. |
| `tests/**`, `docs/**`, `scripts/**`, `mobile/**` | test/development/documentation only | No production import or runtime lookup path reaches them. |
| `tools/**` | `REQUIRED_AT_RUNTIME_FOR_INTERNAL_COVERAGE_ROUTE` | The internal coverage API lazily imports `tools.commentary_health_report` and `tools.ckl_coverage_report`; it remains available to the deployment. |

The local staged tree retained all required paths and passed health, commentary, Bible, and startup checks. Its runtime commentary path was `bhf-commentary-v1.1`, with no candidate workspace dependency.

Lexicon handling is unchanged: `framework/lexical/database/lexicon.sqlite` is not tracked, while the local `.bhf/lexicon.sqlite` is ignored development state. The application’s lexicon diagnostics safely report the database as unavailable when it is absent. No lexical database was removed by this packaging change and no external download was introduced.

## Dependency audit

`pyproject.toml` declares only the production dependencies `fastapi`, `jinja2`, `python-multipart`, and `uvicorn`. Their locally resolved production dependency closure is approximately 10,747,416 bytes across 14 packages. The largest components are Pydantic (3,790,013 bytes), Jinja2 (1,174,184 bytes), FastAPI (1,130,177 bytes), and Uvicorn (463,508 bytes).

The local GUI/development environment also contains approximately 35,610,420 bytes across direct dev/GUI packages, led by Selenium at 27,779,740 bytes. `requirements-gui.txt` is a compatibility entry point for local GUI testing, not production; it is now excluded from the Vercel source. `cffi` is not declared in the production dependency set and is not in the local production closure. The Vercel warning that it was force-bundled must still be observed in the next preview, but it cannot account for the approximately 397 MB package by itself.

No `pyproject.toml` dependency change was needed. Production/dev separation already exists; the Vercel source exclusion prevents the GUI requirements entry point and its development dependency graph from being selected by the deployment build.

## Changes

Added a root `.vercelignore` with narrow, evidence-backed entries for:

- `.bhf-data/bhf-commentary-candidates/**`
- local `.bhf/`, `.venv/`, generated `build/`, `dist/`, pytest cache, and Python bytecode
- `tests/**`, `docs/**`, `.github/**`, `mobile/**`, and `scripts/**`
- `requirements-gui.txt`, `Dockerfile`, and local Docker Compose files

The existing function-level `excludeFiles` setting remains in `vercel.json` as a second protection. Certified runtime data, CKL data, Bible data, templates, static assets, frontend assets, application source, and the legacy-compatible commentary corpus are not excluded.

## After

A Git-like staged deployment tree was built from tracked files and the proposed exclusions:

| Measurement | Bytes | Approximate size |
| --- | ---: | ---: |
| Staged source/runtime tree | 37,417,268 | 37.42 MB |
| Production dependency estimate | 10,747,416 | 10.75 MB |
| Combined projected source + dependency estimate | 48,164,684 | 48.16 MB |

This is a repository-side projection, not a Vercel-authoritative optimized function measurement. The observed Vercel preview includes platform/runtime packaging overhead, so the next authorized preview remains required.

External release evidence for `dd62adf` subsequently reported the Vercel
preview as `READY`; the application root returned HTTP 200 and exposed
`commentaryRelease: commentary-v1.1`. The exact post-hardening raw and
optimized function sizes were not exposed in the available deployment logs.

## Tests and smoke checks

Focused packaging tests currently pass: 9 passed, including:

- exact 1,189-chapter canonical runtime count and release fingerprint
- law/Torah, narrative, poetry, wisdom, prophecy, Gospel, epistle, and apocalyptic representative lookups
- Deuteronomy 32, Numbers 6, Isaiah 40, and Psalms 119 lookups
- CKL/Bible/runtime-path packaging guards
- explicit candidate-workspace independence
- FastAPI startup and health endpoint checks

The staged tree also passed a local ASGI smoke check for health, the four remediated commentary chapters, Bible Genesis 1, lexicon diagnostics, and the internal commentary coverage API (`Genesis 1`). The lexicon result was the expected safe-unavailable state because no production lexicon SQLite file is tracked.

The completed focused release/API groups were 9 + 31 + 15 + 64 + 10 passing tests, with one documented skip and 10 passing subtests. A combined group that also included the slower `tests/test_web_app.py` was stopped after 128 passed, 1 skipped, and 10 passing subtests in 200.97 seconds; it produced no failure, and the isolated CKL/Bible/lexicon group completed separately. `tests/test_web_app.py` was not allowed to run indefinitely. No commentary generation, CKL mutation, or evidence operation was performed.

## Integrity

- Pipeline: `CORPUS_COMPLETE`
- Certified eligible chapters: 935
- Runtime chapters: 1,189
- Runtime fingerprint: `fc905f3a095fd14bb5f557af624f3e40984bd67ee095477b5966eee3aea33b66`
- Runtime corpus bytes: 4,255,616
- CKL changes: none
- Commentary prose regeneration: 0
- Required runtime assets remain present in the staged tree
- Master was not merged
- No release tag was created
- No branch was deleted

The machine-readable inventory is [vercel-function-bundle-audit.json](vercel-function-bundle-audit.json).

## Preview handoff

The next authorized preview should run from the final commit on `feat/commentary-v1.1-expansion` and capture raw/optimized function sizes, build warnings (including `cffi`), startup, and representative commentary/CKL/Bible lookups. The repository-side package is prepared for that verification.
