# ED-4 final report

## Delivery

- Branch: `feat/ed4-research-quality-and-review`
- Base: verified ED-3 merge on `origin/master`, `31832793a155b16b6d694b1e84202bac1ee47c38`
- PR comparison against `master`: [Open the ED-4 comparison](https://github.com/mcscwizzy/biblical-hermeneutics-framework/compare/master...feat/ed4-research-quality-and-review?expand=1). The branch head SHA is reported in the delivery note.
- The branch was pushed to `origin`. No merge or deployment was performed.

## Retrieval

ED-4 corrected two inherited ranking defects. Numbered-book aliases no longer
shadow their unnumbered counterparts, and book-name parsing now requires a
complete alias word boundary, removing false references such as `Revelation`
inside “relate,” `Hebrews` inside “Hebrew,” and `Judges` inside “judging.”
Explicit A-to-B relationship questions identify A as the primary passage while
preserving B as supporting context. Comparisons remain symmetric.

The shared coherent-match index now includes text from an individually
Scripture-anchored interpretive note, while excluding its rationale, caveats,
references, and unanchored notes. This restores both the “judging nothing
before the time” result through its 1 Corinthians 4:5 note and the unprefixed
“What if our heart condemns us?” result through its 1 John 3:19–24 claim. The
progressive-form match is limited to the evidence side of coherent, anchored
units; a general stop word removes the common question word `if`. No book-
specific exception, global stemming, paid search service, or model call was
added. The final retrieval suite passed. Scores and representative comparisons
are in [retrieval before/after](retrieval-before-after.md).

## Human review

The local review workbench lists and filters all 99 original ED-3 queue
records, opens their packets, summarizes actual decisions, exports completed
reviews, and records explicitly attributed human decisions/corrections in an
ignored hash-chained JSONL ledger. It does not write approvals from machine
results. No reviewer identity, review date, decision, rationale, correction,
or approval was invented or recorded by ED-4. All 99 records remain pending;
actual human approvals recorded: **0**.

The 71 “unable to independently verify” records remain verification/access
limitations, not findings that their claims are false. Records with abstract-
only or excerpt-only sources, textual proposals, manuscript comparisons, and
disputed language readings still require qualified independent review.

## Source integrity and compatibility

Of 102 existing source-support-target signals, 45 resolve as cross-object
claim identities, 14 resolve to existing top-level fields, and 24 are generic
field/category labels. Nineteen semantic targets remain unresolved because no
precise existing identity can be verified; no approximate mappings were
invented. Reference-work bibliography review found no basis for bulk
normalization. The 472 Scripture/text source IDs were retained. The 86
reference-work identities were triaged for material author/work conflicts,
edition metadata, locators, and duplicates; no unsupported identity rewrites
were made. One Malachi bibliography entry’s author identity was corrected to
Hauna T. Ondrey and the accessible-preview limit was documented with an
Introduction locator. The source identity and scholarly claims were preserved.
See the [OUP catalog entry](https://academic.oup.com/book/11063) and
[source integrity report](source-integrity-results.md).

The historical NE-9C validator and frozen CKL fingerprint remain unchanged.
The separate read-only current-state compatibility validator passes and
confirms the protected curation hashes, 3,925 reviewed relationship
identities, 44 verified bridges, 7 held candidates, and all current registry
dispositions. Its report makes clear that the current CKL fingerprint differs
from the frozen historical one.

## Reader and coverage

API projections and selected desktop/mobile Chromium journeys passed for
historical/cultural context, literary convention, word study, manuscript
variants, later reception, disputed interpretation, draft-review labels,
source details, navigation, and unassigned source-backed CKL child records.
At 390 CSS px there was no horizontal overflow or duplicate item; locators
remained readable at 320px and 390px. No presentation change was needed.

The Obadiah anomaly was one malformed verse anchor: `Obadiah 7` was parsed as
a nonexistent chapter. Correcting it to `Obadiah 1:7` preserved the record,
source IDs, and review status. The full census now reports 1,090
passage-specific chapters, 56 contextual-only, 2 entity-only, 41 with no
eligible CKL material, and zero incomplete/unknown chapters. The corrected
Obadiah chapter contains 63 eligible items and zero unresolved anchors.

## Validation

Strict CKL validation passes with 687 valid objects, zero errors, and 14
warnings. The deep report remains unchanged at 63 heuristic error-severity
signals, 1,093 warnings, and 102 support-target signals; these heuristic
signals were not suppressed. The full census, targeted API/retrieval/source
integrity suites, frontend suite, profile freshness checks, release-focused
Python group, wheel/sdist content checks, and installed-wheel smoke all pass.

The repository-wide pytest run outcome, any inherited failures, and any new
regressions are recorded in [validation results](validation-results.md).

## Readiness

**Technical readiness:** READY WITH CONDITIONS. Targeted retrieval, reader,
compatibility, package, and release gates pass. The repository-wide pytest run
was stopped at its 25-minute bound after 55 tests and 934 subtests passed; it
was interrupted while entering a slower SQLite setup for the next test, with
no failure reported before the timeout. The 19 support-target identities
remain subject to source-owner or qualified-human follow-up.

**Scholarly publication readiness:** HUMAN REVIEW REQUIRED. The queue has 99
records awaiting qualified human decisions, including 71 with independent
source-verification limitations. Machine validation is not scholarly
approval.
