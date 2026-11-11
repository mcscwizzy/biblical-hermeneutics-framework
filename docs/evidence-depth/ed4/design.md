# ED-4 Design

## Intent

ED-4 improves discovery, traceability, and maintenance of BHF's existing
research library. It repairs deterministic retrieval defects, makes the 99 ED-2
review packets actionable for qualified reviewers, distinguishes confirmed
provenance defects from heuristic signals, adds a current-state curation
compatibility check without altering the frozen historical checkpoint, and
verifies reader access and the Obadiah census anomaly. It does not create a new
evidence wave or record scholarly approvals.

## Goals

- Preserve context-first, evidence-grounded retrieval across numbered books,
  explicit references, comparisons, and ordinary-language questions.
- Give a maintainer a searchable, filterable way to inspect and track each
  pending review item, record only explicit human decisions, append corrections
  to an auditable history, and export actual decisions.
- Keep the ED-3 queue, stable evidence IDs, CKL governance, curation decisions,
  and source locks intact unless a specific identity defect is established.
- Report machine checks, heuristic warnings, access limitations, and human
  scholarly judgments as separate things.
- Verify representative desktop and 390 CSS-pixel reader journeys, including
  source disclosure and additional sourced records.
- Complete repository regression gates, report inherited limits accurately,
  and leave the feature branch pushed but unmerged and undeployed.

## Non-goals and anti-goals

- No mass evidence generation or filler records.
- No paid search service, model API, or vector database.
- No unauthenticated public approval route and no invented reviewer identity,
  credentials, dates, rationales, or decisions.
- No weakening of CKL, source-lock, curation, package, API, or release checks.
- No refreshing or rewriting the historical NE-9C frozen fingerprint.
- No approximation-based provenance repair, guessed bibliography identity, or
  fabricated Malachi locator.
- No redesign of Narrative Explorer.

## Approaches considered

1. **Extend deterministic BHF retrieval and add a local maintainer workbench**
   (selected). BHF already owns its alias parser, lexical ranker, CKL index,
   reviewer queue, and packet files. A local CLI can display packet contents,
   filter the queue, and append human decisions to an ignored JSONL ledger
   without adding an unauthenticated endpoint or service dependency.
2. **Add an in-app reviewer interface.** This could be convenient, but the
   repository has no suitable authenticated reviewer authorization flow. A
   safe version would require a broader identity, access-control, and hosting
   design outside ED-4's scope.
3. **Adopt an external review or search service.** This adds cost, dependencies,
   and external state; it is unnecessary for the bounded queue and prohibited
   paid search requirement.

The assignment explicitly selects the first approach through its constraints
and fallback requirement. The existing feature-branch checkout is the isolated
workspace. The work proceeds sequentially through the eight requested phases.

## Design boundaries

### Retrieval

Keep the current deterministic CKL retrieval stack. Correct whole-token alias
recognition and overlapping numbered-book matches. Model reference roles only
where the wording distinguishes a primary passage from its supporting context;
keep both sides of a genuine comparison available. Add a bounded, labeled
regression set across both Testaments and include before-and-after rank output.

### Human review

Provide repository-maintainer commands for listing/searching/filtering records,
showing the source packet and its locators/questions, recording one of the five
allowed human decisions, recording correction and verification events, and
exporting a reproducible report. The source queue and packet files remain
unchanged. The default decision ledger lives outside Git under ignored local
study data; each appended event preserves stable CKL evidence ID, reviewer
identity and expertise, date, action, rationale, inspected sources/access
scope, and any correction. Empty state means no decision. Machine validation
never creates a decision.

### Source and governance integrity

Inspect all 19 unresolved semantic support targets and the reference-work
subset of the 558 sparse IDs. Repair only exact, verifiable identity defects.
Keep unresolved questions and incomplete metadata visible. Add a separate
read-only current-state compatibility validator for the protected NE-9C/NE-10
identities, hashes, held/excluded state, and runtime registry resolution while
retaining the old validator's frozen fingerprint behavior.

### Reader and census

Use existing Narrative Explorer projection, UI, and API routes. Make only a
narrow presentation change if a reproduced defect warrants it. Trace Obadiah
through canonical book identity, Scripture anchor parsing, eligible projection,
and both detailed and strict census outputs before editing anything.

## Validation

Use the existing CKL, source-lock, curation, API/projection, retrieval,
frontend, census, package, and release gates. Add focused tests for each new
behavior and run the repository suite with a bounded execution window. Browser
checks must report actual viewport dimensions. Technical validation does not
constitute scholarly approval.

## Remaining builder decisions

Choose concrete CLI syntax and local ledger serialization that fit the current
Python tooling; retain append-only review history and never edit CKL governance
automatically. Decide whether an investigated signal has an exact existing
target only after reading its authoring conventions and source/object data.
