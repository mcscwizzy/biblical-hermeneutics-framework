# NE-6R2 — Vercel Build Artifact Validation

## Local source-built artifact

The project-owned command `python -m framework.canonical_library.vercel_build` completed locally using the checked-out CKL JSON sources. It generated `framework/canonical_library/data/ckl.sqlite`, then ran `verify_database` against the same source root. The observed artifact was 116,334,592 bytes with SHA-256 `0f7552f335ca88acf0a1ea1e49cdbf6a76b1e550191dc89d7e2ff742e76737c9`. It reported 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, schema version 4, retrieval version 3, inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`, manifest fingerprint `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`, and source-inventory signature `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea`.

After the strict local Vercel runtime selection and retrieval proof, the package data directory contained only `ckl.sqlite`; the artifact hash remained unchanged. No database binary is tracked. Build and runtime never read the developer's `.bhf/ckl.sqlite`.

## Configured function inputs and size estimate

`vercel.json` configures `bhf_web/app.py` with explicit includes for:

- `framework/canonical_library/data/ckl.sqlite`
- `framework/canonical_library/manifest.json`
- `framework/canonical_library/objects/**/*.json`

The included CKL SQLite file plus source inventory total approximately 131,497,704 uncompressed bytes (about 125.4 MiB). This is only the measured CKL input set; it excludes Python runtime, dependencies, and other FastAPI function files. It is below the current documented 500 MB uncompressed Python function limit, but the complete function bundle size is unknown until a Vercel artifact is generated. The source files remain bundled for fingerprint verification. `.vercelignore` excludes `.bhf-data/**`, `.bhf/`, `.env*`, `local.config.json`, build caches, and tests/docs; no credentials or production environment values were pulled into the local artifact.

## Build order and runtime proof

The supported FastAPI project build hook is declared in `pyproject.toml` as `python -m framework.canonical_library.vercel_build`. It writes into the same package-owned path referenced by `includeFiles`, verifies identity before succeeding, and only then does Vercel package the Python function according to its documented build flow. The runtime resolver uses that path deterministically and opens SQLite read-only. Missing or stale artifacts fail closed; runtime rebuilding and JSON fallback are prohibited on Vercel.

Local runtime proof selected `SQLiteCanonicalRepository` at the expected package path, retrieved eight Genesis 2:8 CKL results, refused writes, did not construct `JsonCanonicalRepository`, and did not change the database bytes or create SQLite sidecars. Focused tests cover missing, stale, schema, manifest, backend override, and path override failures. These checks establish the application behavior against the locally generated artifact.

## Actual Vercel artifact gap

`vercel` was absent from `PATH`; `npx --offline --yes vercel --version` could not resolve a cached package (`ENOTCACHED`). The worktree has no `.vercel` project metadata. No project linking, settings, secrets, or environment variables were fetched. Therefore `vercel build` could not produce `.vercel/output`, and there is no actual generated Vercel function artifact to inspect for final file inclusion, total bundle size, build ordering, or runtime module loading. Configuration tests prove the declarations, not the packaged artifact.

No preview or production deployment was made. The exact remaining validation is a local supported `vercel build` artifact check when the CLI is available without linking or fetching secrets. If hosted function cold-start validation is required, status remains `VALIDATION_PENDING` until separate explicit preview authorization. No production deployment is in scope.

## Official platform references

- [FastAPI build configuration and project hooks](https://vercel.com/docs/frameworks/backend/fastapi)
- [Function `includeFiles` project configuration](https://vercel.com/docs/project-configuration/vercel-json)
- [Python function runtime limits](https://vercel.com/docs/functions/runtimes/python)
- [Local Vercel Build output](https://vercel.com/docs/cli/build)
