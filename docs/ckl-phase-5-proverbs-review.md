# Phase 5 Wave 12 Review: Proverbs

Last updated: 2026-07-24

## Review status

The Proverbs correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`proverbs.json`](../framework/canonical_library/objects/books/proverbs.json)
- [`test_proverbs_record.py`](../tests/canonical_library/test_proverbs_record.py)

## Corrections made

- Removed the inherited generic wisdom-book placeholder, including its Job,
  David, temple, suffering, praise, lament, and undifferentiated Solomonic
  content.
- Rebuilt the record around the explicit collection headings and units in
  Proverbs 1–9, 10:1–22:16, 22:17–24:22, 24:23–34, 25–29, 30, and 31.
- Distinguished Solomon, unnamed wise teachers, Hezekiah's officials, Agur,
  Lemuel, Lemuel's mother, Woman Wisdom, Woman Folly, the strange or forbidden
  woman, and the capable woman.
- Distinguished extended parental instruction, sentence sayings,
  admonitions, comparisons, better-than sayings, numerical sayings, riddling
  observations, royal instruction, autobiographical sayings, personification,
  and alphabetic poetry.
- Qualified attribution, composition, Hezekiah-era copying, social settings,
  collection history, dating, and final editing rather than assigning one
  author, date, or institution to every saying.
- Added fear of YHWH, creation, moral formation, speech, anger, work, family,
  friendship, sexuality, wealth, poverty, debt, bribery, rulers, justice, and
  social power without turning the book into a list of slogans.
- Treated Proverbs as context-sensitive moral formation rather than a set of
  unconditional promises, with Proverbs 26:4–5 as a focused example of
  situational judgment.
- Added the Instruction of Amenemope comparison while distinguishing close
  literary relationship from disputed direction and mechanism of dependence.
- Added Hebrew lexical cautions for *mashal*, *hokmah*, *musar*, *lev*,
  *zarah*, *nokriyah*, *qanah*, *amon*, *eshet hayil*, and *shevet*.
- Distinguished Masoretic and Old Greek Proverbs, including interpretive
  additions and the Greek form's different ordering of material corresponding
  to portions of chapters 24, 30, and 31.
- Put Proverbs in canonical dialogue with Job and Ecclesiastes so ordinary
  moral patterns cannot become exhaustive explanations of suffering,
  injustice, poverty, prosperity, or death.
- Added ethical safeguards against misogynistic use of the strange woman,
  compulsory use of Proverbs 31 against women, abusive use of rod sayings,
  victim-blaming, prosperity teaching, and simplistic blame of poor people.
- Distinguished Proverbs 8's female poetic personification and difficult
  Hebrew and Greek wording from later technical christological claims.
- Added eleven sourced claims, sixteen current-taxonomy interpretive notes,
  seventeen source records, explicit section statuses and knowledge layers,
  a populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `proverbs-multiple-collections` | `textually_explicit` | `minor_scholarly_disagreement` |
| `proverbs-purpose-fear-yhwh` | `textually_explicit` | `minor_scholarly_disagreement` |
| `proverbs-rival-women-paths` | `strong_consensus` | `minor_scholarly_disagreement` |
| `proverbs-wisdom-creation` | `textually_explicit` | `lexical_uncertainty` |
| `proverbs-amenemope-parallels` | `probable` | `major_scholarly_disagreement` |
| `proverbs-hezekiah-copying` | `textually_explicit` | `historical_uncertainty` |
| `proverbs-agur-lemuel-voices` | `textually_explicit` | `historical_uncertainty` |
| `proverbs-capable-woman-acrostic` | `textually_explicit` | `minor_scholarly_disagreement` |
| `proverbs-contextual-generalizations` | `strong_consensus` | `minor_scholarly_disagreement` |
| `proverbs-poverty-justice-complexity` | `textually_explicit` | `minor_scholarly_disagreement` |
| `proverbs-greek-order` | `textually_explicit` | `textual_variant` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and source mappings are in
[`proverbs.json`](../framework/canonical_library/objects/books/proverbs.json).

## Sources used

Primary witnesses are Masoretic Proverbs, Old Greek Proverbs, the Instruction
of Amenemope, and representative New Testament quotations and echoes.
Independent sources added:

- Michael V. Fox, *Proverbs 1–9* (Anchor Yale Bible Commentary; Yale
  University Press, 2000):
  <https://yalebooks.yale.edu/book/9780300139594/proverbs-1-9/>
- Michael V. Fox, *Proverbs 10–31* (Anchor Yale Bible Commentary; Yale
  University Press, 2009):
  <https://yalebooks.yale.edu/book/9780300142099/proverbs-10-31/>
- Bruce K. Waltke, *The Book of Proverbs, Chapters 1–15* (NICOT; Eerdmans,
  2004):
  <https://www.eerdmans.com/9780802825452/the-book-of-proverbs-chapters-1-15/>
- Richard J. Clifford, *Proverbs: A Commentary* (Old Testament Library;
  Westminster John Knox Press, 1999):
  <https://www.wjkbooks.com/bookproduct/0664228534-proverbs/>
- Katharine J. Dell, *The Theology of the Book of Proverbs* (Cambridge
  University Press, 2023):
  <https://www.cambridge.org/core/books/theology-of-the-book-of-proverbs/BC224F5F5A33D9C03C3173D2CB22FF8F>
- Anne W. Stewart, *Poetic Ethics in Proverbs* (Cambridge University Press,
  2015):
  <https://www.cambridge.org/core/books/poetic-ethics-in-proverbs/FE8E38BAC87C85476599B746D75FCBAE>
- Stuart Weeks, *Instruction and Imagery in Proverbs 1–9* (Oxford University
  Press, 2007):
  <https://academic.oup.com/book/11971>
- Esperanza Alfonso, “Late Medieval Readings of the Strange Woman in
  Proverbs” (Oxford University Press, 2015):
  <https://academic.oup.com/fordham-scholarship-online/book/15193/chapter-abstract/169682563>
- Jacqueline Vayntrub, “Beauty, Wisdom, and Handiwork in Proverbs 31:10–31”
  (*Harvard Theological Review*, 2020):
  <https://www.cambridge.org/core/journals/harvard-theological-review/article/abs/beauty-wisdom-and-handiwork-in-proverbs-311031/C47DF1ADB831556BBAF6412F05D1D116>
- British Museum, “Papyrus EA10474,2: Teaching of Amenemope”:
  <https://www.britishmuseum.org/collection/object/Y_EA10474-2>
- Johann Cook, *A New English Translation of the Septuagint: Proverbs*
  (IOSCS, 2007):
  <https://ccat.sas.upenn.edu/nets/edition/25-proverbs-nets.pdf>
- Lorenzo Cuppi, “Proverbs,” in *The Oxford Handbook of the Septuagint*
  (Oxford University Press, 2021):
  <https://academic.oup.com/edited-volume/34470/chapter-abstract/292460954>
- James L. Crenshaw, “Wisdom Traditions and the Writings: Sage and Scribe,”
  in *The Oxford Handbook of the Writings of the Hebrew Bible* (Oxford
  University Press, 2018):
  <https://academic.oup.com/edited-volume/28060/chapter/212044262>
- John H. Walton, general editor, *The Minor Prophets, Job, Psalms, Proverbs,
  Ecclesiastes, Song of Songs* (Zondervan Illustrated Bible Backgrounds
  Commentary, 2009):
  <https://zondervanacademic.com/products/the-minor-prophets-job-psalms-proverbs-ecclesiastes-song-of-songs>

Publisher, university, scholarly-organization, and museum pages establish
bibliographic identity, scope, textual evidence, or artifact identity. They do
not substitute for a qualified reviewer checking each use and locator.

## Retrieval coverage

The new tests require first-place book results for:

- whether Solomon wrote every proverb;
- Agur, Lemuel, and Lemuel's mother;
- Hezekiah's officials and Proverbs 25;
- maxims versus unconditional promises;
- Proverbs 26:4–5;
- Amenemope and Proverbs 22;
- Woman Wisdom and Woman Folly;
- misuse of Proverbs 31 as a compulsory checklist;
- rod sayings and child abuse;
- the different order of Greek Proverbs; and
- poverty, laziness, and victim-blaming.

All pass with the existing retrieval implementation. One exact child-discipline
alias was added to make the safety-critical wording discoverable; no
ranking-code change was needed.

## Human review checklist

Verify:

- the wording, bounds, relationships, and sequence of every collection heading
  and major unit;
- whether Proverbs 1:1 governs the whole received work literarily and what it
  can establish historically;
- distinctions among composition, attribution, transmission, collection,
  copying, editing, and final placement;
- all proposed dates for Solomonic traditions, Hezekiah's officials,
  Proverbs 1–9, the named final collections, the Hebrew anthology, and Greek
  translation;
- proposed household, court, scribal-school, village, commercial, and
  administrative settings without claiming that one institution produced the
  book;
- definitions and examples of instruction, sentence saying, admonition,
  numerical saying, riddling observation, better-than saying, royal counsel,
  autobiography, personification, and acrostic poetry;
- Hebrew parallelism, sound, repetition, imagery, catchwords, juxtaposition,
  clusters, and contextual tensions;
- *mashal*, *hokmah*, *musar*, *binah*, *daat*, *yirat YHWH*, *lev*,
  *tsedeq*, *mishpat*, *peti*, fool terms, *lets*, *zarah*, *nokriyah*,
  *qanah*, *amon*, *eshet hayil*, and *shevet*;
- every parallel proposed between Proverbs 22:17–24:22 and the Instruction of
  Amenemope, including the limits of claims about direct dependence;
- Woman Wisdom and Woman Folly as literary figures, their possible cultural
  backgrounds, and the rhetoric of their rival calls, paths, houses, meals,
  and destinies;
- the strange or forbidden woman language, male addressee, male agency,
  ethnicity questions, sexual ethics, and history of harmful gendered use;
- Proverbs 8:22–31 in Hebrew and Greek, especially *qanah*, *amon*,
  personification, creation, and Jewish and Christian reception;
- every claim concerning work, wealth, poverty, debt, boundaries, scales,
  bribery, courts, rulers, generosity, oppression, and structural power;
- parent, child, correction, and rod texts with contemporary safeguarding,
  trauma, disability, anger, legal, and pastoral expertise;
- Proverbs 31:1–9 as a mother's royal instruction and 31:10–31 as alphabetic
  praise, including labor, household, class, trade, generosity, wisdom, and
  fear of YHWH;
- observations, expectations, commands, consequences, exceptions, and
  promises without forcing one genre on every saying;
- Proverbs 26:4–5 and other juxtaposed or repeated sayings as exercises in
  contextual discernment;
- canonical dialogue with Torah, prophets, Psalms, Job, Ecclesiastes, Ben
  Sira, Wisdom of Solomon, and Qumran wisdom texts;
- the Greek order, additions, translational character, recensional questions,
  and possible source-text differences;
- every New Testament quotation and echo in its own argument;
- christological reception without erasing Woman Wisdom, Jewish Scripture, or
  the lexical and literary limits of Proverbs 8;
- every source locator, support target, certainty label, dispute label, and
  pastoral application; and
- misogyny, xenophobia, child abuse, domestic abuse, coercive control,
  victim-blaming, prosperity teaching, class bias, ableism, and poverty
  stigma.

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/proverbs.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests/canonical_library/test_proverbs_record.py \
  tests/canonical_library/test_psalms_record.py \
  tests/canonical_library/test_job_record.py \
  tests/canonical_library/test_golden_queries.py \
  tests/canonical_library/test_manifest.py
# 34 tests in 31.673s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 284 tests in 131.549s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,150 edges, 0 unknown targets, 0 orphaned objects
# 2,720 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave12-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave12-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# fdfbed1572f68cf93ff8ff8c4826dd45bb7502fece5d1d158961945da24ffb75
```

The focused regression file contains eight tests covering factual content,
template removal, collection structure, governance, evidence taxonomy, source
depth, graph anchors, retrieval precision, difficult interpretive
qualifications, and complete JSON/SQLite payload parity. The known Python 3.14
unclosed-SQLite `ResourceWarning` messages remain nonfatal test-harness debt.

## What remains

1. Obtain human review for all twenty corrected records from Genesis through
   Proverbs.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 46 books in small source-backed
   waves.
4. The recommended next wave is Ecclesiastes. Audit its frame narrator,
   Qohelet's voice, superscription, royal persona, first-person investigation,
   poems, sayings, tensions, epilogue, authorship, date, historical and social
   setting, Hebrew and Greek textual questions, *hebel*, *yitron*, enjoyment,
   toil, wisdom, injustice, time, death, God, judgment, and canonical dialogue
   with Proverbs, Job, Psalms, later Jewish wisdom, and New Testament
   reception.
5. Explicitly guard against nihilistic flattening, forced harmonization of
   Qohelet and the epilogue, prosperity claims, using “a time for” to justify
   harm, victim-blaming, dismissing grief or depression, and treating “under
   the sun” as a technical slogan for a secular worldview without contextual
   argument.
6. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
