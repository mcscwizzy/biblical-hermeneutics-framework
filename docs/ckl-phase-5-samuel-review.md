# Phase 5 Wave 5 Review: 1 Samuel and 2 Samuel

Last updated: 2026-07-24

## Review status

The 1 Samuel and 2 Samuel correction wave is implemented and
machine-verified. Both records remain `draft` / `in_review`, require human
review, and have `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`1-samuel.json`](../framework/canonical_library/objects/books/1-samuel.json)
- [`2-samuel.json`](../framework/canonical_library/objects/books/2-samuel.json)
- [`test_samuel_records.py`](../tests/canonical_library/test_samuel_records.py)

## Corrections made

### 1 Samuel

- Removed inherited Joshua, Solomon, Canaan, Jerusalem, Samaria, conquest, and
  exile material from the book's own people, places, and events.
- Rebuilt the structure around Hannah and Samuel, the ark narrative, Israel's
  monarchy request, Saul's selection and rejection, David's rise and flight,
  Endor, Ziklag, and Gilboa.
- Distinguished the narrated early-monarchy setting from disputed source,
  composition, chronology, and final-form proposals.
- Represented 1 Samuel 8–12's simultaneous criticism, permission, selection,
  and covenantal accountability of monarchy.
- Qualified the shorter Greek and longer Masoretic David-and-Goliath forms,
  Saul's harmful spirit, the Endor episode, and the ethics of the Amalek
  command.
- Added six sourced claims, five structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### 2 Samuel

- Removed inherited Joshua, Samaria, conquest, and exile material from the
  book's own people, places, and events while retaining Solomon's birth and
  explicitly locating his accession in 1 Kings.
- Rebuilt the structure around David's accession, Jerusalem and the ark, the
  house promise, Mephibosheth, Bathsheba and Uriah, Tamar and Amnon,
  Absalom's rebellion, Sheba's revolt, and the four-part closing appendix.
- Added the court, household, military, prophetic, harmed, and dissenting
  figures needed to represent the narrative rather than reducing it to David
  alone.
- Treated David's taking of Bathsheba and killing of Uriah as condemned abuse
  of royal power rather than a harmless romance, and retained Tamar's voice
  and harm within the book's central royal crisis.
- Qualified the scope and later development of the Davidic house promise, the
  different census-agency language in Samuel and Chronicles, and what
  archaeology can establish about Davidic dynasty and kingdom scale.
- Added six sourced claims, five structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| 1 Samuel | `first-samuel-literary-movement` | `strong_consensus` | `not_disputed` |
| 1 Samuel | `first-samuel-hannah-reversal` | `textually_explicit` | `not_disputed` |
| 1 Samuel | `first-samuel-ark-not-talisman` | `strong_consensus` | `not_disputed` |
| 1 Samuel | `first-samuel-accountable-monarchy` | `textually_explicit` | `major_scholarly_disagreement` |
| 1 Samuel | `first-samuel-saul-rejected` | `textually_explicit` | `not_disputed` |
| 1 Samuel | `first-samuel-david-spares-saul` | `textually_explicit` | `not_disputed` |
| 2 Samuel | `second-samuel-literary-movement` | `strong_consensus` | `not_disputed` |
| 2 Samuel | `second-samuel-david-lament` | `textually_explicit` | `not_disputed` |
| 2 Samuel | `second-samuel-jerusalem-ark` | `textually_explicit` | `not_disputed` |
| 2 Samuel | `second-samuel-davidic-house` | `textually_explicit` | `major_scholarly_disagreement` |
| 2 Samuel | `second-samuel-david-condemned` | `textually_explicit` | `not_disputed` |
| 2 Samuel | `second-samuel-absalom-rebellion` | `textually_explicit` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within its record. The
full wording, Scripture references, and source mappings are in the JSON files.

## Sources used

Primary text anchors are 1 Samuel 1–31 and 2 Samuel 1–24. Independent sources
added or reused in this wave:

- David Toshio Tsumura, *The First Book of Samuel* (Eerdmans, 2007):
  <https://www.eerdmans.com/9780802823595/the-first-book-of-samuel/>
- Ralph W. Klein, *1 Samuel, Volume 10*, second edition (Zondervan, 2014):
  <https://zondervanacademic.com/products/1-samuel-volume-10>
- David Toshio Tsumura, *The Second Book of Samuel* (Eerdmans, 2019):
  <https://www.eerdmans.com/9780802870964/the-second-book-of-samuel/>
- Arnold A. Anderson, *2 Samuel, Volume 11* (Zondervan, 2015):
  <https://zondervanacademic.com/products/2-samuel-volume-11>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Joshua, Judges, Ruth, 1 and 2 Samuel* (Zondervan, 2009):
  <https://zondervanacademic.com/products/joshua-judges-ruth-1-and-2-samuel>

## Retrieval correction

The Samuel regression tests found that a trailing question mark prevented the
named-book draft-ranking guard from recognizing `2 Samuel` as explicitly
named. That allowed the complete `davidic-covenant` topic record to precede
the named book even when 2 Samuel had the stronger raw score.

Named-book token comparison now uses the same punctuation-normalized alias
form used elsewhere in retrieval. The direct question “What does the Davidic
covenant promise in 2 Samuel?” now returns `2-samuel` first. Golden retrieval,
prior-wave retrieval, and all CKL tests still pass.

## Human review checklist

For 1 Samuel, verify:

- the seven-part structure and movement from failed priestly leadership to
  Samuel, Saul, David, and Gilboa;
- every person, place, battle, ark movement, royal action, and event;
- the integration of positive and negative monarchy material in chapters
  8–12;
- Saul's two rejection judgments and the wording of the Amalek claim;
- the David-and-Goliath textual-variant note;
- wording about Saul's harmful spirit, David and Jonathan, Abigail, and Endor;
- chronology, Philistine history, archaeology, and composition cautions; and
- every source locator and relationship label.

For 2 Samuel, verify:

- the six-part structure and placement of chapters 21–24;
- every court and household figure, location, rebellion, battle, and event;
- the house/temple/dynasty wording and discipline in 2 Samuel 7;
- wording about royal coercion, Bathsheba, Uriah, Tamar, Amnon, and David's
  failures as king and father;
- Joab's political and military role and David's responses to unauthorized
  killings;
- the Gibeonite/Saulide episode, Rizpah, the census, and Araunah's floor;
- the Samuel/Chronicles census comparison and archaeological qualification;
- the distinction between Solomon's birth here and accession in 1 Kings; and
- every source locator and relationship label.

For both records, verify every certainty/dispute label, distinguish narrated
setting from compositional reconstruction and later reception, and advance
only the sections actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/1-samuel.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/2-samuel.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 227 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,093 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave5-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave5-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The focused regression file contains eight tests covering factual separation,
governance, evidence taxonomy, source depth, retrieval precision, difficult
interpretive qualifications, and complete JSON/SQLite payload parity. The
known Python 3.14 unclosed-SQLite `ResourceWarning` messages remain non-fatal
test-harness debt.

## What remains

1. Obtain human review for all ten corrected records from Genesis through
   2 Samuel.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 56 books in small source-backed
   waves.
4. The recommended next wave is 1 Kings and 2 Kings, preserving the
   historical-book sequence while auditing Solomon, the divided kingdoms,
   prophetic ministries, Assyrian and Babylonian settings, archaeology, and
   the fall of Samaria and Jerusalem.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
