# NE-11B decisions and implementation contract

## Scope and baseline

NE-11B is a review-only phase. It records eligibility and exact future acceptance conditions; it does not add routes, promote candidates, or change CKL, NE-9C, or NE-10.

- Required NE-11A audit commit `c2cb939dcd4ced0bf601ac22d9015a70307abaa7` is an ancestor of `origin/master`.
- Actual `master` and `origin/master` baseline: `b37a159aab092b28a599928b2326a2d7c2e2d1fc`.
- Work branch: `research/ne11b-evidence-grounded-connections`.
- Baseline worktree before NE-11B documents: clean.
- CKL inventory: 687 JSON objects; inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.
- CKL object-byte tree fingerprint: `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`.
- NE-9C bulk state: 3,925 reviewed identities over 4,061 inventory rows; 408 curated, 1,622 excluded, and 1,895 held. Active curated identities: 433. Full registry tree fingerprint: `691c9201d50eb0cceccac1b1a6d1beaa58f65b96cac54241cc856c8e2bc87a31`; active identity fingerprint: `528f6a36dd729a90d16beaa023400bb80821f021f25417076d3b8f831e016dd0`.
- NE-10 state: 43 active bridge identities and 7 held candidates. Registry tree fingerprint: `6dfe864406a2b28fa2ec7c997f7cb66decabf645f483706d25c76058512649b6`; active identity fingerprint: `c0c329dd1002a5519a1bc5301975b7821a81802b98eec6ebd837e473c97e919f`; held identity fingerprint: `ad1a754affefdcb5bfe7aff0b7c059d0624521b85ecd42c7cda7f870656608d3`.
- Read all four NE-11A reports: `01-coverage-baseline.md`, `02-visibility-gap-analysis.md`, `03-prioritized-opportunities.md`, and `04-implementation-recommendations.md` under `docs/narrative-explorer/ne11a/`.

## Eligibility decisions

| Relationship | Status | Proposed exact route | Canonical change required? |
|---|---|---|---|
| Psalm 22:1 → Mark 15:34 | **NEEDS_CKL_REFINEMENT** | `direct_quotation`; source-to-receiver direction, reversible display; proposed future record `mark#claim:mark-psalm-22-1-mark-15-34` | **Yes.** Add a verse-scoped record and establish a verse-specific Psalm witness/source locator before a route can be promoted. |
| Jonah 1:17 → Matthew 12:40 | **READY_AS_IS** | `later_canonical_reception`; source-to-receiver direction, reversible display; existing record `jonah#claim:jonah-three-days` | No CKL change. A separately authorized NE-10 bridge insertion would still be required before runtime exposure. |
| Psalm 110:1 / Acts 2:22–36 held candidate | Reconciliation only: keep held, no second bridge | Active NE-9C route already points to Psalm 110:1–7 from Acts 2:22–36; do not duplicate | No change in NE-11B. |

The two primary relationship decisions use the status vocabulary specified in NE-11B. Psalm 110 is explicitly limited to reconciliation and receives no new eligibility approval.

## Future implementation acceptance conditions

Implementation is a separate, later authorization. No provisional candidate from this review is a confirmed runtime route.

### A. Psalm 22 / Mark

Before adding an NE-10 route:

1. Add CKL record `mark#claim:mark-psalm-22-1-mark-15-34` with exact Scripture references `Psalm 22:1` and `Mark 15:34`; use a claim/evidence type appropriate to a textual quotation.
2. Attach the Mark Greek text source ID `mark-greek` and a resolving Psalm text source ID that identifies the Hebrew witness/edition and exact locator (MT Psalm 22:2 / standard Psalm 22:1). Existing `psalms-mark` may be used only if its record is refined to provide that specificity.
3. Confirm both exact endpoints are inside the evidence record scope and that the claim expressly identifies the quotation. Do not inherit eligibility from `Mark 15:16-41` or the book-level source list alone.
4. Add at most one route with ID `psalm-22-1-mark-15-34-cry`, `passages=[Psalm 22:1, Mark 15:34]`, `source_text_passage=Psalm 22:1`, `receiving_text_passage=Mark 15:34`, category `direct_quotation`, `direction=source_to_receiving_text`, `evidence_layer=direct_textual_relationship`, and reversible display.
5. Set `supporting_records` to one claim record `{object_id: mark, record_kind: claim, record_id: mark-psalm-22-1-mark-15-34, source_ids: [mark-greek, psalms-mark]}` after both source IDs resolve and the Psalm locator is verse-specific.
6. Use explanation: Mark 15:34 places a Semitic form and Greek rendering of Psalm 22:1’s opening lament on Jesus’ lips. State that the route concerns this verse only; state that the larger theological and literary interpretation remains debated.
7. Run CKL source/integrity and NE10/projection checks. Verify no second Psalm 22 / Mark route and no change to protected curated paths.

### B. Jonah / Matthew

If NE-10 implementation is later authorized:

1. Use existing record `jonah#claim:jonah-three-days`; no new canonical claim is required for the narrow pair.
2. Add one route with ID `jonah-1-17-matthew-12-40-sign-of-jonah`, `passages=[Jonah 1:17, Matthew 12:40]`, `source_text_passage=Jonah 1:17`, `receiving_text_passage=Matthew 12:40`, category `later_canonical_reception`, `direction=source_to_receiving_text`, `evidence_layer=later_reception`, and reversible display.
3. Set `supporting_records` to one claim record `{object_id: jonah, record_kind: claim, record_id: jonah-three-days, source_ids: [jonah-masoretic, jonah-new-testament]}`. The attached scholarly ID `graybill-kaltner-mckenzie-jonah` is not independently verified for the precise issue; do not imply that it was.
4. Explain that Matthew explicitly compares Jonah’s narrated duration in the fish with the Son of Man’s time in the heart of the earth. Note `Jonah 1:17` is MT/LXX Jonah 2:1.
5. Preserve uncertainty about idiom, chronology, “heart of the earth,” and literary interpretation. Do not say Jonah’s original narrative was written as a prediction.
6. Run NE10 schema, source-provenance, route-projection, and collision checks. Preserve the existing 43 bridge identities except for this explicitly authorized insertion.

### C. Psalm 110 / Acts 2 and negative controls

No code or registry edit is approved for Psalm 110. Preserve the active NE-9C route and held candidate `psalm-110-acts-2-enthronement`; do not add a second route. If future work proposes to narrow an active endpoint, it requires its own reviewed decision and registry change.

Keep all seven current NE-10 held candidates held:

- `deuteronomy-32-psalm-82-job-1-divine-assembly`
- `exodus-12-1-corinthians-5-passover`
- `ezekiel-37-john-3-water-spirit`
- `ezekiel-40-48-revelation-21-22-temple`
- `genesis-2-3-revelation-21-22-eden-tree-life`
- `isaiah-43-exodus-12-15-new-exodus`
- `psalm-110-acts-2-enthronement`

Existing curated pathways remain protected. No finding in NE-11B authorizes promotion of a negative-control candidate.

## Evidence classification summary

- **Scripture observations:** The exact wording and scopes summarized in the individual reviews are directly checkable in the cited Hebrew and Greek text pages.
- **Independently inspected academic material:** de Lang on Mark 15:34–37; Combs on the proposed wider Psalm 22/Mark 15 allusion; Waters on the interpretive and chronological questions in Matthew 12:39–41. Each is reported as a particular scholarly argument, not consensus.
- **CKL bibliographies not independently checked at the relevant pages:** Marcus and the Postcolonial Mark source for the Psalm/Mark claim; Graybill, Kaltner, and McKenzie for the Jonah claim. Those entries remain recorded in CKL but are not treated as proof of precise propositions.
- **Debate preserved:** The meaning and extent of Psalm 22’s literary use in Mark; Jonah’s chronology/idiom and Matthew’s “heart of the earth” and reception; and the original setting and later messianic readings of Psalm 110.
- **Research limits:** The reviews compare critical text editions, not a full manuscript apparatus or every textual witness. Where no accessible scholarly page or exact commentary section was inspected, that gap is named rather than filled with an assumed consensus.

## Verification record

Completed checks:

- `python3 -m framework.canonical_library --root framework/canonical_library --json` passed: 687 objects; inventory fingerprint remains `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. Recomputed SHA-256 over all 687 CKL object files remains `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`.
- `python3 scripts/ne9c_bulk_curation.py --source-root . --state-dir docs/narrative-explorer/ne9c-bulk-curation validate` passed with 3,925 reviewed rows, 4,061 inventory rows, 408 curated, 1,622 excluded, and 1,895 held. NE-9C tree hash remains `691c9201d50eb0cceccac1b1a6d1beaa58f65b96cac54241cc856c8e2bc87a31` and the curated-identity hash remains `528f6a36dd729a90d16beaa023400bb80821f021f25417076d3b8f831e016dd0`.
- NE-10 registry tree hash remains `6dfe864406a2b28fa2ec7c997f7cb66decabf645f483706d25c76058512649b6`. The 43 bridge IDs and seven held candidate IDs retain hashes `c0c329dd1002a5519a1bc5301975b7821a81802b98eec6ebd837e473c97e919f` and `ad1a754affefdcb5bfe7aff0b7c059d0624521b85ecd42c7cda7f870656608d3`. The held-file status remains `research_candidates_only_excluded_from_confirmed_passage_graph`.
- Focused command: `.venv/bin/python -m pytest -q tests/canonical_library/test_manifest.py tests/canonical_library/test_loader.py tests/canonical_library/test_source_locks.py tests/canonical_library/test_scripture_reference_integrity.py tests/canonical_library/test_typed_evidence_targets.py tests/canonical_library/test_schema.py tests/test_ne9c_bulk_curation.py tests/test_narrative_explorer_projection.py tests/test_narrative_explorer_passages.py tests/test_narrative_explorer_curation.py tests/test_narrative_explorer_api.py`. Result: **724 passed, 1 failed**. The only failure was `CanonicalInventoryTests.test_all_inventory_json_files_validate_and_receive_governance_defaults`: `genesis-abraham-call-covenant-context` has `review_status=in_review` but an empty `generated_by` list, violating the existing test assertion. This CKL input is unchanged from the `master` baseline and is outside NE-11B scope; no integrity gate was weakened or altered.
- Direct text pages for the Hebrew and Greek passages and the cited academic material were checked. Relative Markdown links in the four new documents resolve; all external links are directly cited. `git diff --check` is clean.
- Final worktree scope is exactly the four NE-11B Markdown files. CKL objects and manifest, NE-9C, NE-10, application code, and production behavior are unchanged. No generated files were added.
- The staged full diff was reviewed and `git diff --cached --check` passed. Record the final commit SHA and comparison URL in the handoff. Do not merge or deploy.
