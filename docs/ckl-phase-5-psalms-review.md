# Phase 5 Wave 11 Review: Psalms

Last updated: 2026-07-24

## Review status

The Psalms correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`psalms.json`](../framework/canonical_library/objects/books/psalms.json)
- [`test_psalms_record.py`](../tests/canonical_library/test_psalms_record.py)

## Corrections made

- Removed the inherited Solomon-centered wisdom-book authorship, audience,
  setting, Job, court, and generic canonical-book content.
- Rebuilt the record as a five-book anthology with the paired Psalms 1–2
  gateway, doxological seams, Book III covenant crisis, Book IV
  YHWH-kingship emphasis, Book V pilgrimage and Torah clusters, and Psalms
  146–150 conclusion.
- Distinguished Davidic, Asaphite, Korahite, Solomonic, Mosaic, Hemanite,
  Ethanite, Songs of Ascents, Hallel, and anonymous materials without treating
  every superscription as a modern byline.
- Added individual and communal lament, praise, thanksgiving, royal, Zion,
  Torah, wisdom, creation, historical, penitential, enthronement, imprecatory,
  and pilgrimage genres while explicitly allowing mixed forms.
- Qualified composition, collection, editing, original setting, historical
  notices, speakers, enemies, Hebrew parallelism, musical labels, and uncertain
  terms such as *maskil*, *miktam*, and *selah*.
- Distinguished the 150-psalm Masoretic form, Qumran Psalms manuscripts,
  Greek and Latin numbering, and Psalm 151. The record identifies the
  combinations of Psalms 9–10 and 114–115 and divisions of Psalms 116 and 147.
- Added the Great Psalms Scroll's different order, additional compositions,
  and David prose composition while leaving its classification disputed.
- Addressed prayer, lament, protest, praise, divine kingship, Torah, wisdom,
  creation, Zion, temple, exile, restoration, Davidic hope, nations, justice,
  mortality, the poor, and universal worship.
- Kept royal, messianic, and christological readings within Israelite, Jewish,
  New Testament, and Christian reception contexts rather than making every
  first-person speaker Jesus.
- Added ethical cautions concerning Psalm 137, imprecations, enemy labeling,
  political and territorial appropriation, decontextualized protection or
  prosperity promises, trauma, and use of Psalm 51 after abuse.
- Added nine sourced claims, fifteen current-taxonomy interpretive notes,
  twelve source records, explicit section statuses and knowledge layers, a
  populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `psalms-five-book-anthology` | `textually_explicit` | `minor_scholarly_disagreement` |
| `psalms-gateway-torah-king` | `strong_consensus` | `minor_scholarly_disagreement` |
| `psalms-superscription-collections` | `textually_explicit` | `major_scholarly_disagreement` |
| `psalms-lament-praise-range` | `strong_consensus` | `minor_scholarly_disagreement` |
| `psalms-book-three-crisis` | `textually_explicit` | `major_scholarly_disagreement` |
| `psalms-exile-restoration-pilgrimage` | `strong_consensus` | `minor_scholarly_disagreement` |
| `psalms-qumran-plurality` | `textually_explicit` | `major_scholarly_disagreement` |
| `psalms-numbering-witnesses` | `textually_explicit` | `textual_variant` |
| `psalms-new-testament-reception` | `textually_explicit` | `denominational_disagreement` |

Every claim has a rationale and source IDs that resolve within the record.
The Qumran claim appropriately has no canonical verse locator because it
describes a manuscript artifact; its primary and institutional sources are
explicit. Full wording and source mappings are in
[`psalms.json`](../framework/canonical_library/objects/books/psalms.json).

## Sources used

Primary witnesses are the Masoretic Psalter, Qumran Psalms manuscripts,
especially 11QPs-a, the Septuagint and subsequent Latin numbering traditions,
Psalm 151, and representative New Testament quotations and echoes.
Independent sources added or retained in corrected form:

- John Goldingay, *Psalms* (Baker Commentary on the Old Testament Wisdom and
  Psalms, three volumes; Baker Academic):
  <https://tst.bakeracademic.com/p/Psalms-John-Goldingay/40486>
- Nancy L. deClaissé-Walford, Rolf A. Jacobson, and Beth LaNeel Tanner, *The
  Book of Psalms* (NICOT; Eerdmans, 2014):
  <https://www.eerdmans.com/9780802824936/the-book-of-psalms/>
- Frank-Lothar Hossfeld and Erich Zenger, *Psalms 2* and *Psalms 3*
  (Hermeneia; Fortress Press):
  <https://ms.fortresspress.com/downloads/HermeneiaBrochure_2018.pdf>
- Mitchell Dahood, *Psalms I 1–50* (Anchor Yale Bible Commentary; Yale
  University Press):
  <https://yalebooks.yale.edu/book/9780300139563/psalms-i-1-50/>
- Nancy L. deClaissé-Walford, “The Meta-Narrative of the Psalter,” in *The
  Oxford Handbook of the Psalms*:
  <https://academic.oup.com/edited-volume/35006/chapter/298743361>
- Rolf A. Jacobson and Michael J. Chan, “Chapter 20: Psalms,” online resources
  for *Introducing the Old Testament* (Baker Academic):
  <https://bakeracademic.com/pages/jacobson-chan-introducing-the-old-testament-esources-1>
- Library of Congress, “The Psalms Scroll,” *Scrolls from the Dead Sea*
  exhibition:
  <https://www.loc.gov/exhibits/scrolls/scr1.html>
- John H. Walton, general editor, with Richard E. Averbeck and other
  contributors, *The Minor Prophets, Job, Psalms, Proverbs, Ecclesiastes,
  Song of Songs* (Zondervan Illustrated Bible Backgrounds Commentary):
  <https://zondervanacademic.com/products/the-minor-prophets-job-psalms-proverbs-ecclesiastes-song-of-songs>

Publisher, university, and government-institution pages establish
bibliographic identity and scope. The record uses the works for textual,
literary, historical, comparative, theological, ethical, reception, and
pastoral judgments; those pages do not substitute for human review.

## Retrieval coverage

The new tests require first-place book results for:

- Davidic authorship and the 150 psalms;
- the five-book Psalter;
- Asaphite and Korahite headings;
- *selah*;
- imprecatory prayer;
- Psalm 137 and violence against children;
- Greek, Latin, and Septuagint numbering;
- the Great Psalms Scroll;
- misuse of protection promises; and
- New Testament use of Psalm 110.

All pass with the existing retrieval implementation. No ranking-code change
was needed.

## Human review checklist

Verify:

- the number, boundaries, closing doxologies, and characteristic contents of
  all five books;
- the paired function of Psalms 1–2 and the literary role of Psalm 150 and
  Psalms 146–150;
- every stated Davidic, Asaphite, Korahite, Solomonic, Mosaic, Hemanite,
  Ethanite, Hallel, pilgrimage, and anonymous collection;
- Hebrew superscription grammar, the dates and status of titles, and every
  historical notice without applying one authorship theory uniformly;
- the proposed monarchic, temple, military, healing, festival, exilic, and
  post-exilic settings without assigning unsupported dates;
- lament, thanksgiving, hymn, royal, Zion, Torah, wisdom, creation,
  historical, penitential, enthronement, imprecatory, and pilgrimage genre
  definitions, including mixed forms;
- parallelism, lineation, imagery, metaphor, refrains, acrostics, voice
  changes, and liturgical dialogue;
- *tehillim*, *mizmor*, *tehillah*, *tefillah*, *maskil*, *miktam*,
  *lamnatseach*, *selah*, *torah*, *hesed*, *ashre*, *mashiach*, *nephesh*,
  *sheol*, and *hallelu-yah*;
- ancient Egyptian, Mesopotamian, Ugaritic, and West Asian comparisons without
  treating resemblance as proof of direct dependence;
- Masoretic, Qumran, Greek, and Latin evidence for text, order, and numbering,
  especially Psalms 9–10, 114–115, 116, 147, and 151;
- 11QPs-a contents, date, order, extra compositions, David prose text, and
  competing canonical-edition or liturgical-anthology models;
- Psalm 89's creation, covenant, royal rejection, protest, and position at the
  end of Book III;
- temple-destruction, exile, return, pilgrimage, and restoration claims in
  Psalms 74, 79, 89, 102, 107, 120–137, and related texts;
- divine kingship, creation, Torah, wisdom, justice, the poor, mortality,
  nations, enemies, Zion, temple, Davidic promise, and universal praise;
- the rhetoric and ethics of enemy petitions and imprecations, especially
  Psalm 137:9, without silencing survivors or licensing retaliation;
- protection and flourishing language alongside the Psalter's illness,
  violence, defeat, abandonment, injustice, and death;
- Psalm 51's received David–Nathan–Bathsheba title and the necessity of
  victim-centered truth, accountability, restitution, safeguarding, and
  repair;
- every New Testament quotation or echo and whether its relationship is
  quotation, allusion, analogy, typology, corporate representation, or claimed
  fulfillment;
- Jewish liturgical and messianic reception before Christian appropriation;
- Christian worship and christological trajectories without erasing the
  Psalter as Jewish Scripture;
- every source locator, relationship, certainty, dispute label, textual
  statement, and pastoral application; and
- trauma, grief, abuse, displacement, political violence, disability,
  dehumanizing enemy labels, nationalism, and territorial or prosperity
  misuse.

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/psalms.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests/canonical_library/test_psalms_record.py \
  tests/canonical_library/test_job_record.py \
  tests/canonical_library/test_golden_queries.py \
  tests/canonical_library/test_manifest.py \
  tests/canonical_library/test_quality_report.py
# 28 tests in 119.364s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 276 tests in 450.173s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,146 edges, 0 unknown targets, 0 orphaned objects
# 2,720 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave11-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave11-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 2255e2ba7edd4aa7440e36bd9db91ee2c08364e7dd5f34f10f1c3a98d7aa70c8
```

The focused regression file contains nine tests covering factual content,
template removal, five-book structure, governance, evidence taxonomy, source
depth, graph anchors, retrieval precision, difficult interpretive
qualifications, and complete JSON/SQLite payload parity. The known Python
3.14 unclosed-SQLite `ResourceWarning` messages remain nonfatal test-harness
debt.

## What remains

1. Obtain human review for all nineteen corrected records from Genesis
   through Psalms.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 47 books in small source-backed
   waves.
4. The recommended next wave is Proverbs. Audit its multi-collection
   structure, superscriptions, sentence sayings, instructions, poems,
   personified Wisdom and Folly, royal and scribal settings, ancient Near
   Eastern parallels, Hebrew poetics, gendered voices, discipline, poverty
   and wealth, speech, work, family, justice, retribution, misuse as absolute
   promises, and New Testament reception.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
