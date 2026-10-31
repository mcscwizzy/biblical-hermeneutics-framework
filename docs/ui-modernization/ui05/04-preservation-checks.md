# BHF UI-05 — Preservation Checks

## Canonical Knowledge Library

- `git diff --exit-code -- framework/canonical_library` passed: no CKL source, schema, review, provenance, evidence, curation, source lock, fingerprint, or manifest file was changed.
- CKL source validation scanned 687 files and validated 687 objects: 0 errors and 14 existing warnings. No warning was edited as part of UI-05.
- The provisioned local CKL SQLite database passed `verify-db`: schema version 4, retrieval index version 3, 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, and inventory fingerprint `90fa7547ea4146328ab1fc4e9f4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.

## Tyndale Open Study Notes

- No Tyndale source, license, importer, repository, retrieval service, schema, or build hook is part of the UI-05 diff.
- The provisioned `.bhf/commentary.sqlite` SHA-256 before and after browser integration was `2652edde56b22cf22628ced0da7dd81d7668c305ce17581a5a817aa97765e17f`.
- `framework.commentary check-tyndale` reported a healthy database, SQLite integrity `ok`, 17,478 entries and anchors, zero orphaned anchors, and one source. The source SHA-256 was `7b4d5ae088449d5a6925170c4b89b978acee2f78f73dc6b8a278fa948a7e8498`; the runtime disclosure identified Tyndale House Publishers and CC BY-SA 4.0.
- The real-browser integration against the provisioned notes database passed. It checked the Tyndale note display and translation comparison while preserving reader context. The integration uses a temporary test copy; the provisioned database hash remained unchanged.
- The relevant Python/API and Tyndale test batch completed with **232 passed, 55 skipped, 4 subtests passed**.

## Reader, handoff, and Narrative Explorer

- Ask BHF remains a selected-passage external-assistant handoff. The mobile browser test verifies the selected verse, prepared question text, copy path, and assistant destination with external browser APIs stubbed.
- Verse selection is asserted through `BHFStudySelection` including the exact selected verse and text. No selection model or translation comparison implementation was changed.
- Narrative Explorer feature-gate, history, responsive-action, and real-CKL handoff journeys passed in targeted browser runs. No Narrative Explorer implementation, feature flag, relationship data, history, or disclosure file appears in the diff.
- No deployment configuration was changed.
- Frontend tests passed **16/16**, framework validation accepted **94 modules**, CKL source validation reported **0 errors**, packaging tests passed, and retired Commentary route/runtime tests passed in the Python/API batch.

The reports [failure classification](01-failure-classification.md) and [remediation evidence](02-remediation-evidence.md) describe how the existing contracts were tested. Full-suite and source SHA evidence is recorded in [the acceptance run](03-full-gui-rerun.md) and [release decision](05-release-decision.md).
