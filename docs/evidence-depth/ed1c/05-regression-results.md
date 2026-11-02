# ED-1C regression and integrity results

All results are recorded from the ED-1C work branch. No CKL object, source
record, source lock, manifest, NE-9C curation input, or NE-10 bridge registry
was changed.

## Required gates

| Gate | Command | Result |
| --- | --- | --- |
| Frontend suite | `npm test` | PASS: 17 test files, 17 passed, 0 failed. |
| Narrative Explorer, API, source-lock, manifest, release regressions | `.venv/bin/pytest -q tests/test_ne9c_bulk_curation.py tests/test_narrative_explorer_*.py tests/canonical_library/test_source_locks.py tests/canonical_library/test_manifest.py tests/canonical_library/test_release.py` | PASS: 648 passed, 13 subtests passed in 397.36s. |
| CKL schema, Scripture-anchor, and typed evidence checks | `.venv/bin/pytest -q tests/canonical_library/test_schema.py tests/canonical_library/test_scripture_reference_integrity.py tests/canonical_library/test_typed_evidence_targets.py` | PASS: 108 passed in 31.00s. |
| CKL validation | `python3 tools/ckl_validate.py --root framework/canonical_library` | PASS: 687 valid objects, 0 errors, 14 warnings. |
| Desktop and mobile reader acceptance | `.venv/bin/pytest tests/gui/ne11d1/test_ed1c_additional_records.py -q -s` | PASS: 2 parameterized cases after final copy and lexical-label changes. |
| ED-1C Markdown links | Local relative-link check across `docs/evidence-depth/ed1c/*.md` | PASS: 6 Markdown files. |
| Diff whitespace check | `git diff --check` | PASS in the final pre-commit review. |

The full ED-1A inventory reproduction ran before implementation and passed:
687 CKL objects scanned, 1,189 chapter rows, no unmapped record identities,
and the audit’s validation status was `pass`. It counted 12,665 eligible
placements, 11,642 assigned placements, and 1,023 unassigned placements in 394
chapters. ED-1C changes no CKL data, section assignments, or API projection, so
those counts remain unchanged; the reader-only disclosure and lexical label do
not affect the inventory.

## Focused acceptance checks

- `node tests/frontend/narrative-explorer.test.js` — 54 tests passed after the
  structured lexical label change. Coverage includes collapsed activation,
  provenance retention, exact example anchors, and exclusions for assigned,
  broad, source-less, inapplicable, or already previewed records.
- `.venv/bin/pytest tests/test_narrative_explorer_api.py::test_ed1c_additional_record_inputs_keep_exact_scope_and_held_ezekiel_bridge_out -q`
  — 1 passed. The test checks Proverbs 31 applicability, Mark 2 verse
  exclusion, and the held Ezekiel/Revelation route.
- `.venv/bin/pytest tests/gui/ne11d1/test_ed1c_additional_records.py -q -s`
  — 2 passed at desktop and mobile sizes. Browser evidence is documented in
  [reader acceptance](04-reader-acceptance.md).

## Scope limits

The work is a reader-only change. CKL/source integrity, API, section
classification, provenance, and held-route results are protected by the gates
above; no CKL data was regenerated or rewritten. Final `git diff --check`,
documentation links, generated-file status, and final commit/push state are
reviewed before completion.

An initial command that included every module under `tests/canonical_library`
was intentionally interrupted at 1% because it was broader than the affected
surface. The focused integrity set above and the CKL validator were completed;
the interrupted broad run emitted no test failure before it was stopped.
