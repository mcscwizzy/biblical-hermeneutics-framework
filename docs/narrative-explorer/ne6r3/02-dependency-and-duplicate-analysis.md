# NE-6R3 — Dependency and Duplicate Analysis

## Vercel packaging inputs

`vercel.json` declares a FastAPI project with `fluid: true`. The single
configured Python function is `bhf_web/app.py`; its current settings are
`maxDuration: 60`, `includeFiles: "framework/canonical_library/**"`, and an
`excludeFiles` rule for a Commentary candidate path under `.bhf-data`.

The root `.vercelignore` already excludes all of `.bhf-data/**`, along with
`.bhf/`, `.venv/`, `build/`, `dist/`, `.pytest_cache/`, Python
`__pycache__`, tests, docs, scripts, mobile files, and GitHub workflow files.
Therefore the narrower Commentary-candidate `excludeFiles` rule currently
overlaps the broader `.vercelignore` exclusion. It is not an additional source
of byte savings for this Git deployment.

Vercel's Python runtime documentation says reachable project files are
included by default, Python is not tree-shaken, and `.pyc` files may be
generated during deployment. `includeFiles` explicitly adds every matching
file under the CKL directory. The retained-source manifest is not the same as
the function trace: `tools/`, `frontend/`, and other retained project paths
may not all be reachable from the function. The failed function artifact is
not available, so this audit does not equate all 2,306 retained Git files with
actual function contents.

## Runtime dependencies

The four base dependencies in `pyproject.toml` are:

| Declared runtime dependency | Version constraint |
|---|---|
| `fastapi` | `>=0.115,<0.116` |
| `jinja2` | `>=3.1,<4` |
| `python-multipart` | `>=0.0.9` |
| `uvicorn` | `>=0.30,<0.35` |

The `dev` extra contains `httpx`, pytest, pytest-xdist, PyYAML, and a
Python-version-gated `tomli`; the Vercel build log says it installs required
dependencies from `pyproject.toml`, not the development extra. `setuptools`
and `wheel` are build-system requirements. There is no tracked `uv.lock` or
other Python dependency lock file, so the exact Vercel-resolved package
versions are not fixed by this commit.

For a local reference only, the existing workspace Python 3.12 environment
resolves these four dependencies to 15 distributions totaling 16,000,116
unique installed-file bytes (804 files). The larger local distributions are
`pydantic-core` (5,252,700 bytes), `pydantic` (3,790,013), `anyio`
(1,212,748), `jinja2` (1,174,184), and `fastapi` (1,130,177). This is not a
Vercel package measurement: its versions, runtime layer, bytecode, and tracing
may differ.

The Vercel log separately says it force-bundled two packages without
compatible wheels, both named `cffi`. `cffi` is not a direct `pyproject.toml`
dependency and was absent from the local closure above. The available Vercel
log does not name the parent packages, versions, paths, or byte sizes. There is
not enough evidence to remove or replace a dependency safely.

No direct dependency was found that is clearly unused by the FastAPI reader,
Maps, archaeology, lexical, Commentary, or Narrative Explorer routes.

## Package data and file tracing overlap

The setuptools package-data patterns match files already present in the Git
source tree. Their measured tracked bytes are:

| Package-data group | Files matched | Bytes before generated CKL DB |
|---|---:|---:|
| `framework.canonical_library` manifest, object JSON, schema JSON, benchmarks | 691 | 15,198,923 |
| `framework.lexical` schema JSON and `lexicon.sqlite.gz` | 2 | 39,947,799 |
| `bhf_agent` translation, place, context, and Commentary v1.2 JSON | 980 | 16,785,163 |
| `bhf_web` root templates and static assets | 95 | 1,634,254 |
| **Total tracked package-data matches** | **1,768** | **73,566,139** |

The CKL `includeFiles` glob covers all 691 CKL package-data files and the CKL
Python modules. The build hook creates `framework/canonical_library/data/ckl.sqlite`
after dependency installation and the same glob covers that new file. The
build log does not say whether Vercel installs a built wheel of the project,
copies package data to a second path, or resolves those paths to one copy.
Thus 15,198,923 bytes is a measured configuration-level overlap for existing
CKL source data; it is not a measured duplicate in the failed function. The
generated DB could be duplicated only if a packaging path copies it separately;
the current log does not establish that.

The FastAPI app mounts `bhf_web/static` at `/static` and `frontend` at
`/frontend`. It also opens packaged Bible, Commentary, map, archaeology,
lexical, and CKL resources through runtime code. Those resource paths are
listed in `pyproject.toml` package-data rules and are reachable through the
source tree. Whether Vercel counts each path once or also carries an installed
package copy cannot be confirmed without the function file tree.

## Exact duplicate file content

SHA-256 grouping across the retained tracked inputs found 25 duplicate-content
groups, with 151,625 bytes in additional copies. Most are geography and
journey assets mirrored between `frontend/src/data/` and
`bhf_web/static/data/`. `bhf_web/app.py` mounts `frontend/` as a route as well
as mounting `static/`, so removing one copy would change a served path. The
identical `icon-512.png` and `maskable.png` have distinct URLs used for
different browser icon roles. These copies are measurable but are not proven
safe to remove without changing reader behavior.

No byte-identical duplicate CKL JSON object or CKL SQLite file was found in the
retained Git source. The SQLite index contains a normalized projection of the
authoritative JSON, so it is semantic overlap by design rather than an
unnecessary second source copy. Both are required for indexed retrieval,
source identity, and stale-index checks.

## Build caches and generated files

The committed `.vercelignore` prevents local virtual environments, build
outputs, pytest caches, and Python bytecode caches from entering the Git
deployment source. The audit-created SQLite database was written to
`/tmp/ne6r3-ckl.sqlite`, not into the package tree. Python imports during the
audit may create ignored `__pycache__` files locally; `.vercelignore` excludes
them. Vercel may separately generate `.pyc` files during its own bundle build,
which is not captured in the local tracked-file manifest.

No package installation, dependency change, `.vercelignore` change, or
`includeFiles` change was made. Without the Vercel function file tree, neither
duplicate package installations nor byte savings from narrowing the CKL glob
can be claimed.

## References

- [Vercel Python runtime: dependency and file tracing behavior](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Python runtime: bundle exclusions and bytecode behavior](https://vercel.com/docs/functions/runtimes/python#controlling-what-gets-bundled)
