# ED-2A reader projection acceptance

## Acceptance scope

The new projection test follows all nine records through the established Narrative Explorer evidence projection. It checks that each record:

- appears once in its mapped context;
- preserves its exact authored verse or chapter range in the projected record and Scripture relationship;
- exposes the evidence kind, source IDs, provenance, direct primary observation, separate interpretation, confidence, uncertainty, and review state;
- creates only the direct CKL Scripture-anchor connection, with no new authored cross-passage relationship;
- retains draft/in-review governance and the human-review requirement.

Psalm 145 is also checked for the absence of new passage links or NE-10 bridges. Psalm 44 is checked alongside its pre-existing broad lament claim to ensure the new item is a distinct record rather than a duplicate identity.

## Representative visual acceptance

The browser acceptance test uses Psalm 145:13 (manuscript evidence) and Psalm 44:23 (communal-lament interpretation) in the Narrative Explorer. It opens each evidence card and its provenance section at 1440 × 1200 and 390 × 844 viewport sizes, verifies the exact scope and source locators, checks uncertainty and review metadata, and checks for horizontal overflow. The chapter anchors are deliberately different: Psalm 145 tests a verse-specific witness; Psalm 44 tests a poem-wide claim encountered while the reader selects verse 23.

**Acceptance passed:** `.venv/bin/python -m pytest -m gui tests/gui/ne11d1/test_ed2a_psalms_evidence.py -q --tb=short` completed with 4 passed. Both passages were readable at desktop and mobile widths, with no horizontal overflow and exactly one visible card for each selected evidence ID. The test opened the nested “Recorded observations and interpretation” disclosure and verified the evidence fields, qualified interpretations, source IDs, exact locators, uncertainty, and draft/review governance.

The visual check exposed a pre-existing duplicate-display condition: the hidden preview remained visible when its containing section’s grid styling overrode the browser’s default `[hidden]` rule. The existing Narrative Explorer stylesheet now explicitly hides preview and record-list elements carrying `[hidden]`. The browser acceptance test verifies the result; no new UI component or route was introduced. The corrective style change and regression results are recorded in [04-regression-compatibility.md](04-regression-compatibility.md).

## Reader mapping

Existing evidence-type mappings are used: `literary-convention` records project to the established biblical narrative / biblical connections contexts, and `manuscript` projects to ancient history / archaeology. No UI component, API endpoint, or narrative route was added for this wave.
