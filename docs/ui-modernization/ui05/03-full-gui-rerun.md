# BHF UI-05 — Full GUI Rerun

## Final complete acceptance run

**Branch:** `fix/bhf-ui05-repository-gui-gate`

**Tested source SHA:** `77a9901f549057703351ecc0b00afe633a8a45aa`

**Result:** **141 passed, 0 failed, 0 errors, 0 skipped**

**Duration:** 1,909.87 seconds (31m 49s)

The suite ran serially in one pytest process using local headless Chrome. `BHF_GUI_BASE_URL` and `BHF_WEBDRIVER_URL` were unset, a fresh artifact directory was used, and no browser or WebDriver process was active at start or remained after teardown. The run had loopback socket access so the GUI app and ChromeDriver could start. JUnit recorded 141 tests, zero failures, zero errors, and zero skips.

```sh
env -u BHF_GUI_BASE_URL -u BHF_WEBDRIVER_URL \
  BHF_GUI_ARTIFACTS_DIR=/tmp/bhf-ui05-final-gui-77a9901f \
  .venv/bin/python -m pytest -q tests/gui \
  --junitxml=/tmp/bhf-ui05-final-gui-77a9901f.xml
```

All ten requested node IDs are present as passing cases in this full run:

- `test_canonical_browser_opens_editor_for_draft_object`
- `test_mobile_passage_heading_updates_with_translation_badge`
- `test_mobile_ask_submit_still_works`
- `test_clicking_verse_number_selects_entire_verse`
- `test_import_dialog_uses_user_supplied_translation_name`
- `test_native_resource_never_renders_previous_selection_context`
- `test_word_study_choice_updates_and_restores_shared_selection`
- `test_workspace_tabs_switch`
- `test_desktop_primary_navigation_preserves_reader_split`
- `test_context_result_header_keeps_title_readable_in_study_panel`

## Isolated and neighboring reruns

These results are separate from, and do not replace, the full acceptance result above:

- The ten requested GUI cases passed individually: **10/10**.
- Neighbor groups passed: canonical detail/source/editor 2; mobile Ask/selection 3; reader/import 2; Maps 6; workspace panel/navigation 2; Narrative Explorer reader/feature gate/responsive/real-CKL handoff 5.
- After fixing the two additional test-isolation issues exposed by the first complete run, the two cases passed individually and their cache/translation-comparison neighbors passed **8/8**.
- The real-browser Tyndale integration against a provisioned notes database passed: **1/1**.

## Earlier diagnostic full-suite attempts

These attempts are included for traceability and are not counted as the final acceptance run:

| Source SHA | Result | Classification |
|---|---|---|
| `618c66b7a0e708761dc7c73ddef5624d56e54299` | 33 setup errors, 108 skipped in 4.20 seconds | Default sandbox denied loopback sockets (`PermissionError` during app and ChromeDriver port setup); the suite did not run as acceptance. |
| `618c66b7a0e708761dc7c73ddef5624d56e54299` | 139 passed, 2 failed, 0 skipped in 1,897.78 seconds | Full browser run found two test-isolation defects in Companion cache call counting and reader initialization timing. The tests were corrected; the implementation behavior passed isolated reruns. |
| `77a9901f549057703351ecc0b00afe633a8a45aa` | **141 passed, 0 failed, 0 skipped** in 1,909.87 seconds | Final clean, loopback-enabled acceptance run. |

The earlier failures and their test-only corrections are described in [remediation evidence](02-remediation-evidence.md). The release conclusion is in [the decision report](05-release-decision.md).
