# Phase 5 Wave 1 Review: Genesis and Exodus

Last updated: 2026-07-24

## Review status

The Genesis and Exodus correction wave is implemented and machine-verified.
Both records remain `draft` / `in_review`, require human review, and have
`section_status.human_review` set to `missing`. Nothing in this wave is marked
approved or complete.

Files for review:

- [`genesis.json`](../framework/canonical_library/objects/books/genesis.json)
- [`exodus.json`](../framework/canonical_library/objects/books/exodus.json)
- [`test_genesis_exodus_records.py`](../tests/canonical_library/test_genesis_exodus_records.py)

## Corrections made

### Genesis

- Replaced the inherited Exodus/wilderness people, places, and events with
  Genesis-specific data spanning Genesis 1–50.
- Distinguished the narrated world from disputed composition/history
  questions.
- Added a book-specific structure, canonical movement, themes, Hebrew terms,
  intertextual links, and retrieval questions.
- Added four granular, sourced claims and four structured interpretive notes
  using the current certainty and dispute taxonomies.
- Added explicit section statuses and knowledge-layer classification.
- Replaced internal-only sourcing with Scripture plus independently published
  Jewish, literary, and ancient Near Eastern background resources.

### Exodus

- Removed Moab and duplicated generic event labels from the book overview.
- Added book-specific people, locations, and events from oppression in Egypt
  through the glory filling the tabernacle.
- Distinguished the narrated setting from unresolved date, route, pharaoh,
  population, and composition questions.
- Added a book-specific structure, canonical movement, themes, Hebrew terms,
  intertextual links, and retrieval questions.
- Added five granular, sourced claims and four structured interpretive notes
  using the current certainty and dispute taxonomies.
- Added explicit section statuses and knowledge-layer classification.
- Added a deliberately limited archaeological claim: the Merneptah Stele is
  relevant to early Israel but does not establish the exodus's pharaoh, route,
  date, or narrative details.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| Genesis | `genesis-literary-movement` | `strong_consensus` | `not_disputed` |
| Genesis | `genesis-blessing-for-families` | `textually_explicit` | `not_disputed` |
| Genesis | `genesis-ane-comparative-context` | `strong_consensus` | `minor_scholarly_disagreement` |
| Genesis | `genesis-ends-in-egypt` | `textually_explicit` | `not_disputed` |
| Exodus | `exodus-literary-movement` | `strong_consensus` | `not_disputed` |
| Exodus | `exodus-priestly-kingdom` | `textually_explicit` | `not_disputed` |
| Exodus | `exodus-tabernacle-presence` | `textually_explicit` | `not_disputed` |
| Exodus | `exodus-ane-context` | `probable` | `minor_scholarly_disagreement` |
| Exodus | `exodus-merneptah-limits` | `probable` | `archaeological_uncertainty` |

Every claim has a rationale and local source IDs that resolve against the
record's source list. The full claim wording, Scripture references, and source
mapping are in the JSON files.

## Sources used

Primary text anchors are Genesis 1–50 and Exodus 1–40. Independent supporting
sources added in this wave:

- Nahum M. Sarna, *The JPS Torah Commentary: Genesis* (Jewish Publication
  Society, 1989):
  <https://jps.org/books/jps-torah-commentary-genesis/>
- Nahum M. Sarna, *The JPS Torah Commentary: Exodus* (Jewish Publication
  Society, 1991):
  <https://jps.org/books/jps-torah-commentary-exodus/>
- Victor P. Hamilton, *The Book of Genesis, Chapters 1–17* (Eerdmans, 1990):
  <https://www.eerdmans.com/9780802825216/the-book-of-genesis-chapters-1-17/>
- Victor P. Hamilton, *The Book of Genesis, Chapters 18–50* (Eerdmans, 1995):
  <https://www.eerdmans.com/9780802823090/the-book-of-genesis-chapters-18-50/>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: Genesis, Exodus, Leviticus, Numbers, Deuteronomy* (Zondervan,
  2009):
  <https://zondervanacademic.com/products/genesis-exodus-leviticus-numbers-deuteronomy>
- Museum of the Bible, “The Merneptah Stele” (2020):
  <https://www.museumofthebible.org/book-minute/the-merneptah-stele>

## Human review checklist

The reviewer should verify:

- all people, place, event, structure, and Scripture lists against each book;
- the wording and scope of every authorship, composition, chronology, route,
  and archaeology statement;
- the distinction between textual observation, historical reconstruction,
  ancient Near Eastern comparison, biblical theology, reception, and
  application;
- the certainty and dispute label on each claim and interpretive note;
- bibliographic dates, contributors, locators, and whether additional
  peer-reviewed or reference sources are needed;
- all graph edges and their relationship labels;
- retrieval questions and aliases for precision and usefulness; and
- whether each `needs_review` section can become `reviewed` or `complete`.

Topics intentionally left unresolved pending review include Genesis
composition and the genre/historicity debates around Genesis 1–11, plus the
date, route, pharaoh, population scale, and archaeological reconstruction of
the exodus.

## Verification

The wave currently passes:

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/genesis.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/exodus.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,040 edges, 0 unknown targets, 0 orphaned objects
```

The focused regression file contains eight tests covering factual separation,
honest governance, evidence taxonomy, retrieval precision, and full JSON /
SQLite payload parity.

```text
python3 -m unittest tests/canonical_library/test_*.py
# 195 tests: OK

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

## What remains

1. Obtain human review for Genesis and Exodus and record the reviewer/date.
2. Apply any reviewer corrections and advance only the sections actually
   reviewed.
3. Continue Phase 5 through the remaining books in small, source-backed waves.
4. The Leviticus/Numbers wave is now implemented and documented in
   [`ckl-phase-5-leviticus-numbers-review.md`](ckl-phase-5-leviticus-numbers-review.md).
   The recommended next content wave is Deuteronomy and Joshua.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
