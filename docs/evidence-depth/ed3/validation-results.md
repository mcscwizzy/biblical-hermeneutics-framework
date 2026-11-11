# ED-3 Validation Results

This report records technical gates only. Scholarly publication approval is
tracked separately and remains with qualified human reviewers.

## Status

The focused ED-3 and repository release gates below passed unless a limitation
is stated explicitly. The required release-focused Python set passed 50 tests;
the selected NE/API/projection/curation/source-lock batch passed 584 tests. A
repository-wide `pytest -q` run was stopped after 23 minutes, after reporting
two inherited retrieval-order failures, 54 passing tests, and 892 passing
subtests. It did not reach a full-suite summary. Both failing test methods were
reproduced against an archive of the exact ED-2 `origin/master` base. The
reproducible inventory and fingerprint are in [baseline.md](baseline.md).

## Final gates

| Gate | Result | Evidence |
|---|---|---|
| CKL strict schema and references | Pass | `python tools/ckl_validate.py --root framework/canonical_library --json`: 687 valid objects, 0 errors, 14 inherited warnings. No manifest, evidence-ID, source, or anchor errors. |
| CKL deep source and retrieval checks | Pass with inherited findings | `python tools/ckl_report.py --root framework/canonical_library --deep --json --output /tmp/ed3-final-deep.json`: 1,408 evidence items; 63 heuristic error-severity findings, 1,093 warnings, and 102 source-support-target signals. Deep source scan: 0 unresolved child-source references after the two exact Phase 3 repairs. |
| Python/API, projection, curation, and held-route tests | Focused gates pass; broad suite has two confirmed inherited failures | 584 passed across `test_ne9c_bulk_curation.py`, Narrative Explorer curation/API/projection, canonical-library release, and source-lock tests; Validate workflow release group: 50 passed. The unfiltered run was interrupted after 23 minutes with 54 tests and 892 subtests passed, 2 assertions failed. Both assertions reproduced on ED-2 `origin/master`. |
| Frontend tests | Pass | `npm test`: 17 passed, 0 failed. |
| Protected NE-9C/NE-10 artifacts and identities | Pass by compatibility review; frozen validator limitation retained | Current authored registry counts: 433 accepted identities (431 object, 2 evidence), 44 NE-10 bridges, 7 held candidates. NE-9C checkpoint and NE-10 file hashes match baseline; no protected file diff. Legacy bulk validator stops at its inherited CKL fingerprint mismatch; see below. |
| Chapter census | Pass | ED-1A census: 1,189/1,189 chapters, 687 objects, 0 unmapped identities, 19 deterministic sample checks, 16 targeted service builds. Coverage split: 1,089 passage-specific, 56 contextual-only, 2 entity-only, 41 no eligible CKL material, 1 incomplete/unknown. |
| Profile generation cleanliness | Pass | Both supported profiles regenerated; `git diff --exit-code -- profiles/` passed. |
| Package contents and installed-wheel smoke | Pass with existing packaging warnings | `python -m build --no-isolation` built wheel and sdist; content gate found 1,052 wheel entries and 1,242 sdist entries, all required files present, no retired generated-commentary payload. Installed wheel smoke loaded its own packaged app and 687 CKL objects; CLI and Commentary module help passed. |
| Genuine 390 CSS-pixel reader checks | Completed in phase 6 | [Reader acceptance](reader-acceptance.md) |
| Diff, generated-file, and worktree review | Pass at validation checkpoint | `git diff --check` passed; no generated profile changes or package artifacts entered Git. Only two CKL objects differ from the ED-2 base, for documented source/claim corrections. |

## Command record and limits

- `.venv/bin/python tools/validate.py framework/` — 94 modules valid.
- `.venv/bin/python -m pytest -q tests/test_ne9c_bulk_curation.py tests/test_narrative_explorer_curation.py tests/test_narrative_explorer_api.py tests/test_narrative_explorer_projection.py tests/canonical_library/test_release.py tests/canonical_library/test_source_locks.py` — 584 passed.
- `.venv/bin/python -m pytest -q` was stopped after 23:10 because it had not reached a useful completion point. It reported 54 passed, 892 subtests passed, and 2 failed before interruption. Exact failures: `FirstJohnRecordTests.test_retrieval_answers_book_specific_questions` (`What if our heart condemns us?`: expected `1-john`, received `john`) and `FirstThessaloniansRecordTests.test_retrieval_answers_book_specific_questions` (`How does 1 Thessalonians relate to Acts 17?`: expected `1-thessalonians`, received `acts`). The same two tests failed against an isolated `git archive origin/master` checkout (2 failed, 2 passed, 70 subtests passed in the two targeted methods), so they are inherited retrieval-ranking behavior and no ED-3 fix was applied.
- `.venv/bin/python -m pytest -q` with the workflow's exact NE7R3 release list — 50 passed in 97.42 seconds.
- `npm test` — 17 passed, 0 failed.
- `python -m build --no-isolation` emitted existing setuptools license deprecation notices and the optional commentary SQLite glob warning. No dependency or package configuration was changed.
- The installed-wheel smoke used an isolated temporary `--target` install and the already installed `.venv` dependency site-packages; it did not fetch new dependencies. The app import resolved from `/tmp/ed3-wheel-site` and `CanonicalLibrary.load_default()` read 687 packaged objects.
- The full ED-1A audit wrote only under `/tmp/ed3-final-census`; its read-only input was `.bhf-data/study.sqlite`. The committed NE-9C checkpoint was not regenerated.

The legacy command `python3 scripts/ne9c_bulk_curation.py validate` returns
`NE-9C bulk curation stopped: protected CKL source fingerprint changed`.
The same frozen-checkpoint mismatch was reproduced at ED-3 baseline on the
unmodified ED-2 merge because the checkpoint predates ED-2's CKL additions.
ED-3 preserved the checkpoint and verified current authored accepted
identities, the held/excluded state via the existing tests, the protected file
hashes, and the NE-10 counts without weakening validation or refreshing the
historical fingerprint.

## Interpretation

Inherited heuristic signals, the interrupted broad pytest run, the confirmed
base-revision retrieval failures, and historical checkpoint compatibility
limits are reported separately from completed gates and ED-3 corrections. No
checkpoint was regenerated to bypass a fingerprint mismatch.
