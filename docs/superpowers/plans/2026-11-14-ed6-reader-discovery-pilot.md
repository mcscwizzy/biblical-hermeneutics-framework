# ED-6 Reader Discovery Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a pilot-ready, privacy-preserving reader study toolkit and scholarly-review kickoff without representing synthetic data or automated checks as human findings.

**Architecture:** Add a standard-library JSONL validator/importer/aggregate analyzer, synthetic-only fixtures, focused Chromium readiness checks, and the requested facilitator/reviewer documentation. Keep authentic records in ignored `.bhf-data/ed6-reader-pilot/`; do not change scholarly data or production deployment settings.

**Tech Stack:** Python 3.12 standard library, pytest, existing Selenium/Chromium GUI infrastructure, Markdown, JSON, JSONL.

**Spec:** `docs/superpowers/specs/2026-11-14-ed6-reader-discovery-pilot-design.md`

## Global Constraints

- “Do not simulate human participation or scholarly approval.”
- “No participant accounts, analytics tracking, screen recording, voice recording, or external uploads should be required.”
- “Do not modify scholarly content to improve pilot results.”
- “Do not merge or deploy.”
- Preserve NE-9C/NE-10 decisions, source locks, provenance, and the active Validate workflow.
- Store genuine data only under the ignored local path `.bhf-data/ed6-reader-pilot/`.

## Review Focus

- Invalid JSONL lines and duplicate participant codes must be reported and block import without losing existing records.
- Incomplete/stopped sessions must remain analyzable with explicit denominators and no imputed completion.
- Synthetic fixture records must be rejected by ordinary import/report commands.
- Direct identifiers in fields or free text must be rejected or flagged without echoing participant text.
- A 390 CSS-pixel viewport and keyboard-operated disclosures must be asserted with live Chromium evidence.

---

### Task 1: Local session schema and toolkit

**Files:**
- Create: `tools/ed6_reader_pilot.py`
- Create: `docs/evidence-depth/ed6/session-record.schema.json`
- Create: `tests/test_ed6_reader_pilot.py`
- Create: `tests/fixtures/ed6_reader_pilot/synthetic_sessions.jsonl`

**Interfaces:**
- `read_jsonl(path: Path, allow_synthetic: bool = False) -> dict[str, Any]`
- `validate_session(record: dict[str, Any], allow_synthetic: bool = False) -> list[dict[str, str]]`
- `analyze_records(records: list[dict[str, Any]], input_summary: dict[str, Any]) -> dict[str, Any]`
- CLI commands: `validate`, `import`, and `report`; normal commands accept participant records only.

- [ ] Write failing tests for a valid complete record, an incomplete record, malformed JSONL, duplicate codes, forbidden identifier fields/free-text patterns, quote consent, synthetic rejection, and denominator-aware aggregate output.
- [ ] Run `pytest -q tests/test_ed6_reader_pilot.py` and confirm the expected missing-tool failures.
- [ ] Implement schema loading, line-by-line validation, safe local import, and aggregate JSON reporting with no third-party runtime dependency.
- [ ] Run `pytest -q tests/test_ed6_reader_pilot.py` and confirm all cases pass.
- [ ] Confirm an invalid import writes nothing and an incomplete session appears in the report with observed-only denominators.

### Task 2: Study and privacy documentation

**Files:**
- Create: `docs/evidence-depth/ed6/README.md`
- Create: `docs/evidence-depth/ed6/baseline.md`
- Create: `docs/evidence-depth/ed6/participant-protocol.md`
- Create: `docs/evidence-depth/ed6/consent-and-privacy.md`
- Create: `docs/evidence-depth/ed6/facilitator-guide.md`
- Create: `docs/evidence-depth/ed6/study-task-bank.md`
- Create: `docs/evidence-depth/ed6/participant-notes-template.md`
- Create: `docs/evidence-depth/ed6/post-session-questions.md`
- Create: `docs/evidence-depth/ed6/measurement-rubric.md`
- Create: `docs/evidence-depth/ed6/data-management.md`

- [ ] Document the 20–30 minute session, voluntary consent, neutral facilitation, non-identifying recruitment mix, and local-only privacy rules.
- [ ] Map four balanced tasks per participant to exact ED-5 IDs, with passage diversity, a verified Jonah → Matthew relationship, and the eligible negative case.
- [ ] Define observed-behavior scoring, task-level denominators, optional quotations, and direct-observation versus facilitator-interpretation fields.
- [ ] Validate Markdown links and documented commands after the tool interface is final.

### Task 3: Scholarly review kickoff and reporting handoff

**Files:**
- Create: `docs/evidence-depth/ed6/scholarly-review-kickoff.md`
- Create: `docs/evidence-depth/ed6/feedback-analysis-method.md`
- Create: `docs/evidence-depth/ed6/reader-pilot-readiness.md`
- Create: `docs/evidence-depth/ed6/validation-results.md`
- Create: `docs/evidence-depth/ed6/final-report.md`
- Create: `docs/evidence-depth/ed6/progress.json`

- [ ] Explain CKL evidence, observation versus reconstruction, uncertainty, independent source inspection, review workbench, export/verification/backup, and access-limit outcomes.
- [ ] Prioritize the first 3–5 ED-5 pilot-index packets by its existing priority ordering; retain links to all 12 and leave outcomes empty.
- [ ] Define transparent improvement prioritization and distinguish integrity, accessibility, navigation, terminology, density, preference, and out-of-mission feedback.
- [ ] Mark participant results and scholarly decisions unpopulated, and set explicit readiness labels.

### Task 4: Reader pilot browser readiness

**Files:**
- Create: `tests/gui/ne11d1/test_ed6_reader_pilot_readiness.py`

- [ ] Add bounded Chromium journeys for exact passage/evidence, source and draft disclosures, uncertainty text, verified Jonah direction and return, 1 Kings 2 completed-empty, 390px mobile operation, and keyboard disclosure access.
- [ ] Run the existing connectivity smoke gate, then the new ED-6 GUI tests and the existing ED-5 acceptance file.
- [ ] Fix only a reproduced task-blocking issue; otherwise leave production code unchanged and document the acceptance evidence and limits.

### Task 5: Final validation and delivery

**Files:**
- Modify: `docs/evidence-depth/ed6/validation-results.md`
- Modify: `docs/evidence-depth/ed6/final-report.md`
- Modify: `docs/evidence-depth/ed6/progress.json`

- [ ] Run pilot-tool tests, relevant frontend tests, targeted API/projection tests, strict CKL validation, source-lock/provenance checks, current NE-9C/NE-10 compatibility, and bounded GUI checks.
- [ ] Review all required files, `git diff --check`, complete diff, generated files, ignored local data, and final branch status.
- [ ] Commit changes in coherent groups; push `feat/ed6-reader-discovery-pilot`; open one PR against `master`; do not merge or deploy.
