# Phase 5 Wave 6 Review: 1 Kings and 2 Kings

Last updated: 2026-07-24

## Review status

The 1 Kings and 2 Kings correction wave is implemented and machine-verified.
Both records remain `draft` / `in_review`, require human review, and have
`section_status.human_review` set to `missing`. Automated validation does not
constitute approval.

Files for review:

- [`1-kings.json`](../framework/canonical_library/objects/books/1-kings.json)
- [`2-kings.json`](../framework/canonical_library/objects/books/2-kings.json)
- [`test_kings_records.py`](../tests/canonical_library/test_kings_records.py)

## Corrections made

### 1 Kings

- Removed inherited Joshua, Canaan, conquest, and exile-wide material from the
  book's own principal people, places, events, and narrated setting.
- Rebuilt the structure around Solomon's succession, wisdom, administration,
  temple and palace, dedication prayer, covenant failure, the kingdom's
  division, parallel regnal history, and the Elijah–Ahab conflict.
- Added Bathsheba, Nathan, Adonijah, Zadok, Abiathar, Joab, Benaiah, Hiram,
  the queen of Sheba, Rehoboam, Jeroboam, Ahijah, Omri, Jezebel, Elijah,
  Naboth, Micaiah, and other figures required by the narrative.
- Held Solomon's wisdom and temple achievement together with accumulation,
  forced labor, divided loyalty, and judgment.
- Coordinated divine judgment on Solomon with Rehoboam's and Jeroboam's
  accountable political choices rather than reducing the division to one
  cause.
- Qualified Solomonic chronology and archaeology, temple comparisons, the
  difficult Horeb phrase, Carmel's violence, and the Kurkh Monolith's limited
  but relevant historical evidence.
- Added six sourced claims, six structured interpretive notes, five source
  records, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### 2 Kings

- Removed Joshua, David, Solomon, and Jeremiah from the principal cast.
  Jeremiah remains an important canonical parallel but is not named as a
  character in Second Kings.
- Rebuilt the structure around Elijah's departure, Elisha's ministry, the
  Moab and Aramean conflicts, Jehu's coup, Assyrian expansion, Samaria's fall,
  Hezekiah and Sennacherib, Manasseh, Josiah, Babylon's destruction of
  Jerusalem, Gedaliah, and Jehoiachin's release.
- Restored the parallel regnal sequence, prophetic succession, foreign rulers,
  women, priests, officials, imperial agents, deportations, and resettlement
  policies belonging to the book.
- Distinguished theological explanations for both kingdoms' falls from the
  ordinary imperial mechanisms the narrative also reports.
- Preserved the mixed evaluation of Jehu, the limits of Josiah's reform, and
  the restrained rather than completed hope of the Jehoiachin ending.
- Qualified the Bethel-bears vocabulary and ethics, the ambiguous ending of
  the Moab campaign, Jehu and Hosea, the Sennacherib comparison, and
  differences between Kings and Chronicles concerning Josiah.
- Added eight sourced claims, seven structured interpretive notes, six source
  records, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| 1 Kings | `first-kings-literary-movement` | `strong_consensus` | `not_disputed` |
| 1 Kings | `first-kings-solomon-discernment` | `textually_explicit` | `not_disputed` |
| 1 Kings | `first-kings-temple-prayer-warning` | `strong_consensus` | `minor_scholarly_disagreement` |
| 1 Kings | `first-kings-kingdom-division` | `textually_explicit` | `not_disputed` |
| 1 Kings | `first-kings-carmel-confession` | `textually_explicit` | `not_disputed` |
| 1 Kings | `first-kings-naboth-condemnation` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-literary-movement` | `strong_consensus` | `not_disputed` |
| 2 Kings | `second-kings-elisha-succeeds` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-naaman-healed` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-samaria-falls` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-jerusalem-delivered` | `textually_explicit` | `historical_uncertainty` |
| 2 Kings | `second-kings-josiah-reform` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-jerusalem-falls` | `textually_explicit` | `not_disputed` |
| 2 Kings | `second-kings-jehoiachin-released` | `textually_explicit` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within its record. The
full wording, Scripture references, and source mappings are in the JSON files.

## Sources used

Primary text anchors are 1 Kings 1–22 and 2 Kings 1–25. Independent sources
added in this wave:

- Mordechai Cogan, *I Kings* (Yale University Press, 2001):
  <https://yalebooks.yale.edu/9780300140538/i-kings/>
- Gene Rice, *1 Kings: Nations under God* (Eerdmans, 1990):
  <https://www.eerdmans.com/9780802804921/1-kings/>
- Mordechai Cogan and Hayim Tadmor, *II Kings* (Yale University Press, 1988):
  <https://yalebooks.yale.edu/book/9780300140743/ii-kings/>
- David T. Lamb, *1–2 Kings* (Zondervan, 2021):
  <https://zondervanacademic.com/products/1-and-2-kings-1>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: 1 and 2 Kings, 1 and 2 Chronicles, Ezra, Nehemiah, Esther*
  (Zondervan, 2009):
  <https://zondervanacademic.com/products/1-and-2-kings-1-and-2-chronicles-ezra-nehemiah-esther>
- British Museum, Black Obelisk collection record:
  <https://www.britishmuseum.org/collection/object/W_1848-1104-1>
- British Museum, Taylor or Sennacherib Prism collection record:
  <https://www.britishmuseum.org/collection/object/W_1855-1003-1>
- British Museum, Kurkh Stela collection listing:
  <https://www.britishmuseum.org/collection/object/W_1863-0619-2>

Museum records are used as primary artifact documentation, not as proof of
the books' theological interpretations or every narrated event.

## Retrieval coverage

The new tests require first-place book results for:

- why the kingdom divided in 1 Kings;
- what happened on Mount Carmel in 1 Kings;
- why Samaria fell in 2 Kings;
- how 2 Kings ends; and
- what the Sennacherib Prism says about Hezekiah in relation to 2 Kings.

All pass with the existing named-book ranking correction. No additional
retrieval algorithm change was needed in this wave.

## Human review checklist

For 1 Kings, verify:

- the seven-part structure and exact transition from David to Ahaziah;
- every ruler, prophet, official, woman, location, battle, and regnal event;
- succession details involving Adonijah, Bathsheba, Nathan, Zadok, Abiathar,
  Joab, Benaiah, and Solomon;
- Solomon's administration, labor, building chronology, trade, wealth, wives,
  adversaries, and covenant evaluation;
- temple architecture, divine-name theology, foreign prayer, and warning;
- Rehoboam, Jeroboam, the two shrines, and the causes of division;
- the anonymous prophetic narratives in chapters 13 and 20;
- Elijah, Obadiah, the Zarephath household, Carmel, Horeb, and Elisha's call;
- Naboth, land inheritance, Jezebel's conspiracy, Ahab's responsibility, and
  Micaiah's council vision;
- regnal chronology, Omride archaeology, and the Kurkh correlation; and
- every source locator and relationship label.

For 2 Kings, verify:

- the eight-part structure and the exact boundaries between Elisha material,
  northern collapse, Hezekiah, Josiah, and Babylonian destruction;
- every king, prophet, foreign ruler, woman, priest, official, imperial agent,
  place, campaign, deportation, and event;
- the Bethel-bears note, its lexical classification, and ethical wording;
- the Moab campaign's ending and responsible use of the Mesha Stele;
- Naaman, the captive Israelite girl, Gehazi, and the Shunammite household;
- Hazael and Jehu, including commission, violence, mixed evaluation, and
  Hosea's later judgment;
- Samaria's fall, deportation, resettlement, and the chapter 17 explanation;
- Hezekiah, Isaiah, the Rabshakeh, Sennacherib's sources, and Lachish;
- Manasseh's responsibility and Josiah's scroll, Huldah, reform, and death;
- Babylonian chronology, destruction, deportations, Gedaliah, Egypt, and
  Jehoiachin's release; and
- every source locator and relationship label.

For both records, verify every certainty/dispute label, distinguish biblical
claims from external historical evidence, and advance only the sections
actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/1-kings.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py --path framework/canonical_library/objects/books/2-kings.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 235 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 pre-existing migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,099 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave6-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave6-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The focused regression file contains eight tests covering factual separation,
governance, evidence taxonomy, source depth, retrieval precision, difficult
interpretive qualifications, and complete JSON/SQLite payload parity. The
known Python 3.14 unclosed-SQLite `ResourceWarning` messages remain non-fatal
test-harness debt.

## What remains

1. Obtain human review for all twelve corrected records from Genesis through
   2 Kings.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 54 books in small source-backed
   waves.
4. The recommended next wave is 1 Chronicles and 2 Chronicles, preserving the
   historical-book sequence while auditing genealogies, David and Solomon,
   temple and Levites, Judah's kings, differences from Samuel–Kings, Persian
   setting, and the Cyrus ending.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
