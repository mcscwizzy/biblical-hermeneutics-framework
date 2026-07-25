# Phase 5 Wave 2 Review: Leviticus and Numbers

Last updated: 2026-07-24

## Review status

The Leviticus and Numbers correction wave is implemented and
machine-verified. Both records remain `draft` / `in_review`, require human
review, and have `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`leviticus.json`](../framework/canonical_library/objects/books/leviticus.json)
- [`numbers.json`](../framework/canonical_library/objects/books/numbers.json)
- [`test_leviticus_numbers_records.py`](../tests/canonical_library/test_leviticus_numbers_records.py)

## Corrections made

### Leviticus

- Removed Egypt, Moab, the exodus, and the wilderness journey from the list of
  the book's own principal places and events.
- Anchored the narrated setting at the Sinai tent of meeting between Exodus 40
  and Numbers 1 and 10.
- Added a book-specific structure covering offerings, priestly inauguration,
  purity, the Day of Atonement, holy communal life, festivals, Sabbath years,
  Jubilee, covenant consequences, and vows.
- Distinguished ritual impurity, moral offense, holiness, sacrifice, and
  atonement instead of collapsing them into one category.
- Added current interpretive taxonomy, five sourced claims, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### Numbers

- Replaced the generic Egypt/Sinai/Moab template with the actual journey from
  Sinai through Kadesh and Transjordan to the plains of Moab.
- Added the main leaders, challengers, foreign figures, locations, censuses,
  rebellions, judgments, blessings, transitions, and inheritance cases.
- Organized the record around geographic movement and the transition between
  the first counted generation and the generation prepared for the land.
- Explicitly marked census totals, route identifications, population scale,
  composition, warfare ethics, and archaeological reconstruction as disputed
  or uncertain where appropriate.
- Limited the Deir Alla claim to evidence for a later Balaam son of Beor
  tradition; the inscription is not represented as verification of Numbers
  22–24.
- Added current interpretive taxonomy, six sourced claims, independent
  sources, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| Leviticus | `leviticus-literary-movement` | `strong_consensus` | `not_disputed` |
| Leviticus | `leviticus-called-from-tent` | `textually_explicit` | `not_disputed` |
| Leviticus | `leviticus-day-of-atonement` | `textually_explicit` | `not_disputed` |
| Leviticus | `leviticus-holy-community` | `textually_explicit` | `not_disputed` |
| Leviticus | `leviticus-purity-distinctions` | `strong_consensus` | `minor_scholarly_disagreement` |
| Numbers | `numbers-literary-journey` | `strong_consensus` | `not_disputed` |
| Numbers | `numbers-two-generations` | `textually_explicit` | `not_disputed` |
| Numbers | `numbers-kadesh-judgment` | `textually_explicit` | `not_disputed` |
| Numbers | `numbers-balaam-blessing` | `textually_explicit` | `not_disputed` |
| Numbers | `numbers-inheritance-preparation` | `strong_consensus` | `not_disputed` |
| Numbers | `numbers-deir-alla-limits` | `probable` | `archaeological_uncertainty` |

Every claim has a rationale and source IDs that resolve within its record. The
full claim wording, Scripture references, and source mappings are in the JSON
files.

## Sources used

Primary text anchors are Leviticus 1–27 and Numbers 1–36. Independent sources
added or reused in this wave:

- Baruch A. Levine, *The JPS Torah Commentary: Leviticus* (Jewish Publication
  Society, 1989):
  <https://jps.org/books/jps-torah-commentary-leviticus/>
- Jacob Milgrom, *The JPS Torah Commentary: Numbers* (Jewish Publication
  Society, 1990):
  <https://jps.org/books/jps-torah-commentary-numbers/>
- Gordon J. Wenham, *The Book of Leviticus* (Eerdmans, 1979):
  <https://www.eerdmans.com/9780802825223/the-book-of-leviticus/>
- Timothy R. Ashley, *The Book of Numbers*, second edition (Eerdmans, 2022):
  <https://www.eerdmans.com/9780802872029/the-book-of-numbers/>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Genesis, Exodus, Leviticus, Numbers, Deuteronomy* (Zondervan,
  2009):
  <https://zondervanacademic.com/products/genesis-exodus-leviticus-numbers-deuteronomy>
- Biblical Archaeology Society, “Deir Alla Inscription”:
  <https://library.biblicalarchaeology.org/sidebar/deir-alla-inscription/>

## Human review checklist

For Leviticus, verify:

- the structure and terminology of the offerings;
- the wording of claims about ritual and moral impurity;
- translations and descriptions of Hebrew ritual terms;
- Day of Atonement, holiness, land, Sabbath-year, and Jubilee summaries;
- Jewish and Christian reception statements; and
- the source locators and relationship labels.

For Numbers, verify:

- the five-part geographic structure and all journey locations;
- the relationship between the two censuses and two generations;
- every person, event, and inheritance summary;
- the presentation of difficult judgment and warfare passages;
- the census, route, chronology, and population cautions;
- the Deir Alla claim and source quality; and
- the source locators and relationship labels.

For both records, verify every certainty/dispute label, distinguish textual
observation from historical reconstruction and later reception, and advance
only the sections actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/leviticus.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/numbers.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 203 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,060 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave2-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave2-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The focused regression file contains eight tests covering factual separation,
governance, evidence taxonomy, source depth, retrieval precision, and complete
JSON/SQLite payload parity. The known Python 3.14 unclosed-SQLite
`ResourceWarning` messages remain non-fatal test-harness debt.

## What remains

1. Obtain human review for all four corrected Pentateuch records: Genesis,
   Exodus, Leviticus, and Numbers.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 62 books in small source-backed
   waves.
4. The recommended next wave is Deuteronomy and Joshua, which bridges the end
   of Torah and entry into the land.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
