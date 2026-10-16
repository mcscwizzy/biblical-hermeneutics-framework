# NE-6R2 — Vercel CKL Index Build Design

## Supported deployment path

The repository's Vercel integration uses the Python/FastAPI runtime. Current Vercel documentation describes project build hooks for FastAPI in `pyproject.toml`; the documented `[tool.vercel.scripts].build` hook runs before function packaging. Python function `includeFiles` patterns are configured per function in `vercel.json` and are relative to the project root. The Python runtime documentation also describes the uncompressed function bundle limit. See [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json), and [Python runtime limits](https://vercel.com/docs/functions/runtimes/python).

The repository now declares the build hook:

```toml
[tool.vercel]
entrypoint = "bhf_web.app:app"

[tool.vercel.scripts]
build = "python -m framework.canonical_library.vercel_build"
```

`framework.canonical_library.vercel_build` builds from the checked-out `framework/canonical_library` JSON inventory into `framework/canonical_library/data/ckl.sqlite`. It does not inspect or copy `.bhf/ckl.sqlite` or any `.bhf-data` contents. It invokes the normal deterministic database builder, then verifies database integrity and the source inventory identity before returning success. A failure propagates as a failing build.

The function's explicit `includeFiles` list packages the generated SQLite file, `manifest.json`, and `objects/**/*.json`. The CKL JSON remains the authoritative source and remains present for runtime freshness checking. `.vercelignore` excludes `.bhf-data/**`, `.bhf/`, environment files, local configuration, caches, tests, and docs from ordinary deployment inputs. Explicit CKL includes do not add local state.

## Runtime contract

When `VERCEL=1`, repository selection resolves the SQLite path deterministically relative to the installed package at `framework/canonical_library/data/ckl.sqlite`. It requires SQLite, read-only access, an `error` stale-index policy, the package-owned source root, expected manifest/inventory identity, and supported schema/retrieval versions. Conflicting backend, path, or source-root overrides fail. Missing index is a clear error. The Vercel branch never falls back to JSON and never calls the builder or performs a migration during an HTTP request.

The existing local and Docker configuration behavior remains available outside Vercel. CKL source objects, evidence relationships, manifest, schema, and inventory fingerprints were not modified. The local runtime proof confirms selection of `SQLiteCanonicalLibrary` backed by `SQLiteCanonicalRepository`, `read_only=True`, `PRAGMA query_only=1`, successful read-only Genesis 2:8 retrieval, rejected write attempts, unchanged database SHA, and no JSON repository construction.

## SQLite publication and runtime writes

The normal builder originally left a WAL journal mode. A read-only runtime open then created `-wal` and `-shm` sidecars even though the database content did not change. The builder now checkpoints the WAL and switches the fully built file to `journal_mode=DELETE` before closing and atomically publishing it. The regression test opens the packaged database through the strict read-only runtime, performs retrieval, confirms the directory still contains only `ckl.sqlite`, and confirms the file SHA remains unchanged. This change preserves the schema and records while preventing runtime sidecar writes.

## Build identity and reproducibility

Build identity is stored with the index and checked against the same source root: the CKL inventory fingerprint, manifest fingerprint, full JSON source-inventory content signature, database schema version, retrieval-index version, record counts, required indexes, SQLite `integrity_check`, and `foreign_key_check`. The package build command used the committed JSON files and can reproduce the index independently of a developer's `.bhf/` database. The exact observed identity and proof are in [integrity and parity](03-index-parity-and-integrity.md).

The full inventory check reads the source JSON and can be expensive on a cold function filesystem. In one Firefox run it took 7.1 seconds inside a 9.4-second Narrative Explorer server wait; the direct benchmark measured about 260 ms. This is evidence for the need to measure the deployed cold path, not a reason to remove the integrity check. It did not explain the separate historical first Maps delay.

## Vercel artifact validation boundary

The Vercel CLI is not installed or available in the local package cache, the worktree has no linked `.vercel` project, and project settings or secrets were not fetched. Therefore the supported project-owned build hook and index generator were run and inspected locally, but `.vercel/output` and the actual function bundle could not be produced or inspected. `includeFiles` is configured and covered by tests; this local evidence does not prove that an actual Vercel function artifact contains the file. No preview or production deployment was authorized or made. The release disposition is `VALIDATION_PENDING` pending a supported Vercel artifact build and, if function cold-start behavior must be measured, explicit authorization for a preview deployment.
