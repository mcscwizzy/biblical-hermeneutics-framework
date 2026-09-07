# Commentary v1.1 post-release audit

Audit scope: forward-only validation and packaging correction after the
Commentary v1.1 release. No certified Commentary prose, evidence, CKL record,
fingerprint, or release tag was changed.

## Release

- Starting and production `master` HEAD: `0036ec7d05558869e6bc6515168ff2ea650397e8`
- Release merge: `0036ec7` (`58f93df` + `cab9854f`)
- Release tag: annotated `commentary-v1.1`, points to `0036ec7`
- Production Vercel: READY; live `/api/health` returned HTTP 200 with
  `{"status":"ok","service":"bhf-web"}`.
- The corrective work is on `fix/commentary-v1.1-postrelease`; the release tag
  remains immutable and was not retargeted.

## Commentary

- Pipeline state: `CORPUS_COMPLETE`
- Eligible finalized: `935 / 935`
- Runtime chapters: `935`
- Runtime fingerprint:
  `9df456a3a22003587347cc0a78a9de5ca292e1d9554c4af3fc591207dd87e5db`
- Protected fingerprints: `948`, clean after validation
- CKL: unchanged
- No prose regeneration, Terra invocation, or candidate-state advancement was
  performed.

The live BHF Commentary diagnostics route returned `935` files and status
`ok`. John 1, Psalms 119, 2 Samuel 6, Joshua 1, and Revelation 22 returned
available v1.1 projections. Genesis 1 returned the existing
`bhf_commentary_not_available` response in both production and the staged
tree; Genesis 1 is not among the derived 935 eligible runtime chapters. It was
not synthesized or added because doing so would violate the certified-corpus
guardrails.

## Lexicon

Before the fix, production `/api/lexicon/diagnostics` returned HTTP 200 but
reported:

```json
{"path":"/tmp/bhf-data/lexicon.sqlite","lexical_database_found":false}
```

The runtime expects `framework/lexical/database/lexicon.sqlite`, falling back to
the Vercel writable `/tmp/bhf-data/lexicon.sqlite`. The authoritative generated
database was local-only, ignored by `.bhf/` and `*.sqlite`, and therefore was
not present in the Vercel source package. `.vercelignore` did not accidentally
exclude the runtime path; the runtime asset simply did not exist in Git.

The exact existing generated database was packaged as the deterministic
`framework/lexical/database/lexicon.sqlite.gz` asset (39 MB compressed; no
lexical content was regenerated). Runtime code expands it atomically into the
writable runtime directory on first use. Package data metadata and regression
coverage were updated accordingly.

The production result before this branch is therefore **broken/unavailable**;
the staged post-fix result is **working**: `14,197` lexical entries,
`444,339` verse-token rows, and passing John 1:1 Greek `G3056` and Psalm 23:6
Hebrew `H2617` checks. Production must be rechecked after this branch is
merged; no production deployment was changed by this audit.

## Path sanitation

- Before: `9` absolute local-path occurrences across `7` tracked files.
- After: `0` occurrences matching local `/home/<user>/`, `/Users/<user>/`, or
  Windows user paths in the committed release/audit scope.
- Sanitized files included the resume document, the pre-merge audit, and six
  generated candidate/audit metadata files.
- Replacements use `<repo-root>` or `<local-worktree>` and preserve the
  referenced repository-relative meaning.
- No protected Commentary chapter, evidence bundle, CKL record, or runtime
  corpus file was modified.
- `tests/test_release_path_sanitization.py` prevents future local absolute paths
  in committed release/audit artifacts.

## Security

- Committed credentials found: **no**.
- Focused tracked-file scan found no API keys, provider tokens, passwords,
  authorization bearer values, OAuth secrets, or private keys.
- `gitleaks` and `trufflehog` were not installed in the environment, so no
  third-party scanner result is claimed.

## Runtime and packaging

The production-like staged tree excluded candidates, tests, docs, caches,
virtual environments, GUI requirements, Docker-only files, and local `.bhf`
state. It included the certified runtime corpus, Bible data, CKL JSON runtime
data, FastAPI source, templates, static assets, `tools/**`, and the compressed
lexicon asset. The staged tree was approximately 118 MB, below the 225 MB
function ceiling used by the prior audit.

Post-fix staged ASGI checks:

- startup and root page: pass; release metadata contains `commentary-v1.1`
- `/api/health`: HTTP 200
- Bible Genesis 1 and John 1: HTTP 200
- translations: HTTP 200
- CKL search: HTTP 200 with results
- lexicon diagnostics and Hebrew/Greek samples: pass
- BHF Commentary diagnostics: `935`, `ok`
- required static CSS: HTTP 200
- requested Commentary chapters: 5 available; Genesis 1 remains the documented
  derived-corpus omission above
- no candidate workspace dependency in the staged tree or rendered root

## Tests

Focused results from this corrective branch:

- packaging, Vercel startup, and path guard: `11 passed`
- Commentary/Bible/release/runtime group: `97 passed`
- Commentary orchestrator and scaled-preflight regression group:
  `78 passed`
- CKL/retrieval/lexicon/storage/dependency group: `51 passed`, `4 subtests`
  passed, plus one pre-existing dependency-guard failure
- Scripture reference integrity: `15 passed`
- focused FastAPI web routes/assets: `8 passed`

The pre-existing dependency-guard failure is
`tests/test_project_dependencies.py::test_production_modules_have_no_undeclared_direct_third_party_imports`:
the baseline import scan reports `anthropic`, `starlette`, and `tools` as
outside the declared direct dependency set. It is unrelated to this fix and
was not weakened or changed.

Known stale historical fixtures remain the three recorded in the release
report: the Numbers 16 canary lock and two Batch 003 lock-accounting
expectations. They do not affect the certified runtime corpus.

## Git hygiene

The authenticated GitHub protection API was unavailable in this environment
(`gh` is not authenticated; unauthenticated API returned HTTP 401). No
administrative settings were changed. The repository's previous recorded state
was that `master` protection was disabled. Recommended baseline: require a PR,
require core CI checks, block force pushes and deletion, and require the branch
to be up to date where practical.

Current ancestry audit:

| Branch | HEAD | Ahead | Behind | Fully merged | Safe to delete |
| --- | --- | ---: | ---: | --- | --- |
| `feat/commentary-v1.1-expansion` | `cab9854f` | 0 | 1 | yes | yes |
| `feat/commentary` | `884b6968` | 0 | 100 | yes | yes, if no archival need |
| `fix/async-ai-presentation` | `61697828` | 0 | 187 | yes | yes, if no archival need |
| `fix/vercel-commentary-corpus` | `9c4791c4` | 0 | 87 | yes | yes, if no archival need |
| `fix/commentary-v1.1-postrelease` | current hotfix HEAD | 0 | 0 | n/a | no |

The obsolete `feat/commentary-v1.1-expansion` branch is fully merged with zero
unique commits and is the only branch removed by this pass. The three older
merged branches remain as historical refs because active-work/archival intent
could not be authenticated from this environment; they are cleanup
recommendations, not silently deleted refs. `master` was not deleted or
rewritten.

## Remaining issues

- Release blocker: none for the certified corpus or current production health.
- Post-fix deployment action: merge this focused branch through the normal PR
  workflow, then verify the resulting Vercel deployment's lexicon diagnostics
  and representative lookups.
- Maintenance: resolve or explicitly re-scope the pre-existing dependency guard
  failure and refresh the three stale historical fixtures in a separate change.
- Maintenance: decide whether Genesis 1 should become eligible in a future,
  separately governed Commentary release; it was intentionally not changed
  here.
- Optional: authenticate a GitHub administrator and apply the recommended
  `master` protection baseline.
