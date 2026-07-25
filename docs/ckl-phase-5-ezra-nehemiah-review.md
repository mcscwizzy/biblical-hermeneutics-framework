# Phase 5 Wave 8 Review: Ezra and Nehemiah

Last updated: 2026-07-24

## Review status

The Ezra and Nehemiah correction wave is implemented and machine-verified.
Both records remain `draft` / `in_review`, require human review, and have
`section_status.human_review` set to `missing`. Automated validation does not
constitute approval.

Files for review:

- [`ezra.json`](../framework/canonical_library/objects/books/ezra.json)
- [`nehemiah.json`](../framework/canonical_library/objects/books/nehemiah.json)
- [`test_ezra_nehemiah_records.py`](../tests/canonical_library/test_ezra_nehemiah_records.py)

## Corrections made

### Ezra

- Removed the inherited Joshua, David, Solomon, Canaan, conquest, monarchy,
  and generic settlement-through-exile template.
- Separated the Cyrus-to-Darius return and temple sequence in chapters 1–6
  from Ezra's later Artaxerxes-era return and Torah mission in chapters 7–10.
- Restored Cyrus, Sheshbazzar, Zerubbabel, Jeshua, Haggai, Zechariah, Darius,
  Ahasuerus, Artaxerxes, Tattenai, Ezra, and their appropriate narrative roles.
- Marked Ezra 4's topical movement across Persian reigns so it is not read as
  a simple chronological sequence.
- Identified the Hebrew frame and Aramaic sections while qualifying the
  archival and literary history of the embedded letters and decrees.
- Treated the Cyrus Cylinder as comparative evidence for Babylonian
  restoration rhetoric rather than a copy or direct proof of Ezra's decree.
- Qualified the return totals, rejected temple collaborators, Persian
  chronology, Sheshbazzar/Zerubbabel questions, Ezra-Nehemiah order, and the
  Chronicles relationship.
- Addressed the marriage-dissolution account, the absent voices of wives and
  children, `holy seed` language, wider canonical evidence, and the danger of
  racial, nationalist, coercive, or universalized application.
- Added seven sourced claims, nine current-taxonomy interpretive notes, eight
  source records, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

### Nehemiah

- Removed the inherited Joshua, David, Solomon, Canaan, conquest, monarchy,
  and generic exile template.
- Rebuilt the record around Susa, Artaxerxes, the night inspection, wall work,
  regional opposition, armed defense, the chapter 5 debt crisis, wall
  completion, the returnee register, Torah assembly, confession, covenant,
  repopulation, dedication, and the later chapter 13 reforms.
- Restored Nehemiah, Hanani, Artaxerxes, Sanballat, Tobiah, Geshem, Shemaiah,
  Noadiah, Ezra, the Levites, builders, nobles, and officials to their
  appropriate roles.
- Distinguished the first administration, return to the royal court, and
  second Jerusalem visit without inventing a date for the interval.
- Treated the first-person memoir as important evidence within a final work
  that also contains third-person narration, lists, prayers, Ezra material,
  covenant text, and editorial transitions.
- Qualified the archaeology and route of the wall, the Persian regional
  setting of opponents, the fifty-two-day claim, the meaning of Nehemiah 8:8,
  and the chronology of Ezra and the dedication.
- Kept economic justice central: debt, taxes, land loss, enslavement,
  restitution, and accountable use of the governor's allowance are not
  incidental to the building narrative.
- Addressed armed defense, Ammonite and Moabite exclusion, canonical
  comparison with Ruth and Isaiah 56, Sabbath enforcement, cursing, beating,
  hair-pulling, expulsion, and the danger of treating these actions as direct
  modern leadership methods.
- Added eight sourced claims, ten current-taxonomy interpretive notes, seven
  source records, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Record | Claim ID | Certainty | Dispute status |
| --- | --- | --- | --- |
| Ezra | `ezra-cyrus-return` | `textually_explicit` | `historical_uncertainty` |
| Ezra | `ezra-altar-temple` | `textually_explicit` | `not_disputed` |
| Ezra | `ezra-opposition-darius` | `textually_explicit` | `historical_uncertainty` |
| Ezra | `ezra-temple-passover` | `textually_explicit` | `not_disputed` |
| Ezra | `ezra-torah-vocation` | `textually_explicit` | `not_disputed` |
| Ezra | `ezra-ahava-journey` | `textually_explicit` | `not_disputed` |
| Ezra | `ezra-confession-reform` | `textually_explicit` | `major_scholarly_disagreement` |
| Nehemiah | `nehemiah-prayer-authorization` | `textually_explicit` | `not_disputed` |
| Nehemiah | `nehemiah-wall-opposition` | `textually_explicit` | `historical_uncertainty` |
| Nehemiah | `nehemiah-economic-justice` | `textually_explicit` | `minor_scholarly_disagreement` |
| Nehemiah | `nehemiah-wall-completed` | `textually_explicit` | `historical_uncertainty` |
| Nehemiah | `nehemiah-torah-understanding` | `textually_explicit` | `lexical_uncertainty` |
| Nehemiah | `nehemiah-covenant-commitments` | `textually_explicit` | `minor_scholarly_disagreement` |
| Nehemiah | `nehemiah-dedication-support` | `textually_explicit` | `chronological_uncertainty` |
| Nehemiah | `nehemiah-later-reforms` | `textually_explicit` | `major_scholarly_disagreement` |

Every claim has a rationale and source IDs that resolve within its record. The
full wording, Scripture references, and source mappings are in the JSON files.

## Sources used

Primary text anchors are Ezra 1–10 and Nehemiah 1–13. Independent sources
added or reused in this wave:

- H. G. M. Williamson, *Ezra-Nehemiah, Volume 16* (Word Biblical
  Commentary; Zondervan Academic, 1985):
  <https://zondervanacademic.com/products/ezra-nehemiah-volume-16>
- F. Charles Fensham, *The Books of Ezra and Nehemiah* (NICOT; Eerdmans,
  1983):
  <https://www.eerdmans.com/9780802882288/the-books-of-ezra-and-nehemiah/>
- Jacob M. Myers, *Ezra, Nehemiah* (Anchor Yale Bible; Yale University
  Press, 1995):
  <https://yalebooks.yale.edu/book/9780300139556/ezra-nehemiah/>
- David J. Shepherd and Christopher J. H. Wright, *Ezra and Nehemiah* (Two
  Horizons Old Testament Commentary; Eerdmans, 2018):
  <https://www.eerdmans.com/9781467449625/ezra-and-nehemiah/>
- Lester L. Grabbe, *Eerdmans Commentary on the Bible: Ezra and Nehemiah*
  (Eerdmans, 2019):
  <https://www.eerdmans.com/9781467453608/eerdmans-commentary-on-the-bible-ezra-and-nehemiah/>
- The British Museum, *The Cyrus Cylinder*, collection object
  `1880,0617.1941`:
  <https://www.britishmuseum.org/collection/object/W_1880-0617-1941>
- John H. Walton, general editor, *Zondervan Illustrated Bible Backgrounds
  Commentary: 1 and 2 Kings, 1 and 2 Chronicles, Ezra, Nehemiah, Esther*
  (Zondervan, 2009):
  <https://zondervanacademic.com/products/1-and-2-kings-1-and-2-chronicles-ezra-nehemiah-esther>

Publisher and museum pages establish bibliographic identity, scope, and the
Cyrus Cylinder's actual contents. The records use the full works for
literary, historical, textual, archaeological, theological, and reception
judgments; publisher summaries do not substitute for human review.

## Retrieval coverage

The new tests require first-place book results for:

- why Ezra 4 moves between Persian kings;
- why part of Ezra is written in Aramaic;
- why Ezra's assembly sent away foreign wives and children;
- the economic injustice in Nehemiah 5;
- the interpretive question in Nehemiah 8:8; and
- Nehemiah's hair-pulling in chapter 13.

All pass with the existing retrieval implementation. No ranking-code change
was needed in this wave.

## Human review checklist

For Ezra, verify:

- the nine-part outline and all chapter boundaries;
- Cyrus, Sheshbazzar, Zerubbabel, Jeshua, Haggai, Zechariah, Darius,
  Ahasuerus, Artaxerxes, Tattenai, Ezra, and every named official or group;
- the relationship between Sheshbazzar and Zerubbabel without asserting an
  unsupported identification;
- temple vessels, return lists and totals, priestly genealogy, altar,
  foundation, mixed emotional response, opposition, resumption, completion,
  dedication, and Passover;
- Ezra 4's topical chronology and every Persian reign;
- all Hebrew and Aramaic section boundaries and claims about documentary
  form;
- the Cyrus Cylinder comparison and the distinction between comparative
  imperial policy and direct verification;
- the conventional 458/457 BCE dating and alternative Ezra-Nehemiah
  chronologies;
- Ezra's genealogy, Torah vocation, commission, Ahava fast, stewardship,
  journey, and arrival;
- the wording and ethical treatment of Ezra 9–10, including women, children,
  ancestry, practice, holiness, divorce, coercion, and canonical comparison;
- every source locator, relationship, certainty, and dispute label.

For Nehemiah, verify:

- the eleven-part outline and the relation among chapters 1–6, 7–12, and 13;
- Artaxerxes, Nehemiah, Hanani, Hananiah, Eliashib, Sanballat, Tobiah, Geshem,
  Shemaiah, Noadiah, Ezra, Levites, nobles, and officials;
- regnal-year conversion, first governorship, court return, and unspecified
  second-visit interval;
- Susa, Jerusalem, Yehud, the province Beyond the River, neighboring regions,
  all gates, work sections, inspection route, and dedication processions;
- the historical and archaeological qualifications around the wall circuit,
  extent, construction organization, threat, and fifty-two days;
- the full economic setting and restitution obligations in chapter 5;
- the memoir/editorial distinctions and every shift of voice or literary
  form;
- the returnee list's relationship to Ezra 2;
- Torah reading, explanation, grief, joy, Booths, confession, historical
  prayer, covenant signatories, and enumerated commitments;
- population, priests, Levites, singers, gatekeepers, wall dedication, and
  temple support;
- Tobiah's chamber, Sabbath markets, mixed marriages, language, exclusion,
  cursing, physical force, expulsion, and remembrance prayers in chapter 13;
- the canonical comparison with Deuteronomy 23, Ruth, Isaiah 56, and Malachi;
- every source locator, relationship, certainty, and dispute label.

For both records, distinguish the biblical text's claims from modern
historical reconstruction, do not mechanically harmonize lists or chronology,
and advance only the sections actually reviewed.

## Verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/ezra.json
# 1 valid object, 0 warnings, 0 errors

python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/nehemiah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest tests/canonical_library/test_*.py
# 251 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,131 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave8-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave8-ckl.sqlite
# 620 objects; database schema 2; fingerprint
# 3ce0b541475a91e7fd1e20fbf2ea538b1db0c447199d5688cdcb77db3bd329af
```

The focused regression file contains eight tests covering factual separation,
governance, evidence taxonomy, source depth, retrieval precision, difficult
interpretive qualifications, and complete JSON/SQLite payload parity. The
known Python 3.14 unclosed-SQLite `ResourceWarning` messages remain non-fatal
test-harness debt.

## What remains

1. Obtain human review for all sixteen corrected records from Genesis through
   Nehemiah.
2. Apply reviewer corrections and record reviewer/date provenance.
3. Continue Phase 5 through the remaining 50 books in small source-backed
   waves.
4. The recommended next wave is Esther. Give special attention to Ahasuerus
   and Persian court setting, Vashti, Esther, Mordecai, Haman, Jewish identity
   in diaspora, the absence of an explicit divine name, fasting, providence,
   irrevocable edicts, threatened genocide, reversal, retaliatory violence,
   Purim, historicity and archaeology, Hebrew and Greek forms, gender and
   power, antisemitic reception, and modern ethnic or political application.
5. Regenerate both quality reports and update the durable progress checkpoint
   after every wave.
