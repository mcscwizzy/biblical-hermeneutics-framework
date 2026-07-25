# Phase 5 Wave 4 Review: Judges and Ruth

Last updated: 2026-07-24

## Review status

The Judges and Ruth correction wave is implemented and machine-verified. Both
records remain `draft` / `in_review`, require human review, and have
`section_status.human_review` set to `missing`. Automated validation does not
constitute approval.

Files for review:

- [`judges.json`](../framework/canonical_library/objects/books/judges.json)
- [`ruth.json`](../framework/canonical_library/objects/books/ruth.json)
- [`test_judges_ruth_records.py`](../tests/canonical_library/test_judges_ruth_records.py)

## Corrections made

### Judges

- Removed Ruth from the book's principal people and separated the narrated
  judges period from later monarchy, exile, and disputed compositional dates.
- Rebuilt the record around its two introductions, varied judge narratives,
  Gideon/Abimelech turning point, Samson cycle, and two closing appendices.
- Represented the literary movement as deterioration rather than a flat series
  of interchangeable hero cycles.
- Added the judges, women, tribes, foreign powers, locations, vows, sanctuaries,
  civil conflict, and internal violence that belong to the book.
- Treated the no-king refrain as a complex kingship question rather than a
  blanket endorsement of monarchy.
- Explicitly qualified Jephthah's vow, the judges chronology, archaeology,
  violence, women, and moral evaluation of Spirit-empowered leaders.
- Added six sourced claims, five structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### Ruth

- Removed inherited Joshua, Solomon, Canaan, Jerusalem, Samaria, conquest,
  monarchy, and exile material from the book's own people, places, events, and
  disputes.
- Rebuilt the record around Naomi, Ruth, Boaz, famine, migration, bereavement,
  return, gleaning, harvest, the threshing floor, gate negotiation, Obed's
  birth, and the genealogy to David.
- Distinguished the judges-period narrated setting from the disputed date and
  audience of the anonymous final form.
- Treated Ruth 4 as a distinctive combination of land, kinship, lineage,
  marriage, and public transfer rather than an exact application of only
  Deuteronomy's brother-in-law law.
- Preserved Ruth's Moabite identity and agency while avoiding unsupported
  claims about a single later polemical purpose.
- Separated Matthew's explicit genealogical reuse from later Christian claims
  that Boaz is a direct type of Christ.
- Added six sourced claims, five structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| Judges | `judges-literary-movement` | `strong_consensus` | `not_disputed` |
| Judges | `judges-programmatic-pattern` | `textually_explicit` | `not_disputed` |
| Judges | `judges-deborah-leadership` | `textually_explicit` | `not_disputed` |
| Judges | `judges-gideon-abimelech-turn` | `strong_consensus` | `minor_scholarly_disagreement` |
| Judges | `judges-samson-begins-deliverance` | `textually_explicit` | `not_disputed` |
| Judges | `judges-no-king-refrain` | `textually_explicit` | `major_scholarly_disagreement` |
| Ruth | `ruth-literary-movement` | `strong_consensus` | `not_disputed` |
| Ruth | `ruth-loyal-pledge` | `textually_explicit` | `not_disputed` |
| Ruth | `ruth-gleaning-protection` | `textually_explicit` | `not_disputed` |
| Ruth | `ruth-redemption-arrangement` | `textually_explicit` | `major_scholarly_disagreement` |
| Ruth | `ruth-providence-through-action` | `strong_consensus` | `minor_scholarly_disagreement` |
| Ruth | `ruth-obed-david-genealogy` | `textually_explicit` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within its record. The
full claim wording, Scripture references, and source mappings are in the JSON
files.

## Sources used

Primary text anchors are Judges 1–21 and Ruth 1–4. Independent sources added
or reused in this wave:

- Barry G. Webb, *The Book of Judges* (Eerdmans, 2012):
  <https://www.eerdmans.com/9780802826282/the-book-of-judges/>
- Trent C. Butler, *Judges, Volume 8* (Zondervan, 2014):
  <https://zondervanacademic.com/products/judges-volume-8>
- Robert L. Hubbard Jr., *The Book of Ruth* (Eerdmans, 1989):
  <https://www.eerdmans.com/9780802883315/the-book-of-ruth/>
- Peter H. W. Lau, *The Book of Ruth* (Eerdmans, 2023):
  <https://www.eerdmans.com/9780802877260/the-book-of-ruth/>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Joshua, Judges, Ruth, 1 and 2 Samuel* (Zondervan, 2009):
  <https://zondervanacademic.com/products/joshua-judges-ruth-1-and-2-samuel>

## Retrieval changes

Expanded drafts contain vocabulary from adjacent books and related canonical
topics. The draft-ranking guard now detects when a query explicitly names a
book and gives a stronger penalty to other broad draft books. This keeps a
rich Judges record from displacing focused Joshua 24 results while preserving
first-place Judges and Ruth results for questions that name those books.

The filter accepts only literal normalized book-name matches. This avoids
treating a fuzzy analysis match such as `renewal` → `Revelation` as an
explicitly named book and preserves the covenant-renewal golden ranking.

## Human review checklist

For Judges, verify:

- the eight-part structure, downward literary movement, and differences among
  individual judge episodes;
- every leader, tribe, foreign power, location, and narrative event;
- the Gideon/Abimelech turning-point claim;
- wording about Deborah, Barak, Jael, women, victims, and escalating gendered
  violence;
- the Jephthah-vow note and its certainty classification;
- the Samson “begins to deliver” claim;
- the no-king refrain and relationship to 1 Samuel's monarchy warnings;
- chronology, regional overlap, archaeology, and settlement cautions; and
- every source locator and relationship label.

For Ruth, verify:

- the seven-part structure and emptiness-to-fullness movement;
- every person, place, harvest detail, legal action, blessing, and genealogical
  relationship;
- Hebrew terms including `hesed`, `goel`, `kanaph`, and `hayil`;
- the relationship among gleaning, land redemption, kinship, marriage, and
  preservation of the deceased's name;
- the threshing-floor caution and the nearer redeemer's stated concerns;
- statements about Moabite identity, Deuteronomy 23, and possible later
  identity debates;
- providence and human agency;
- Jewish Shavuot reception, Matthew's genealogy, and Christian typology; and
- every source locator and relationship label.

For both records, verify every certainty/dispute label, distinguish narrated
setting from compositional reconstruction and later reception, and advance
only the sections actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/judges.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/ruth.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 219 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,085 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave4-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave4-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The focused regression file contains eight tests covering factual separation,
governance, evidence taxonomy, source depth, retrieval precision, difficult
interpretive qualifications, and complete JSON/SQLite payload parity. The
known Python 3.14 unclosed-SQLite `ResourceWarning` messages remain non-fatal
test-harness debt.

## What remains

1. Obtain human review for all eight corrected records from Genesis through
   Ruth.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 58 books in small source-backed
   waves.
4. The recommended next wave is 1 Samuel and 2 Samuel, preserving the
   historical-book sequence while auditing Samuel, Saul, David, monarchy,
   covenant, violence, and differing narrated/compositional settings.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
