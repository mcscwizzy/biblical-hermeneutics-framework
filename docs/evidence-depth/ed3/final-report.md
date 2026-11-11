# ED-3 Final Report

**Audit outcome:** completed with documented source-access, test-suite, and
historical-checkpoint limits. **No human scholarly approvals were recorded.**

## Branch and scope

- Branch: `audit/ed3-scholarly-integrity`
- Base: `origin/master` at `8a0bda764328f9399552e46c224c949b35c064fc`; a final fetch confirmed the upstream tip was unchanged.
- Final branch commit and PR comparison: recorded in the repository delivery after publication.
- No merge or deployment was performed.

ED-3 reconciled and assessed every one of the 99 evidence records introduced by
ED-2, investigated inherited source-integrity findings, checked reader
disclosure and mobile behavior, and prepared an independent human review queue.
It did not generate a new evidence wave.

## Scholarly source review

| Freshly inspected material | Records | Limit |
|---|---:|---|
| Full scholarly text, including full dissertation/article text | 8 | Relevant cited sections were inspected; not every source argument in every record was freshly reproduced. |
| Relevant excerpt | 4 | The remainder of each cited publication was not available or inspected. |
| Abstract and/or bibliographic metadata | 18 | Claims remain bounded to the inspected abstract or metadata. |
| No new source text inspected | 69 | ED-2's reported access was kept separate from fresh ED-3 inspection. |

The 99 machine-assisted outcomes are: **27 supported with limitations, 1
correction required, and 71 unable to independently verify**. No item was
marked human-reviewed, accepted, or publication-approved. Five Greek text
observations were checked against the SBL Greek New Testament text. No critical
apparatus, manuscript image, papyrus, scroll, inscription, archaeological
object, or primary artifact edition was independently examined for this audit.
The direct witness/artifact verification count is therefore **zero**; the five
edition text checks do not establish manuscript priority.

All 21 abstract-only, 3 excerpt-only, and 3 mixed-access cases were rechecked
through legitimate publisher or institutional routes. Restricted full text was
not circumvented. Remaining source requests and record-level questions are in
the [source verification report](source-verification.md) and each
[review packet](human-review-packets/).

## Corrections and unresolved provenance

- **Psalm 17:** The full Italian article was newly consulted at pp. 398–402 and
  406–407. The CKL source note and interpretation now state that the proposals
  are not consensus, preserve their conjectural/attested distinction, and
  include the author's caution about the reported manuscript support for v. 11.
  The critical apparatus and manuscript evidence remain unchecked; low
  confidence and disputed status remain.
- **Roman Ephesus:** Two unresolved child-source references were repaired to
  exact, existing source identities: `harland-associations-ephesus` and
  `glancy-slavery-ephesus`. No bibliography was fabricated.
- **`patristic-minor-prophets`:** The expected locator remains unresolved. The
  collection-level source could be identified, but no defensible passage,
  page, or section locator was established.
- **Inherited source heuristics:** All 102 source-support-target signals were
  classified (45 IDs present as claims elsewhere, 14 existing top-level fields
  not flattened by the checker, 24 generic category labels, 19 unresolved
  semantic targets). The rules were not weakened. The historical set of 558
  sparse bibliography IDs was triaged; 472 are Scripture/text identities and
  86 reference-work identities. No ambiguous publication identity was guessed
  and no sparse bibliography entry was manufactured.

See [correction log](scholarly-corrections.md),
[source-integrity findings](source-integrity-findings.md), and
[source-integrity fixes](source-integrity-fixes.md) for record-level details.

## Human review and reader transparency

The searchable queue and 99 concise packets are grouped across the five ED-2
research waves. Every decision, reviewer name, date, rationale, and correction
field remains blank. All 99 records remain `draft`, `in_review`, and
`human_review_required`; none has an approval recorded. The reusable
[human review process](human-review-process.md) defines the five permitted
review outcomes without filling one in.

Narrative Explorer displays the draft-review notice before provenance is
expanded. Live Chromium checks verified a real **390 CSS-pixel** viewport
(`innerWidth` and `screen.width` 390, DPR 1) for six exact-passage samples:
Psalms, wisdom, historical books, prophets, a Gospel textual dispute, and an
ED-1C reception record. The sample set included an abstract-limited record.
All six showed one eligible evidence card, accessible uncertainty/provenance,
and no horizontal overflow. Firefox's effective 500-pixel narrow viewport was
not counted as a 390-pixel check. `npm test` passed 17/17.

Full results are in [reader acceptance](reader-acceptance.md).

## Research depth

The reproduced 1,189-chapter inventory has 1,089 chapters with passage-specific
material, 56 contextual-only, 2 entity-only, 41 with no eligible CKL material,
and 1 incomplete/unknown. A stricter item-count view finds 669 chapters with
more than one eligible item, 479 with exactly one, and 41 with none. The
book-by-book backlog ranks source-led work across all 66 books. Its 494 unique
thin-passage candidates are a research signal, not a quota. No mass expansion
wave was opened.

See [research depth priorities](research-depth-priorities.md) and the
[candidate inventory](thin-passage-candidates.csv).

## Technical validation and protected governance

- `python tools/validate.py framework/`: 94 modules valid.
- Strict CKL validation: 687 valid objects, 0 errors, 14 inherited warnings.
- Deep CKL report: 1,408 typed evidence items, 63 error-severity heuristic
  findings, 1,093 warnings, and 102 inherited support-target signals. The two
  child-source reference repairs leave 0 unresolved child-source references.
- Focused Python/API/projection/curation/source-lock tests: 584 passed; the
  exact Validate workflow release group: 50 passed.
- Full frontend suite: 17 passed.
- Full ED-1A census: 1,189 chapter rows, 0 unmapped identities, 19 sample
  checks, 16 targeted service builds.
- Profiles generated without a diff. Wheel and sdist built; required package
  contents passed inspection, retired generated-commentary payload remained
  absent, and installed-wheel CLI/app/default-CKL smoke loaded 687 objects.
- NE-9C/NE-10 current registry counts: **433 accepted identities** (431
  object, 2 evidence), **44 verified passage bridges**, and **7 held
  candidates**. Protected files and checkpoint hashes match the baseline; no
  held relationship was promoted.

The unfiltered repository test run was stopped after 23:10. It had reported 54
passed tests, 892 passed subtests, and two retrieval-order failures before
interruption. Both exact failures were reproduced on an isolated archive of the
ED-2 `origin/master`: “What if our heart condemns us?” returned `john` instead
of `1-john`; “How does 1 Thessalonians relate to Acts 17?” returned `acts`
instead of `1-thessalonians`. They are inherited retrieval behavior; ED-3 did
not change retrieval logic.

The legacy `ne9c_bulk_curation.py validate` command stops at its frozen CKL
fingerprint mismatch. This same mismatch was recorded on the unmodified ED-2
base because the historical checkpoint predates ED-2 CKL additions. ED-3
preserved the checkpoint and verified authored identities, protected hashes,
and compatibility tests without refreshing the frozen fingerprint.

The full gate record is [validation results](validation-results.md).

## Final readiness

**Technical readiness: READY WITH CONDITIONS.** The supported release-focused
and ED-3 regression gates pass. The repository-wide test run is incomplete and
has two failures confirmed on the base revision; the frozen NE-9C bulk
checkpoint validator retains its documented pre-ED-2 fingerprint limit.

**Scholarly publication readiness: HUMAN REVIEW REQUIRED.** All 99 ED-2 items
remain drafts awaiting independent qualified review. The 71 unable-to-verify
records and all primary-witness questions remain explicitly assigned for that
review.

## Pull request

The final branch push and PR comparison are pending publication in Phase 10.
