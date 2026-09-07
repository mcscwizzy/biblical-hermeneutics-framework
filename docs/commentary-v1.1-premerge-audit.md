# Commentary v1.1 final pre-merge audit

Audit date: 2026-09-06. This audit is read-only with respect to `master` and
does not merge, tag, delete branches, regenerate commentary, or modify CKL,
evidence, certified prose, or protected fingerprints.

## Repository

| Item | Result |
| --- | --- |
| Feature branch | `feat/commentary-v1.1-expansion` |
| Feature HEAD | `dd62adf70a0461a74d0769bf46f77b8db191c068` |
| Master HEAD | `58f93df1c1cc716c4e72c6787b774e0beb08a929` |
| Merge base | `58f93df1c1cc716c4e72c6787b774e0beb08a929` |
| Ahead / behind | 75 ahead / 0 behind |
| Predicted merge conflicts | 0 |
| Working tree at audit start | clean |
| Remote feature synchronization | current and pushed |

`git merge-tree` reported no predicted conflict markers. The feature/master
diff contains 3,525 paths, 6,758,559 insertions, and 165 deletions. Its
categorized path counts are: 2,472 candidate/audit artifacts, 936 runtime
commentary files, 40 documentation files, 24 tests, 18 CKL files, 16 tools,
11 runtime-application files, 5 orchestration/remediation files, 2 packaging
files, and 1 repository-instruction file (`AGENTS.md`). The CKL changes are
the earlier, intentional semantic-scope work in commits `ea8480c`, `a4cbc71`,
and `cc9f0f0`; CKL is unchanged from the release-hardening baseline
`5c75868`, as is the published runtime corpus.

## Corpus

| Check | Result |
| --- | --- |
| Orchestrator status/report/validate/next | `CORPUS_COMPLETE`, clean; `next` remained terminal |
| Eligible corpus | 935 |
| Eligible finalized | 935 |
| Protected finalized | 948 |
| Runtime chapter files | 935 |
| Missing / unexpected | 0 / 0 |
| Duplicate canonical identities | 0 |
| Stale runtime chapters | 0 |
| Uncertified runtime prose | 0 |
| Batch 009 | absent; no initialization attempted |

The authoritative publisher validation recomputed 935 certified rows and the
runtime fingerprint:

`9df456a3a22003587347cc0a78a9de5ca292e1d9554c4af3fc591207dd87e5db`

The runtime directory is 3,264,473 bytes including its manifest. The manifest
SHA-256 is
`eeeb52dd767f0c8bfd0d49f4875069f7128b0f0efcc06236a1ec1c6134b88b60`.

## Integrity

- Protected fingerprint verification: 948 expected, 948 actual, 0 mismatches.
- Runtime JSON/schema/evidence-hash validation: clean.
- Commentary prose regeneration during release hardening: 0.
- Runtime and CKL trees are unchanged since `5c75868`.
- CKL direct fallback loaded 665 objects with inventory fingerprint
  `4110222ae77df2e35c91cdd59af4312ba4e3710accf349bf030aefe9d3b1e9bc`.
- CKL retrieval/scope/integrity tests passed; no CKL content changed during
  packaging hardening.
- No stale lock artifact or hidden Batch 009 was found.

## Runtime dependency proof

The production entry point is `bhf_web/app.py`. `runtime_paths.py` resolves
the default release to `.bhf-data/bhf-commentary-v1.1`; Vercel rejects an
explicit candidate-workspace override. The staged tree retained the certified
commentary corpus, CKL JSON/source, Bible JSON, templates/static assets, and
the `tools` modules lazily imported by the internal coverage route. The
candidate workspace was physically absent from the staged tree, and 18 direct
commentary/evidence lookups succeeded across Torah, narrative, poetry,
wisdom, prophecy, Gospel, Acts, Pauline/general epistles, and apocalyptic
controls, including all 12 explicitly remediated chapters.

## Vercel

The prior deployment evidence reported approximately 388.83 MB raw and
397.27 MB optimized against a 225 MB limit. The root `.vercelignore` excludes
the proven candidate/audit workspace and development-only files; it does not
exclude broad `.bhf-data/**`, runtime commentary, CKL, Bible data, lexicons,
application source, templates, or static assets. `vercel.json` retains the
function-level candidate exclusion for `bhf_web/app.py`.

Repository-side staging measured:

| Component | Bytes |
| --- | ---: |
| Staged source/runtime tree | 37,417,268 |
| Estimated production dependency closure | 10,747,416 |
| Projected combined footprint | 48,164,684 |

External release evidence for deployment commit `dd62adf` reports preview
state `READY`; the root returned HTTP 200 and exposed
`commentaryRelease: commentary-v1.1`. Exact post-hardening raw/optimized
function sizes were not exposed in the available evidence. No Vercel CLI is
installed or linked locally, so this result was not independently queried from
the platform in this environment.

## Runtime smoke tests

The staged app imported with 111 routes and returned HTTP 200 for `/`,
`/api/health`, `/api/bible/Genesis/1`, `/api/bible/books`, and
`/api/translations`. The 18 required commentary references returned available
Commentary v1.1 content, and all 18 corresponding evidence bundles loaded
directly with no candidate workspace present. Direct CKL loading succeeded.

The staged `/api/canonical/entities-for-passage` probe exceeded the bounded
120-second check; this is recorded rather than called a pass. The staged
lexicon diagnostics endpoint correctly reported the database absent, but a
representative standalone lexicon lookup could not succeed because
`framework/lexical/database/lexicon.sqlite` is intentionally generated and is
not tracked or seeded by the Vercel source. The code and documentation require
safe-unavailable behavior in that condition. The explicit final gate in this
audit nevertheless requires a successful representative lexicon lookup, so
this is a release blocker unless production lexicon provisioning is provided
and verified without changing the certified release.

## Tests

| Suite | Result |
| --- | --- |
| Vercel packaging/startup | 9 passed |
| Release/commentary/coverage | 46 passed |
| Orchestration/remediation/recovery | 51 passed |
| CKL/Bible/lexicon | 81 passed, 1 skipped, 10 subtests passed |
| Web/presentation bounded group | stopped at 180 seconds after partial progress; no failures emitted |
| Historical Terra fixture review | 5 passed, 3 known stale failures |

The three stale failures are unchanged historical expectations: the canary
fixture requires the old Numbers 16 lock, and two Batch 003 tests expect
pre-remediation lock accounting. They do not alter certified prose or release
policy and were not changed. No release-critical failure occurred in the
focused packaging, release, orchestration, CKL, Bible, or lexicon test groups.

## Security

No credential/token/private-key pattern was found. However, seven tracked
files contain serialized absolute local paths beginning with
`/home/johnwalker`, including `.BHF-GENERATION-RESUME.md` and candidate/audit
artifacts such as `future-ckl-remediation-queue.json` and
`post-remediation-recovery-adjudication.json`. These are local-machine data
leaks in committed release artifacts. Redacting or removing them would touch
audit/evidence artifacts and is outside the allowed minimal pre-merge changes;
the issue therefore blocks merge and requires a separately reviewed metadata
sanitization change.

## Branch cleanup plan

| Branch | HEAD | Fully merged now? | Safe after merge? | Recommendation |
| --- | --- | --- | --- | --- |
| `master` | `58f93df` | yes | no | preserve |
| `feat/commentary-v1.1-expansion` | `dd62adf` | no | no | merge only in a later task after blockers clear |
| `feat/commentary` | `884b696` | yes | yes | optional cleanup after release; do not delete in this task |
| `fix/async-ai-presentation` | `6169782` | yes | yes | optional cleanup after release; do not delete in this task |
| `fix/vercel-commentary-corpus` | `9c4791c` | yes | yes | optional cleanup after release; do not delete in this task |

## Merge plan

The recommended method is a normal `--no-ff` merge commit, preserving the
corpus milestones, audit/remediation history, and packaging hardening. The
recommended tag is `commentary-v1.1`, created on the actual master merge
commit after the merge is approved.

Exact commands for the next task, after all blockers are resolved:

```bash
git switch master
git pull --ff-only origin master
git merge --no-ff origin/feat/commentary-v1.1-expansion -m "Merge Commentary v1.1 release"
git push origin master
git tag -a commentary-v1.1 -m "Commentary v1.1 release"
git push origin commentary-v1.1
```

## Final gate

Corpus, certified runtime integrity, protected fingerprints, CKL integrity,
candidate independence, packaging, and focused release tests pass. The gate
is **BLOCKED** by (1) the explicit requirement for a successful representative
lexicon lookup while the Vercel staged runtime has no lexicon database, and
(2) seven committed files containing absolute local filesystem paths. The
current platform preview evidence is `READY`, but it does not override either
repository/runtime or security failure.

`COMMENTARY_V1.1_PREMERGE_BLOCKED`
