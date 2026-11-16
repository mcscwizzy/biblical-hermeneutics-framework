# ED-6 Reader Discovery Pilot Design

## Intent

Prepare BHF for an exploratory study with approximately 6–8 consenting adult
readers. The study measures observed discovery, contextual understanding,
clarity, evidence verification, and navigation continuity. It does not rate
spiritual maturity, doctrinal agreement, or the truth of a participant's
interpretation. If no genuine participant records are available, ED-6 ends with
a clearly labeled pilot-ready handoff.

## Goals

- Provide a practical 20–30 minute facilitator-led session with four comparable
  tasks per participant and a varied passage pool.
- Explain voluntary participation, stopping, optional recording, privacy, and
  local data handling in plain language.
- Reuse ED-5's checked-in task passages, evidence identities, and reviewer index.
- Provide a file-based, de-identified session schema, validator/importer, and
  aggregate report generator with synthetic fixtures segregated from real data.
- Run bounded Chromium acceptance checks for the selected reader tasks,
  including mobile at 390 CSS pixels and keyboard operation.
- Prepare the first 3–5 scholarly review requests from ED-5's priority index
  without creating or implying any reviewer decision.

## Non-goals and anti-goals

- Do not fabricate reader participation, ratings, quotations, or scholarly
  approval.
- Do not modify CKL claims, evidence, source identities, source locks, NE-9C
  curations, NE-10 bridges, or held candidates.
- Do not add production analytics, accounts, recording, external uploads, a
  public study application, paid services, or deployment changes.
- Do not present disagreement with a participant as a usability failure or
  doctrinal error.

## Approaches

1. **Local JSONL toolkit (selected).** A small standard-library Python tool
   validates/imports de-identified session records and generates aggregate
   counts. It keeps records in an ignored local directory, is easy to review,
   and can report incomplete sessions without dropping observations.
2. **Spreadsheet-first collection.** Familiar to facilitators, but less
   reproducible for schema validation and safe append/import behavior.
3. **New web form or study application.** Adds deployment, data-retention, and
   tracking decisions that are unnecessary for this small pilot and conflict
   with the no-upload requirement.

## Design decisions

- Keep study documents in `docs/evidence-depth/ed6/` and data tooling in
  `tools/ed6_reader_pilot.py` with standard-library-only runtime code.
- Keep authentic local records under `.bhf-data/ed6-reader-pilot/`; the
  repository ignore rules must prevent them from entering Git.
- Put synthetic-only records under `tests/fixtures/ed6_reader_pilot/` and make
  the normal CLI reject synthetic-origin records.
- Report denominators for every measure. Treat missing answers as unobserved,
  not as failures. Preserve incomplete sessions and surface invalid records by
  line and field without printing raw personal text.
- Store facilitator observations separately from facilitator interpretations.
  The default aggregate report contains counts, not raw free-text notes.
- Reuse ED-5 passage/evidence IDs and the existing ED-4 workbench. No reviewer
  identity or outcome is invented or entered by ED-6.
- Add bounded Chromium acceptance coverage only; change production behavior
  only if a demonstrated blocker prevents a valid study task.

## Constraints

- A session lasts about 20–30 minutes and participation is voluntary.
- No name, email, church, IP address, account, recording, or sensitive
  religious background is required.
- A recording requires separate explicit consent and a stated private storage
  location.
- Reader success measures are completion, assistance, time, observed problems,
  evidence/source/uncertainty recognition, and genuine follow-up questions.
- A small convenience sample is exploratory usability research only.
- Do not merge or deploy.

## Implementation ownership

The implementer will finalize task assignment balance, data-field validation,
report formatting, and the exact bounded browser command after inspecting the
current ED-5 tools and test infrastructure. These choices must preserve the
constraints above and current CKL/NE-9C/NE-10 governance.
