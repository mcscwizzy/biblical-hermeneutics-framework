# Phase 5 Wave 3 Review: Deuteronomy and Joshua

Last updated: 2026-07-24

## Review status

The Deuteronomy and Joshua correction wave is implemented and
machine-verified. Both records remain `draft` / `in_review`, require human
review, and have `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`deuteronomy.json`](../framework/canonical_library/objects/books/deuteronomy.json)
- [`joshua.json`](../framework/canonical_library/objects/books/joshua.json)
- [`test_deuteronomy_joshua_records.py`](../tests/canonical_library/test_deuteronomy_joshua_records.py)

## Corrections made

### Deuteronomy

- Anchored the narrated setting on the plains of Moab before the Jordan
  crossing and kept that setting distinct from disputed compositional dates.
- Removed the duplicate Sinai-covenant event and replaced the thin inherited
  outline with the book's movement from retrospective speeches through
  covenant instruction, blessing and curse, renewal, succession, song,
  blessing, and Moses's death.
- Added the people, locations, institutions, vulnerable community members,
  public Torah practices, and major interpretive questions that belong to the
  book.
- Distinguished the Horeb covenant from the explicitly named Moab covenant.
- Treated treaty comparison, centralized worship, composition, warfare,
  chronology, and route identification as questions requiring evidence rather
  than settled facts.
- Added five sourced claims, four structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### Joshua

- Removed inherited later-history material concerning David, Solomon,
  monarchy, exile, Jerusalem, and Samaria from the book's own people, places,
  events, and setting.
- Rebuilt the structure around succession and entry, campaigns, remaining
  land and allotment, refuge and Levitical cities, the altar dispute, farewell,
  and covenant renewal at Shechem.
- Preserved both the book's broad promise-fulfillment and victory summaries
  and its explicit remaining-land and incomplete-possession notices.
- Kept Jericho, Ai, Hazor, Mount Ebal, settlement models, chronology, victory
  rhetoric, and the historical reconstruction of the conquest under explicit
  archaeological or scholarly caution.
- Represented warfare and `herem` as an interpretive and ethical dispute,
  while also retaining Rahab's rescue, oath keeping, tribal unity, and covenant
  accountability.
- Added five sourced claims, five structured interpretive notes, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| Deuteronomy | `deuteronomy-literary-movement` | `strong_consensus` | `not_disputed` |
| Deuteronomy | `deuteronomy-shema-love` | `textually_explicit` | `not_disputed` |
| Deuteronomy | `deuteronomy-moab-covenant` | `textually_explicit` | `not_disputed` |
| Deuteronomy | `deuteronomy-choose-life` | `textually_explicit` | `not_disputed` |
| Deuteronomy | `deuteronomy-moses-joshua-transition` | `textually_explicit` | `not_disputed` |
| Joshua | `joshua-literary-movement` | `strong_consensus` | `not_disputed` |
| Joshua | `joshua-torah-shaped-leadership` | `textually_explicit` | `not_disputed` |
| Joshua | `joshua-rahab-rescue` | `textually_explicit` | `not_disputed` |
| Joshua | `joshua-fulfilled-and-remaining-land` | `textually_explicit` | `major_scholarly_disagreement` |
| Joshua | `joshua-shechem-covenant` | `textually_explicit` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within its record. The
full claim wording, Scripture references, and source mappings are in the JSON
files.

## Sources used

Primary text anchors are Deuteronomy 1–34 and Joshua 1–24. Independent sources
added or reused in this wave:

- Jeffrey H. Tigay, *The JPS Torah Commentary: Deuteronomy* (Jewish
  Publication Society, 1996):
  <https://jps.org/books/jps-torah-commentary-deuteronomy/>
- Ian Cairns, *Deuteronomy: Word and Presence* (Eerdmans, 1992):
  <https://www.eerdmans.com/9780802801609/deuteronomy/>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Genesis, Exodus, Leviticus, Numbers, Deuteronomy* (Zondervan,
  2009):
  <https://zondervanacademic.com/products/genesis-exodus-leviticus-numbers-deuteronomy>
- Marten Woudstra, *The Book of Joshua* (Eerdmans, 1981):
  <https://www.eerdmans.com/9780802825254/the-book-of-joshua/>
- Trent C. Butler, *Joshua*, second edition, volumes 7A and 7B (Zondervan,
  2014):
  <https://zondervanacademic.com/products/joshua-2-volume-set-7a-and-7b>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Joshua, Judges, Ruth, 1 and 2 Samuel* (Zondervan, 2009):
  <https://zondervanacademic.com/products/joshua-judges-ruth-1-and-2-samuel>

## Retrieval changes

Expanded draft books contain much more vocabulary than the legacy records.
The deterministic retrieval service now applies a soft penalty to broad draft
results when a query does not name that book, while retaining direct book and
passage retrieval. It also:

- prefers focused archaeology records when a query explicitly asks about an
  inscription, artifact, excavation, ostracon, or stele; and
- uses passage scope as a tie-breaker so a focused event can precede a broad
  book record for the same chapter.

These changes preserve the existing golden-query sequence, keep the Balaam
inscription ahead of the broad Numbers draft for a Deir Alla question, and
place the Shechem covenant event ahead of the Joshua book for the
Abraham/Joshua 24 query.

## Human review checklist

For Deuteronomy, verify:

- the six-part structure and all speech boundaries;
- the distinction between narrated setting and compositional proposals;
- the Horeb/Moab covenant wording and treaty-comparison cautions;
- descriptions of the Shema, worship centralization, leadership, social
  ethics, blessing and curse, public Torah, song, and succession;
- Hebrew terms and their translations;
- Jewish and Christian reception statements; and
- every source locator and relationship label.

For Joshua, verify:

- the seven-part structure and every person, place, event, and allotment
  summary;
- the relationship between campaign summaries, remaining land, and incomplete
  possession;
- each archaeological statement about Jericho, Ai, Hazor, Mount Ebal, and
  highland settlement;
- the presentation of warfare, divine judgment, mercy, Rahab, and oath
  keeping;
- the distinction between narrated events and compositional or historical
  reconstructions;
- the warnings against modern political proof-texting; and
- every source locator and relationship label.

For both records, verify every certainty/dispute label, distinguish textual
observation from historical reconstruction and later reception, and advance
only the sections actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/deuteronomy.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/joshua.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 211 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,074 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave3-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave3-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The focused regression file contains eight tests covering factual separation,
governance, current claims and notes, source depth, retrieval precision,
archaeological uncertainty, and complete JSON/SQLite payload parity. The known
Python 3.14 unclosed-SQLite `ResourceWarning` messages remain non-fatal
test-harness debt.

## What remains

1. Obtain human review for all six corrected records: Genesis, Exodus,
   Leviticus, Numbers, Deuteronomy, and Joshua.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 60 books in small source-backed
   waves.
4. The recommended next wave is Judges and Ruth, keeping the historical-book
   sequence while contrasting cyclical national disorder with a compact
   localized narrative.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
