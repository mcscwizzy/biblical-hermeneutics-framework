# ED-6 Validation Results

## Current preparation checks

| Check | Outcome |
|---|---|
| Pilot, ED-5 evaluator, Narrative Explorer API, CKL retrieval, source-lock, manifest, and Scripture-reference regressions | 123 passed and 13 subtests passed in 294.29 seconds. Command: `.venv/bin/python -m pytest -q tests/test_ed6_reader_pilot.py tests/test_ed5_reader_evaluation.py tests/test_narrative_explorer_api.py tests/canonical_library/test_ckl_retrieval_service.py tests/canonical_library/test_source_locks.py tests/canonical_library/test_manifest.py tests/canonical_library/test_scripture_reference_integrity.py`. |
| Frontend suite | `npm test`: 17 test files passed, 0 failures. |
| Chromium connectivity smoke gate | 3 passed in 20.92 seconds; remote Chrome reached the test server and offline route. |
| ED-6 Psalm 82 and Deuteronomy 32 tasks | 2 passed in current remote Chromium. Exact records, source disclosures, uncertainty status, and draft/review labels were checked. |
| ED-6 natural-language 1 John task | 1 passed in current remote Chromium using the passage-grounded query in the task bank; reader-facing source titles were visible. |
| ED-5 mobile acceptance, Jonah route, Psalm 145 evidence | 8 passed; 2 Psalm 44 variants were deselected. Includes 390px and 320px states, empty coverage, keyboard disclosure, Genesis 12 at desktop/mobile, verified Jonah → Matthew direction and return, and Psalm 145 at desktop/mobile. |
| Genesis 6 review disclosure | 2 passed; 5 unrelated parameter cases were deselected. Exact draft and review labels, source records, uncertainty, and evidence detail were checked. |
| 1 Corinthians 11:3 lexical task at 390px | 1 passed; desktop variant deselected. Exact anchor, BDAG/Thiselton sources, disputed certainty, and lexical uncertainty were checked. |
| Strict CKL validation | `python tools/ckl_validate.py --root framework/canonical_library`: 687/687 objects valid, 0 errors, 14 inherited warnings. |
| Current NE-9C/NE-10 compatibility | Passed read-only validation: 3,925 reviewed relationship identities, 433 runtime curations, 44 verified bridges, 7 held candidates. The known historical CKL fingerprint mismatch remains documented; protected hashes are unchanged. |
| ED-5 scripted reader evaluator | 12/12 deterministic journeys passed, all 10 projected records matched exact IDs. It is not a human-comprehension measure. |
| Authentic ED-6 records | None present in `.bhf-data/ed6-reader-pilot/` at baseline; no human findings are reported. |

The browser commands used the existing remote Chromium infrastructure and
current in-process application fixture. The relevant files and filters were:

```bash
.venv/bin/python -m pytest -q tests/gui/ne11d1/test_connectivity_smoke.py
.venv/bin/python -m pytest -q tests/gui/ne11d1/test_ed6_reader_pilot_readiness.py
.venv/bin/python -m pytest -q tests/gui/ne11d1/test_ed5_mobile_acceptance.py \
  tests/gui/ne11d1/test_real_ckl_handoff.py::test_real_ckl_jonah_and_matthew_handoffs_preserve_direction_and_return \
  tests/gui/ne11d1/test_ed2a_psalms_evidence.py -k 'not psalm44'
.venv/bin/python -m pytest -q tests/gui/ne11h/test_genesis_draft_record_acceptance.py -k '6-genesis'
.venv/bin/python -m pytest -q tests/gui/ne11d1/test_ed1c_additional_records.py -k mobile
```

The ED-6 readiness module also ran the 1 John browser case separately after
the broad query was found not to return that record in the generic browser
search. The live task was grounded to 1 John 3:19–24 and retested successfully.
All new checks are deterministic UI/projection checks, not participant data.
The census and protected hashes are in [baseline](baseline.md).

Documentation links in the ED-6 package and the `docs/README.md` index were
checked; all relative links resolved and both ED-6 JSON files parsed. The
final working diff passed `git diff --check`, and the working tree contained no
participant data, generated CKL changes, or unrelated files.

## Interpretation limits

Automated tests establish that code and page states behave as exercised by the
tests. They do not establish that participants understand evidence, that
scholarly records are approved, or that every task is usable on every device.
No participant result or reviewer decision belongs in this file unless it was
actually observed and independently documented.
