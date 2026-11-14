# ED-6 Final Report

## Readiness judgments

- **Pilot preparation: READY WITH CONDITIONS** — study documents and a local,
  validated collection and aggregate-analysis workflow are prepared. Recruit
  consenting adults and follow the protocol before collecting results.
- **Actual reader study: AWAITING PARTICIPANTS** — no genuine participant
  sessions or feedback have been supplied for this assignment.
- **Scholarly review: HUMAN REVIEW REQUIRED** — the ED-5 packets remain
  available; no reviewer approval or correction is recorded by ED-6.

## Delivered preparation

This package defines a 20–30 minute, voluntary facilitator-led study for an
exploratory sample of approximately 6–8 adults. It provides balanced tasks,
neutral facilitation, participant-facing consent and privacy language,
observed-behavior measures, a de-identified JSONL schema, a standard-library
validator/importer/report generator, synthetic regression data, a review
kickoff, and a prioritized improvement method. Read [README](README.md) for
the first-session handoff and [validation results](validation-results.md) for
the current evidence.

The readiness checks also compared ED-5's short natural-language 1 John query
with the generic Context workspace search. Because the shorter query returned
Ezekiel rather than 1 John in the reader, ED-6 uses a passage-grounded natural
language prompt for the live 1 John task. No production search behavior or
scholarly evidence was changed.

## Findings and approvals

**Participant findings: none.** No authentic session data was present in the
authorized local input path. Synthetic fixtures and scripted journeys are not
human observations.

**Scholarly decisions: none.** No actual reviewer decision is recorded. ED-5's
12 packets remain the review set, with its first four P0 priorities listed in
the [kickoff](scholarly-review-kickoff.md).

## Maintainer handoff

For the first session: choose the next unused task assignment in
[the task bank](study-task-bank.md), read the [consent script](consent-and-privacy.md),
and begin only after an explicit yes. Use the notes template and neutral
facilitator prompts. Store de-identified JSONL only under the ignored local
`.bhf-data/ed6-reader-pilot/` directory. Validate and import using
[data-management.md](data-management.md); then produce the aggregate report
only after actual sessions exist. Keep direct observations separate from
interpretations and report every denominator. Never place names, contact
details, recordings, or raw notes in Git or a public report.

The study is exploratory and convenience-sampled. Reader usability findings
remain separate from scholarly review and do not alter CKL claims or protected
relationship decisions.

## Repository delivery

The validated branch `feat/ed6-reader-discovery-pilot` is pushed to `origin`
from current `master`. A PR could not be opened in this session: the GitHub
connector returned HTTP 403 (`Resource not accessible by integration`), the
local `gh` CLI has no authenticated session, and no browser session was
available. The pushed branch is ready to compare at
[Create ED-6 pull request](https://github.com/mcscwizzy/biblical-hermeneutics-framework/pull/new/feat/ed6-reader-discovery-pilot).
Use the title “ED-6: Prepare reader discovery pilot and scholarly review
launch” and the validation summary in this report when opening it.
