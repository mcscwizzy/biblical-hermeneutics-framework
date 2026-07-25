# Phase 5 Wave 24 Review: Micah

Last updated: 2026-07-25

## Review status

The Micah correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`micah.json`](../framework/canonical_library/objects/books/micah.json)
- [`test_micah_record.py`](../tests/canonical_library/test_micah_record.py)

## Corrections made

- Removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, Jonah, and Nineveh values, generic corpus dates and setting,
  legacy evidence labels, internal-only sourcing, and the false `complete`
  status and review date.
- Rebuilt the record around Micah 1; 2; 3; 4–5; 6; and 7, while preserving
  three-cycle, judgment-and-salvation, final-form, and redactional approaches
  to the book's alternating doom and hope.
- Distinguished Micah of Moresheth, YHWH, the prophetic and framing voices,
  Samaria, Jerusalem, Jacob, Israel, Judah, daughter Zion, the remnant,
  dispossessors and dispossessed households, rulers, prophets, priests,
  judges, seers, diviners, the Bethlehem ruler, the woman in labor, shepherds,
  creation as witness, Assyria, Babylon, nations, enemies, and later readers.
- Distinguished superscription, theophany, judgment oracle, lament,
  place-name dirge, woe, accusation, disputed speech, remnant and salvation
  oracle, nations-pilgrimage and Zion oracle, ruler and birth oracle, shepherd
  and war oracle, disputation or lawsuit, instruction, wisdom, confession,
  enemy taunt, prayer, hymn, and doxology.
- Qualified Moresheth and the Shephelah, Jotham, Ahaz, Hezekiah, Samaria's
  fall in 722/721 BCE, Sennacherib's 701 BCE campaign, Lachish, tribute,
  warfare, landholding, debt, courts, patronage, rural and urban settings,
  eighth-century prophetic memory, later additions, final form, and the
  Twelve.
- Added bounded archaeological use of the Sennacherib Prism and Lachish
  reliefs while identifying Assyrian royal ideology and refusing to turn
  artifacts into proof of every oracle, place route, or literary layer.
- Addressed land and inheritance, household dispossession, violence, paid
  prophecy, corrupt institutions, Zion and temple confidence, peace and
  disarmament, remnant, daughter Zion, Babylon, Bethlehem, Davidic hope,
  shepherding, Assyria, military and cult objects, covenant memory,
  sacrifice, firstborn rhetoric, *mishpat*, *hesed*, humble walking,
  forgiveness, Jacob, and Abraham.
- Preserved uncertainty concerning authorship and composition, Moresheth,
  Micah 1 wordplays and route, speakers in 2:6–11, the breaker in 2:12–13,
  3:5's feeding imagery, Jeremiah 26's use of 3:12, Micah 4 / Isaiah 2
  priority, Babylon, Hebrew/common-English numbering, the ruler's origins,
  the woman in labor, seven shepherds and eight leaders, Assyria, remnant
  imagery, purification, Micah 6's genre, Shittim and Gilgal, Micah 6:8
  syntax, Omri and Ahab, Micah 7's speakers, and the name wordplay in 7:18.
- Added Masoretic Micah, Old Greek Michaias, CATSS, NETS, 4Q81, 4Q82, MurXII,
  Greek 8HevXII, Isaiah, Jeremiah, Kings, Chronicles, Torah, Psalms, the
  Twelve, Matthew, Luke, John, early Jewish, early Christian, living Jewish,
  artistic, political, liberationist, postcolonial, gender-critical,
  ecological, and trauma-aware contexts.
- Distinguished historical referent, prophetic memory, compiler or tradent,
  quotation, parallel, disputed borrowing, shared tradition, canonical
  trajectory, Jewish messianic reception, Christian christological reception,
  social-justice use, and modern analogy.
- Added safeguards concerning antisemitism, anti-ritual readings,
  supersessionism, Judaism-as-legalism, partisan capture, poverty
  romanticization, victim blame, class contempt, land and housing
  exploitation, coercive charity, clergy and public-leader abuse, child
  sacrifice, coerced worship, weaponized humility or forgiveness, domestic
  violence, gender and childbirth stereotypes, disability stigma, racism,
  nationalism, automatic Zionist or anti-Zionist mappings, colonialism,
  empire, war, genocide, displacement, disaster blame, and survivor safety.
- Added thirty-four sourced claims, fifty-two current-taxonomy interpretive
  notes, twenty-six source records, twenty-three URL-bearing external sources,
  eight graph relationships, eighteen Scripture anchors, twenty Hebrew
  entries, eight Greek entries, explicit section statuses and knowledge
  layers, a populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `micah-superscription` | `textually_explicit` | `historical_uncertainty` |
| `micah-composition` | `probable` | `major_scholarly_disagreement` |
| `micah-structure` | `strong_consensus` | `minor_scholarly_disagreement` |
| `micah-three-cycle` | `probable` | `minor_scholarly_disagreement` |
| `micah-assyrian-horizon` | `strong_consensus` | `chronological_uncertainty` |
| `micah-sennacherib-material` | `strong_consensus` | `not_disputed` |
| `micah-place-dirge` | `strong_consensus` | `lexical_uncertainty` |
| `micah-land-seizure` | `textually_explicit` | `historical_uncertainty` |
| `micah-two-speakers` | `strong_consensus` | `major_scholarly_disagreement` |
| `micah-breaker` | `plausible` | `major_scholarly_disagreement` |
| `micah-leadership` | `textually_explicit` | `not_disputed` |
| `micah-jeremiah-reception` | `textually_explicit` | `historical_uncertainty` |
| `micah-isaiah-parallel` | `textually_explicit` | `major_scholarly_disagreement` |
| `micah-peace-vision` | `textually_explicit` | `minor_scholarly_disagreement` |
| `micah-babylon` | `textually_explicit` | `major_scholarly_disagreement` |
| `micah-numbering` | `textually_explicit` | `not_disputed` |
| `micah-bethlehem-ruler` | `textually_explicit` | `major_scholarly_disagreement` |
| `micah-assyria` | `textually_explicit` | `chronological_uncertainty` |
| `micah-purification` | `textually_explicit` | `major_scholarly_disagreement` |
| `micah-six-genre` | `textually_explicit` | `major_scholarly_disagreement` |
| `micah-six-eight` | `textually_explicit` | `lexical_uncertainty` |
| `micah-firstborn-rhetoric` | `textually_explicit` | `minor_scholarly_disagreement` |
| `micah-omri-ahab` | `textually_explicit` | `historical_uncertainty` |
| `micah-seven-voices` | `strong_consensus` | `major_scholarly_disagreement` |
| `micah-mercy-conclusion` | `textually_explicit` | `minor_scholarly_disagreement` |
| `micah-textual-witnesses` | `strong_consensus` | `textual_variant` |
| `micah-twelve-placement` | `strong_consensus` | `major_scholarly_disagreement` |
| `micah-jewish-reception` | `strong_consensus` | `minor_scholarly_disagreement` |
| `micah-new-testament-reception` | `textually_explicit` | `denominational_disagreement` |
| `micah-social-location` | `probable` | `historical_uncertainty` |
| `micah-gendered-images` | `strong_consensus` | `minor_scholarly_disagreement` |
| `micah-empire-reception` | `plausible` | `minor_scholarly_disagreement` |
| `micah-later-reception` | `strong_consensus` | `minor_scholarly_disagreement` |
| `micah-genre` | `strong_consensus` | `minor_scholarly_disagreement` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and mappings are in
[`micah.json`](../framework/canonical_library/objects/books/micah.json).

## Sources used

Primary witnesses include Masoretic Micah, Hebrew Bible comparanda, Matthew,
Luke, John, Old Greek Michaias, 4Q81, 4Q82, MurXII, Greek 8HevXII, CATSS, NETS,
the Sennacherib Prism, and the Lachish reliefs. Independent research sources
include:

- Rainer Kessler, “Micah”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334373451>.
- Francis I. Andersen and David Noel Freedman, *Micah*:
  <https://drupal.yalebooks.yale.edu/sites/default/files/anchor_bible_2018_online_0.pdf>.
- Bruce K. Waltke, *A Commentary on Micah*:
  <https://www.eerdmans.com/9780802864123/a-commentary-on-micah/>.
- Daniel L. Smith-Christopher, *Micah: A Commentary*:
  <https://www.wjkbooks.com/bookproduct/0664229042-micah/>.
- Leslie C. Allen, *The Books of Joel, Obadiah, Jonah, and Micah*:
  <https://www.eerdmans.com/9780802883964/the-books-of-joel-obadiah-jonah-and-micah/>.
- Mark S. Gignilliat, *Micah*:
  <https://www.bloomsbury.com/ca/micah-itc-9780567716606/>.
- CATSS, “Text and Textual Variants for the Old Greek Book of Micah”:
  <https://ccat.sas.upenn.edu/gopher/text/religion/biblical/lxxvar/active/06Micah.html>.
- George E. Howard, *A New English Translation of the Septuagint: The Twelve
  Prophets*:
  <https://ccat.sas.upenn.edu/nets/edition/32-twelve-nets.pdf>.
- Israel Antiquities Authority records for
  [4Q81](https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q81-1?locale=en_US),
  [4Q82](https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q82-1),
  [MurXII](https://www.deadseascrolls.org.il/explore-the-archive/image/B-281189?locale=en_US),
  and
  [Greek 8HevXII](https://www.deadseascrolls.org.il/explore-the-archive/image/B-314652).
- British Museum records for the
  [Sennacherib Prism](https://www.britishmuseum.org/collection/object/W_1855-1003-1)
  and
  [Lachish relief](https://www.britishmuseum.org/collection/object/W_1856-0909-14_1).
- *New Form Criticism and the Book of the Twelve*:
  <https://www.sbl-site.org/assets/pdfs/pubs/9781628370614_OA.pdf>.
- Anna Sieges, “One Book or Twelve Books?”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334371290>.
- Malka Z. Simkovich, “The Minor Prophets in Early Judaism”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372283>.
- Michael B. Shepherd, “The Minor Prophets in Early Christianity”:
  <https://academic.oup.com/edited-volume/38566/chapter/334372365>.
- John F. A. Sawyer, “The Twelve Minor Prophets in Art and Music”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372557>.
- Susanne Scholz, “Reading the Minor Prophets for Gender and Sexuality”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372627>.
- Jeremiah W. Cataldo, “Postcolonial Approaches to the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372842>.
- Stephen Lewis Fuchs, “The Minor Prophets in Jewish Life Today”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372906>.

Publisher, university, archive, scholarly-organization, and museum pages
establish bibliographic identity, scope, material witness, or a bounded
research claim. They do not substitute for a qualified reviewer checking every
use, locator, translation, manuscript reading, artifact inference, or
scholarly position.

## Retrieval coverage

The tests require a first-place Micah result for:

- Micah of Moresheth, Jotham, Ahaz, Hezekiah, authorship, date, and formation;
- Moresheth, Gath, Lachish, Shephelah puns and route, Samaria's fall,
  Sennacherib's 701 campaign, the Prism, and Lachish reliefs;
- land seizure, houses, fields, women, children, inheritance, debt, courts,
  rulers, priests, judges, seers, diviners, and paid prophets;
- Micah 2 speakers, remnant, breaker, Micah 3:12, and Jeremiah 26:18;
- Micah 4 / Isaiah 2, swords and plowshares, vine and fig tree, Babylon, and
  Hebrew/common-English numbering;
- Bethlehem Ephrathah, the ruler's ancient origins, woman in labor, seven
  shepherds, eight leaders, Assyria, dew, lion, and purification;
- covenant lawsuit or disputation, Shittim, Gilgal, sacrifice, firstborn,
  *mishpat*, *hesed*, humility, Omri, and Ahab;
- Micah 7 speakers, lament, confession, enemy taunt, shepherd prayer, divine
  name wordplay, pardon, sins in the sea, Jacob, and Abraham;
- Old Greek Michaias, Judean Desert witnesses, Matthew, Luke, John, Jewish
  messianic, and Christian christological reception; and
- antisemitism, anti-ritual readings, supersessionism, partisan capture,
  weaponized humility and forgiveness, disability, childbirth, ecology,
  displacement, nationalism, colonialism, genocide, and trauma-aware reading.

All pass with the existing retrieval implementation. No ranking-code change
was needed; two exact aliases disambiguate the deliberately cross-book
Jeremiah 26 and Isaiah 2 questions.

## Human review checklist

Verify:

- the superscription, Micah/Moreshethite wording, every proposed voice,
  speaker, addressee, quotation boundary, first-person shift, and divine
  speech or action;
- all practical units, the three-cycle outline, alternative doom-hope and
  redactional divisions, refrains, seams, and prose or poetic framing;
- Micah of Moresheth, Moresheth-gath, every proposed site, town pun, route,
  Shephelah reconstruction, and inference about rural social location;
- Jotham, Ahaz, Hezekiah, Samaria 722/721, Sennacherib 701, Jerusalem,
  Lachish, tribute, campaign chronology, and later historical horizons;
- every claim about land tenure, inheritance, debt, seizure, housing, courts,
  patronage, elite building, women, children, rural households, and urban
  institutions;
- the Sennacherib Prism, Lachish reliefs, royal ideology, museum metadata,
  artifact dates, and every claimed relation between material evidence and
  Micah;
- speakers in 2:6–11, remnant and breaker in 2:12–13, the flesh and feeding
  metaphors in chapter 3, Zion and temple claims, and Jeremiah 26's use;
- Micah 4 / Isaiah 2 wording and literary direction, nations, Zion, Torah,
  weapons, agriculture, vine and fig tree, the lame remnant, labor, Babylon,
  and verse numbering;
- Bethlehem Ephrathah, *motzaot*, ruler identity and horizons, the woman in
  labor, seven/eight formula, Assyria, Nimrod, dew and lion, and removal of
  military, magical, urban, and cult objects;
- the genre of Micah 6, creation as witness, exodus, Moses, Aaron, Miriam,
  Balak, Balaam, Shittim, Gilgal, sacrifice, firstborn, *mishpat*, *hesed*,
  *hatsnea lekhet*, dishonest measures, Omri, and Ahab;
- every speaker and form in Micah 7, household conflict, enemy address,
  confession, shepherd prayer, Carmel, Bashan, Gilead, nations, exodus
  imagery, pardon, name wordplay, sea metaphor, Jacob, and Abraham;
- every MT, Old Greek, CATSS, NETS, 4Q81, 4Q82, MurXII, 8HevXII, pesher,
  versional, numbering, and textual-variant statement;
- every proposed relationship to Isaiah, Jeremiah, Kings, Chronicles, Torah,
  Psalms, Hosea, Amos, Jonah, Nahum, Matthew, Luke, John, Davidic tradition,
  Zion tradition, and the Twelve;
- early Jewish, rabbinic, living Jewish, early Christian, messianic,
  christological, artistic, musical, political, liberationist, postcolonial,
  gender-critical, ecological, disability-aware, and trauma-aware reception;
- all safeguards concerning antisemitism, supersessionism, anti-ritualism,
  land and housing abuse, coercion, child sacrifice, domestic violence,
  survivor safety, disability, gender, racism, nationalism, Zionism,
  anti-Zionism, colonialism, empire, war, genocide, displacement, disaster
  blame, divine violence, vengeance, humility, and forgiveness; and
- every source author, title, date, URL, locator, support target, claim
  rationale, certainty label, dispute label, graph relationship, and
  application.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

Pre-edit baseline:

```text
python3 -m unittest tests.canonical_library.test_micah_record
# 8 tests; 22 expected failures across seven content/retrieval groups
# SQLite parity alone passed
```

Final verification:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/micah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_micah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 18.271s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 380 tests in 309.279s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,200 edges, 0 unknown targets, 0 orphaned objects
# 2,760 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave24-micah.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave24-micah.sqlite
# 620 objects; schema 2; fingerprint
# 8dfdde1054284dd7574072d55fe53480d19082770806299ab16320ce38261049
# 36,188,160 bytes
```
