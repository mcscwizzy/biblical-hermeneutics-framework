# ED-4 Execution Plan

This plan follows the user's requested phase order. Each completed phase gets a
focused commit and an updated `progress.json`; no merge or deployment is
included. The user's explicit autonomous directive is the execution approval.

## File map

| Area | Expected files | Responsibility |
|---|---|---|
| ED-4 records | `docs/evidence-depth/ed4/README.md`, `baseline.md`, `progress.json`, `design.md`, this plan, and the phase reports | Baseline, decision boundaries, phase evidence, limitations, and final delivery. |
| Retrieval | `framework/canonical_library/retrieval/tokenizer.py`, `models.py`, and `service.py` only if root-cause tests require them | Whole-token book aliases, non-overlapping numbered-book recognition, and explicit passage-role ranking. |
| Retrieval evaluation | New focused test(s) under `tests/canonical_library/` and a small fixture if it improves readability | Bounded two-Testament relevance set; preserve non-book semantic retrieval and ambiguous/no-passage outcomes. |
| Review workbench | `tools/ed4_review_workbench.py` and focused `tests/test_ed4_review_workbench.py` | Local list/filter/show, explicit append-only review events, correction verification, progress, and report export. No public endpoint. |
| Current compatibility | `tools/validate_ed4_curation_compat.py` and focused compatibility tests | Read-only checks for current reviewed IDs, authored relationship IDs, runtime compatibility, held/excluded items, bridge integrity, and protected hashes. |
| Source integrity | Existing CKL objects only for confirmed exact identity/reference defects; reports under `docs/evidence-depth/ed4/` | Resolve findings only with verifiable identity evidence; document unresolved source questions without guessing. |
| Reader and census | Existing Narrative Explorer implementation only for a reproduced presentation/mapping defect; corresponding tests if changed | Confirm passage evidence disclosure, additional records, source locators, mobile scope, and Obadiah classification. |

Do not change ED-3 packets or queue, reviewed NE-9C/NE-10 decisions, source
locks, the frozen fingerprint, or scholarly content as a side effect.

## Phase tasks

## Task 0: Phase 0 — Baseline

1. Confirm `origin/master` and ED-3 merge, create the requested branch, and
   record the clean worktree state.
2. Run the two inherited retrieval test files, strict/deep CKL reports,
   framework validation, and the 1,189-chapter census; count queue rows and
   packets and record current protected registry identities/hashes.
3. Write `README.md`, `baseline.md`, and initial `progress.json` with exact
   outputs and commands. Commit the baseline and plan.

## Task 1: Phase 1 — Retrieval

1. Add failing tests for substring alias rejection (`re` inside `relate`),
   numbered-book overlap (1/2/3 John and other ordinal series), both inherited
   rankings, explicit verse scope, two-passage comparisons, and a no-confident-
   passage case.
2. Add a bounded set across both Testaments for book, verse, language,
   historical/cultural, narrative relationship, comparison, ambiguous title,
   ordinary-language, and negative/ambiguous retrieval.
3. Capture baseline result order and score relevance before changing the
   parser or ranker. Apply one general parser/ranking correction at a time and
   rerun focused red/green checks. Ensure comparison members remain jointly
   retrievable and semantic records still surface.
4. Record cause, ranked before/after output, all evaluation expectations, and
   measured regressions in `retrieval-analysis.md` and
   `retrieval-before-after.md`; commit the validated fix.

## Task 2: Phase 2 — Human review

1. Add failing tests for preserved queue/evidence IDs, searching and filtering
   by book/priority/evidence type/access limit, packet/source locator display,
   blank status, explicit decision validation, and export.
2. Implement a local maintainer CLI that reads the unchanged ED-3 queue and
   packet files and stores review events in ignored local study data. Require
   human identity, expertise, date, decision, rationale, inspected source
   scope, and explicit action. Append events; never rewrite history or CKL
   approval fields.
3. Support an explicit correction request and a separate attributed
   verification event. Report decision status and actual event history. Do
   not write decisions during this assignment.
4. Document commands and safeguards in `review-workflow.md`; validate all 99
   packet links and original evidence IDs; commit.

## Task 3: Phase 3 — Source integrity

1. Inspect the exact object/source fields and authoring convention for each of
   the 19 unresolved targets. Repair only an exact target/reference identity
   defect; retain semantic uncertainty where the intended relation cannot be
   established.
2. Review reference-work bibliography identities from the 86-item ED-3 subset
   with priority to records actually used by reader-facing evidence, plus
   conflicting edition/locator/duplicate signals. Leave legitimate Scripture
   IDs and ambiguous author/work identities unchanged.
3. Inspect the `patristic-minor-prophets` publication and accessible index;
   cite an exact Malachi locator only if verified. Otherwise preserve the
   limitation.
4. Improve source diagnostics only if a distinction is demonstrated without
   weakening a gate. Record exact before/after counts and deferred questions
   in `source-integrity-results.md`; run CKL integrity and source-lock tests;
   commit.

## Task 4: Phase 4 — Current-state compatibility

1. Inspect frozen NE-9C validator inputs, current curation registries, bridge
   validators, and protected hashes. Preserve the historical mismatch test.
2. Add failing tests for accepted identity coverage, authored relationship
   IDs, held/excluded preservation, current runtime resolution, bridge
   validity, and protected artifact hash mismatch.
3. Add a separate read-only current-state validator and focused tests. Do not
   derive or write scholarly decisions.
4. Document old versus current validator use in `compatibility-checks.md`;
   run the historical validator and new validator to demonstrate their
   intentionally different fingerprints; commit.

## Task 5: Phase 5 — Reader usefulness and transparency

1. Inspect the current retrieval/search entry points, Narrative Explorer API,
   CKL projection, disclosure controls, and existing ED-1C additional-record
   behavior. Exercise samples for historical context, literary convention,
   language, variants, cultural practice, later reception, disputed views,
   and unassigned source-backed child records.
2. Verify text/observation, evidence, proposal, dispute, and later-reception
   labels, draft status, source locators, duplicate count, and source
   disclosure. Change presentation code only if an actual failure is
   reproduced and protected by a focused regression test.
3. Use live desktop and true 390 CSS-pixel mobile browser viewports for
   overview navigation, evidence preview, additional records, source details,
   draft labels, search, long locators, and back navigation. Record dimensions
   and results in `reader-acceptance.md`; commit.

## Task 6: Phase 6 — Obadiah

1. Trace Obadiah 1 from the book registry and chapter enumeration through
   anchor formatting, CKL object identity, eligible passage projection, and
   detailed/strict census classifiers.
2. Add a failing test first if a technical mapping defect is demonstrated;
   fix only that mapping, preserving research data. If it is an audit
   limitation or real content gap, do not add filler.
3. Record exact before/after status and evidence in `obadiah-investigation.md`;
   commit.

## Task 7: Phase 7 — Regression and release

1. Run CKL schema/deep integrity, source locks, target behavior, retrieval,
   Narrative Explorer/API, curation/held-route, review-workbench, frontend,
   framework validation, chapter census, compatibility, and package/release
   gates. Check profiles and generated artifacts.
2. Attempt the full repository suite with a documented bound. Separate
   inherited failures, corrected failures, new regressions, checkpoint limits,
   and scholarly source limitations.
3. Run `git diff --check`, inspect the complete diff and protected files, and
   complete `validation-results.md` and `final-report.md`; commit.

## Task 8: Phase 8 — Final delivery

1. Reproduce the baseline/final counts, verify zero human decisions were
   recorded, ensure all requested ED-4 reports exist and links/commands work,
   inspect the full diff and final commit/worktree state.
2. Push `feat/ed4-research-quality-and-review` and provide one comparison URL
   against `master`. Do not merge or deploy.
3. Set the final readiness classifications separately for technical and
   scholarly publication state.

## Review focus

- Numbered aliases must match the complete canonical name and must not erase a
  separately named book in a true comparison.
- A passage reference may identify a focus, supporting context, or one side of
  an explicit comparison; ranking must preserve that distinction.
- No-passage ambiguity must remain visible rather than acquiring a false
  confident result.
- Local review logs must be append-only, attributable, input-validated, and
  outside Git by default.
- Current compatibility checks must fail on changed protected state while
  leaving the historical fingerprint check unchanged.
- Reader and census fixes must not modify scholarly curation or source data
  without exact evidence of an identity defect.
