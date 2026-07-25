# Phase 5 Wave 10 Review: Job

Last updated: 2026-07-24

## Review status

The Job correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`job.json`](../framework/canonical_library/objects/books/job.json)
- [`test_job_record.py`](../tests/canonical_library/test_job_record.py)

## Corrections made

- Removed the inherited David, Solomon, Israel, court, temple, monarchic
  wisdom, and generic canonical-book template.
- Rebuilt the record around Job, his wife and children, Eliphaz, Bildad,
  Zophar, Elihu, the accuser, the heavenly council, messengers, servants,
  raiders, YHWH's speeches, the relatives who return, and the named daughters.
- Distinguished the prose prologue and epilogue, chapter 3 lament, three
  uneven dialogue cycles, Job 28 wisdom poem, Job's chapters 29–31
  retrospective and oath, Elihu speeches, and two divine speeches with two
  Job responses.
- Kept the reader's knowledge of the heavenly challenge separate from the
  characters' knowledge and did not claim that Job learns why he suffered.
- Qualified authorship, compositional history, date, the location of Uz,
  patriarchal-looking customs, historicity, and ancient Near Eastern
  comparisons.
- Treated *Ludlul bel nemeqi* and other righteous-sufferer texts as
  comparative evidence rather than direct proof of dependence or Job's plot.
- Distinguished the Masoretic form, substantially shorter Old Greek form,
  Qumran Hebrew fragments, and 11QtgJob.
- Explained that Hebrew *hasatan* in Job 1–2 identifies an accuser or
  adversarial council role and is not yet an unambiguous proper name carrying
  every feature of later demonology.
- Addressed retribution theology, undeserved suffering, lament, protest,
  integrity, divine justice and freedom, epistemic limits, creation beyond
  human utility, social abandonment, bodily pain, and intercession.
- Kept Job 28's speaker, Elihu's role, the force of YHWH's answer, Job 19's
  redeemer, Job 42:6, and Behemoth and Leviathan explicitly disputed.
- Refused to identify Behemoth and Leviathan confidently as dinosaurs, modern
  states, or the devil from Job 40–41 alone.
- Distinguished the restoration of relationship, wealth, and a future family
  from replacement of the first children or a universal prosperity promise.
- Added trauma-aware cautions against victim blaming, secret-sin diagnosis,
  emotional suppression, harmful counsel, and using the book as a formula for
  doubled wealth.
- Added eight sourced claims, fourteen current-taxonomy interpretive notes,
  eleven source records, explicit section statuses and knowledge layers, a
  populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `job-righteous-before-testing` | `textually_explicit` | `minor_scholarly_disagreement` |
| `job-heavenly-challenge-losses` | `textually_explicit` | `major_scholarly_disagreement` |
| `job-lament-dialogues` | `textually_explicit` | `minor_scholarly_disagreement` |
| `job-wisdom-oath` | `textually_explicit` | `major_scholarly_disagreement` |
| `job-elihu-intervention` | `textually_explicit` | `major_scholarly_disagreement` |
| `job-whirlwind-creation` | `textually_explicit` | `major_scholarly_disagreement` |
| `job-friends-rebuked-intercession` | `textually_explicit` | `major_scholarly_disagreement` |
| `job-restoration-new-family` | `textually_explicit` | `major_scholarly_disagreement` |

Every claim has a rationale, Scripture references, and source IDs that resolve
within the record. The full wording and source mappings are in
[`job.json`](../framework/canonical_library/objects/books/job.json).

## Sources used

Primary text anchors are Job 1–42 in the Masoretic tradition, Old Greek Job,
the Qumran Hebrew fragments, 11QtgJob, Ezekiel 14, and James 5. Independent
sources added in this wave:

- Carol A. Newsom, *The Book of Job: A Contest of Moral Imaginations*
  (Oxford University Press, 2009):
  <https://academic.oup.com/book/3694>
- David J. A. Clines, *Job*, volumes 17, 18A, and 18B (Word Biblical
  Commentary; Zondervan Academic, 2017 set):
  <https://zondervanacademic.com/products/job-3-volume-set-17-18a-and-18b>
- Tremper Longman III, *Job* (Baker Commentary on the Old Testament Wisdom
  and Psalms; Baker Academic, 2012):
  <https://dev.bakeracademic.com/p/Job-Tremper-III-Longman/41514>
- John H. Walton, *Job* (NIV Application Commentary; Zondervan Academic,
  2012):
  <https://zondervanacademic.com/products/job>
- C. L. Seow, *Job 1–21: Interpretation and Commentary* (Illuminations;
  Eerdmans, 2013):
  <https://eerdword.com/excerpt-from-c-l-seows-job-1-21-interpretation-and-commentary-illuminations/>
- John H. Walton, general editor, with Izak Cornelius and other contributors,
  *The Minor Prophets, Job, Psalms, Proverbs, Ecclesiastes, Song of Songs*
  (Zondervan Illustrated Bible Backgrounds Commentary, 2009):
  <https://zondervanacademic.com/products/the-minor-prophets-job-psalms-proverbs-ecclesiastes-song-of-songs>
- Amar Annus and Alan Lenzi, electronic edition of *Ludlul bel nemeqi*,
  cataloged by the Open Richly Annotated Cuneiform Corpus at the University
  of Pennsylvania Museum:
  <https://oracc.museum.upenn.edu/projectlist.html>
- Marvin H. Pope, *Job* (Anchor Yale Bible Commentary; Yale University
  Press):
  <https://yalebooks.yale.edu/9780300140750/job/>

Publisher and university pages establish bibliographic identity and scope.
The record uses the full works for textual, literary, historical, theological,
ethical, comparative, reception, and pastoral judgments; publisher summaries
do not substitute for human review.

## Retrieval coverage

The new tests require first-place book results for:

- innocent suffering;
- the accuser in the heavenly council;
- the friends' condemned counsel;
- the Job 28 wisdom poem;
- Elihu's intervention;
- Behemoth and Leviathan;
- the difficult response in Job 42:6; and
- misuse of the epilogue as a prosperity promise.

All pass with the existing retrieval implementation. No ranking-code change
was needed.

## Human review checklist

Verify:

- every section boundary, especially the disrupted third cycle, Job 28, and
  the number and boundaries of Elihu's speeches;
- Job's opening description, household practices, wealth, children, servants,
  and narrator's evaluation;
- both heavenly councils, the identity and limits of the accuser, and the
  distinction between divine permission and direct agency;
- the Sabeans, fire, Chaldeans, wind, messengers, deaths, bodily affliction,
  ash heap, and exchange with Job's wife;
- the euphemistic uses of Hebrew *barakh* traditionally translated “curse”;
- the three friends' identities, seven days of silence, speech order,
  escalating accusations, invented offenses, and epilogue rebuke;
- Job's lament, death wishes, divine accusations, integrity claims, legal
  metaphors, witness, mediator, redeemer, and continuing address to God;
- every proposal for Uz, Teman, Shuah, Naamah, Buz, Sabeans, Chaldeans, and
  the social or geographic setting;
- authorship, date, prose-poetry relationships, compositional layers, genre,
  and historicity without treating one proposal as settled;
- comparisons with *Ludlul bel nemeqi*, the Babylonian Theodicy, Sumerian
  righteous-sufferer texts, Egyptian dialogue, and ancient council or combat
  imagery;
- the textual shape of the Masoretic Text, Old Greek Job, Qumran Hebrew
  witnesses, and 11QtgJob;
- Job 28's mining imagery, speaker problem, wisdom theology, and relationship
  to the surrounding dialogue;
- Job 29–31's former honor, social ethics, present humiliation, oath formula,
  signature, and summons;
- Elihu's genealogy, anger at both sides, four-speech outline, theological
  proposals, storm transition, and absence from the epilogue;
- YHWH's two speeches, Job's two responses, every creation subject, and the
  absence of a disclosed causal answer;
- Behemoth and Leviathan vocabulary, animal comparisons, ancient mythopoetic
  background, and theological functions;
- every major translation of Job 19:25–27 and Job 42:6;
- YHWH's evaluation of Job and the three friends, sacrifice, prayer, and
  acceptance;
- restored social relationships, livestock totals, new children, daughters'
  names and inheritance, lifespan, and the continuing moral weight of the
  first children's deaths;
- Ezekiel 14, 1 Corinthians 3:19, Romans 11:35, and James 5:11 without
  flattening their selective reuse;
- Jewish interpretation before Christian typology, resurrection, or
  christological synthesis;
- every source locator, relationship, certainty, dispute label, lexical
  gloss, textual claim, and pastoral application; and
- trauma, grief, disability, illness, abuse, poverty, victim blaming,
  prosperity claims, and the risks of demanding passive “patience.”

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/job.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests/canonical_library/test_job_record.py \
  tests/canonical_library/test_esther_record.py \
  tests/canonical_library/test_golden_queries.py \
  tests/canonical_library/test_manifest.py \
  tests/canonical_library/test_quality_report.py
# 27 tests: OK

python3 -m unittest tests/canonical_library/test_*.py
# 267 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,140 edges, 0 unknown targets, 0 orphaned objects
# 2,720 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave10-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave10-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# d5008afbe209687fc1741aff6085bed04aff8cb51eb1709657f33b4b4af6632a
```

The focused regression file contains eight tests covering factual content,
template removal, governance, evidence taxonomy, source depth, graph anchors,
retrieval precision, difficult interpretive qualifications, and complete
JSON/SQLite payload parity. The known Python 3.14 unclosed-SQLite
`ResourceWarning` messages remain non-fatal test-harness debt.

## What remains

1. Obtain human review for all eighteen corrected records from Genesis
   through Job.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 48 books in small source-backed
   waves.
4. The recommended next wave is Psalms. Give special attention to the
   five-book shape, superscriptions, collections and editorial seams, psalm
   genres, parallelism and imagery, speakers and enemies, lament and praise,
   royal and messianic readings, imprecatory language, Zion and temple
   theology, creation, Torah, wisdom, divine kingship, exile and restoration,
   acrostics, Hebrew numbering and Greek/Latin numbering, textual witnesses,
   New Testament reuse, Jewish liturgy, Christian reception, and harmful
   decontextualized promises or enemy labeling.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
