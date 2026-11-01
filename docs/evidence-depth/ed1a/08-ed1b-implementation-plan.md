# ED-1B proposed implementation plan

## Objective and boundary

ED-1B should test the evidence-enrichment standard with a small reviewed research transaction. It should add no more than **one new source-grounded evidence item for each of three chapters**, and may add fewer or none if research does not support a useful record. It should not create new Narrative Explorer sections, routes, schemas, endpoints, AI dependencies, or bulk content. Reuse current CKL evidence fields and current package / validation gates.

The proposed content pilots are:

1. **Psalm 72** — historical/royal setting, poetic structure, superscription and meaningful alternatives;
2. **2 Chronicles 30** — festival narrative, north/south literary presentation, and the limits of external chronology;
3. **Ezekiel 40** — exile setting, visionary genre, internal spatial sequence and interpretive alternatives.

Use 2 Kings 18 as a positive calibration control for existing primary-source and archaeology linkage, not as an invitation to duplicate its current evidence. Use 1 Corinthians 11 to review the source/alternative rubric and discoverability, but do not expand its already dense corpus during this transaction. If a selected chapter does not yield a defensible addition after source review, record that finding and choose a replacement only through the ED-1B review.

## Work sequence

1. **Open a focused branch from a verified `origin/master`.** Capture the CKL fingerprint, source-lock state, NE-9C validation result and NE-10 registry IDs before authoring.
2. **Prepare bounded research packets.** For each chapter, specify the exact question, original audience/historical horizon, competing scholarly readings where they exist, primary and secondary source candidates, source rights, and the verse scope to be examined. Review current CKL claims and evidence first to avoid duplication.
3. **Verify sources before writing.** Consult primary sources in their own chronology and genre; use peer-reviewed or scholarly secondary work for interpretation. Record exact editions and locators. Do not scrape commentary or paste proprietary definitions.
4. **Draft at most three new CKL evidence items.** One per selected chapter, using exact passage scope, a distinct observation and interpretation, relevant chronology, source IDs and locators, confidence and rationale, and a note on uncertainty. Do not edit accepted records or source identities as a side effect. If an existing record must be corrected, defer that correction to its own reviewed task.
5. **Run current integrity and projection gates.** Validate the complete CKL, source and manifest consistency, runtime DB build/verification in a temporary output, current Narrative Explorer passage tests, and a fresh ED1A audit to show that chapter scope and source support resolve. Confirm the object/source fingerprint changes only for the intended CKL object files and manifest.
6. **Review the displayed evidence without changing the API contract.** Check that existing section and evidence-preview logic surfaces or excludes each new record for an intelligible, traceable reason. Classify any missed item as content, discovery, provenance, or presentation work. Do not widen a selector just to make the pilot count appear successful.
7. **Submit a small reviewable PR.** Include source citations, exact record IDs, review status and test output. No deployment or merge is implied by the implementation plan.

## Acceptance criteria

- Every new record is necessary for the passage and has precise, valid Scripture scope.
- Every factual or interpretive assertion is traceable to an attached CKL source ID and a specific locator where the source provides one.
- Chronology distinguishes the biblical setting, source composition, material date, and any later reception.
- Textual observation is separated from interpretation, and important alternatives and limits are represented where appropriate.
- Existing schema and validation conventions are reused; no proprietary text, unverified quotation, invented citation, archaeological identification, or speculative relationship is added.
- CKL validation, manifest/fingerprint checks, source and evidence integrity, NE-9C validation, NE-10 validation, targeted CKL evidence tests, and Narrative Explorer projection tests pass. Existing failures are reported separately and no gate is weakened.
- No NE-9C or NE-10 disposition changes; no held relationship is promoted; no generated BHF Commentary, production database, deployment configuration, endpoint, or API contract changes.
- Reader review verifies that the passage's additional evidence carries its source, exact passage relevance, chronology, and uncertainty through the existing projection.
- The PR's final diff contains only the explicitly reviewed CKL records, required manifest/source-lock updates, tests, and concise research documentation.

## Rollback considerations

Keep ED-1B's source research and CKL changes in a small logical commit. If a citation, interpretation, scope, or projection test fails review, revert the specific new record and its manifest/source-lock change, then rebuild only generated local validation artifacts. Do not apply a blanket rollback to unrelated CKL content. If a broad source-ID correction appears necessary, stop and isolate it as a separate provenance review so the three pilot records can still be accepted or reverted independently. No production state is touched in ED-1B.

## Review decision

This is a proposed plan, not authorization to author the three CKL records. ED-1A delivers the evidence inventory and research packets; the ED-1A report should be reviewed before any evidence expansion begins.
