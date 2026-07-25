# Phase 5 Wave 22 Review: Obadiah

Last updated: 2026-07-25

## Review status

The Obadiah correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`obadiah.json`](../framework/canonical_library/objects/books/obadiah.json)
- [`test_obadiah_record.py`](../tests/canonical_library/test_obadiah_record.py)

## Corrections made

- Removed the inherited Minor Prophets placeholder, including unrelated Hosea,
  Amos, Jonah, and Nineveh values, generic corpus dates and setting, legacy
  certainty labels, internal-only orientation sourcing, and the false
  `complete` status and review date.
- Rebuilt the record around Obadiah 1; 2–9; 10–14; 15–16; and 17–21 while
  preserving alternate outlines, speaker questions, and proposed seams.
- Distinguished Obadiah's sparse superscription, YHWH's reported speech, the
  prophetic voice, the envoy and summoned nations, Edom or Esau, Jacob or
  Israel, Judah and Jerusalem, invaders, allies, sages, warriors, fugitives,
  survivors, the houses of Jacob, Joseph, and Esau, regional populations,
  exiles in Sepharad, and the unnamed figures ascending Zion.
- Distinguished prophetic superscription, vision report, messenger report,
  nations oracle, taunt and reversal, accusation, disputed prohibitions or
  ironic retrospective commands, day-of-YHWH oracle, salvation oracle,
  territorial catalogue, and kingship conclusion.
- Qualified the name Obadiah, absence of patronymic and royal date,
  seventh-century, 587/586 BCE, Persian-period, and compositional proposals,
  Edom's highland setting, southern Judah and Negev interaction, Jerusalem's
  fall, and later Nabataean and Idumean histories.
- Addressed pride, rocky security, alliances, wisdom, warriors, plunder,
  kinship betrayal, violence, gloating, looting, fugitives, survivor handover,
  reciprocal judgment, drinking, holiness, fire, land, restoration, and
  YHWH's kingship.
- Preserved uncertainty concerning the envoy and prophetic plural, allies,
  Teman, the force and time of verses 12–14, the precise historical actions
  attributed to Edom, the day oracle's horizon, verse 16's pronouns and
  drinking imagery, possession in verse 17, verses 19–20's syntax and
  geography, Sepharad, verse 21's plural figures, and the date and unity of
  the closing section.
- Added Masoretic Obadiah, Old Greek Abdias, NETS, CATSS, 4Q82, Jeremiah 49,
  Genesis, Joel, Amos, Psalms, Lamentations, Ezekiel, and Malachi as explicitly
  classified witnesses or comparanda.
- Distinguished textual parallel from disputed borrowing, historical Edom
  from later Edom-as-Rome reception, canonical trajectory from quotation,
  and later Jewish, christological, ecclesial, political, postcolonial, and
  trauma-aware reception from the oracle's first historical horizon.
- Added safeguards concerning ethnic essentialism, hereditary guilt,
  antisemitism, anti-Arab racism, modern ethnic or national coding,
  supersessionism, survivor blame, refugee and border violence, trauma
  exploitation, empire, colonialism, nationalism, revenge, genocide, land
  seizure, and forced displacement.
- Added twenty-three sourced claims, thirty-seven current-taxonomy
  interpretive notes, twenty-three source records, twenty-two URL-bearing
  external sources, seven graph relationships, seventeen Scripture anchors,
  seventeen Hebrew entries, ten Greek entries, explicit section statuses and
  knowledge layers, a populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `obadiah-superscription-identity` | `textually_explicit` | `historical_uncertainty` |
| `obadiah-name` | `strong_consensus` | `minor_scholarly_disagreement` |
| `obadiah-date` | `probable` | `major_scholarly_disagreement` |
| `obadiah-edom-geography` | `probable` | `archaeological_uncertainty` |
| `obadiah-jerusalem-calamity` | `textually_explicit` | `historical_uncertainty` |
| `obadiah-edom-actions` | `textually_explicit` | `major_scholarly_disagreement` |
| `obadiah-pride-security` | `textually_explicit` | `minor_scholarly_disagreement` |
| `obadiah-allies-wisdom` | `textually_explicit` | `historical_uncertainty` |
| `obadiah-messenger` | `textually_explicit` | `major_scholarly_disagreement` |
| `obadiah-commands-12-14` | `disputed` | `major_scholarly_disagreement` |
| `obadiah-day-yhwh` | `textually_explicit` | `minor_scholarly_disagreement` |
| `obadiah-reciprocity` | `textually_explicit` | `major_scholarly_disagreement` |
| `obadiah-drinking` | `disputed` | `major_scholarly_disagreement` |
| `obadiah-zion-survivors` | `textually_explicit` | `textual_variant` |
| `obadiah-houses-fire` | `textually_explicit` | `major_scholarly_disagreement` |
| `obadiah-territorial-catalogue` | `disputed` | `major_scholarly_disagreement` |
| `obadiah-saviors-kingdom` | `textually_explicit` | `lexical_uncertainty` |
| `obadiah-jeremiah49` | `strong_consensus` | `major_scholarly_disagreement` |
| `obadiah-twelve-placement` | `strong_consensus` | `major_scholarly_disagreement` |
| `obadiah-textual-witnesses` | `strong_consensus` | `textual_variant` |
| `obadiah-nt-no-quotation` | `strong_consensus` | `minor_scholarly_disagreement` |
| `obadiah-edom-reception` | `strong_consensus` | `major_scholarly_disagreement` |
| `obadiah-composition` | `probable` | `major_scholarly_disagreement` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and mappings are in
[`obadiah.json`](../framework/canonical_library/objects/books/obadiah.json).

## Sources used

Primary witnesses include Masoretic Obadiah, Old Greek Abdias, 4Q82, NETS,
CATSS, Jeremiah 49, and other canonical comparanda. Independent research
sources include:

- Paul R. Raabe, *Obadiah*:
  <https://yalebooks.yale.edu/book/9780300139716/obadiah/>.
- Bob Becking, “Obadiah”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334373312>.
- James D. Nogalski, *The Books of Joel, Obadiah, and Jonah*:
  <https://www.eerdmans.com/9781467465700/the-books-of-joel-obadiah-and-jonah/>.
- Leslie C. Allen, *The Books of Joel, Obadiah, Jonah, and Micah*:
  <https://www.eerdmans.com/9781467468299/the-books-of-joel-obadiah-jonah-and-micah/>.
- Anthony Gelston and M. Daniel Carroll R., *Eerdmans Commentary on the
  Bible: Joel, Amos, Obadiah*:
  <https://www.eerdmans.com/9781467453936/eerdmans-commentary-on-the-bible-joel-amos-obadiah/>.
- Julia M. O'Brien, “Overview: Approaching the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter/334371096>.
- Nicholas R. Werse, “Violence in the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372028>.
- Stacy Davis, “Race and Intersectionality in Study of the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372701>.
- Jeremiah W. Cataldo, “Postcolonial Approaches to the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372842>.
- Malka Z. Simkovich, “The Minor Prophets in Early Judaism”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372283>.
- Stephen Lewis Fuchs, “The Minor Prophets in Jewish Life Today”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334372906>.
- Kimberly R. Wagner and Brady Alan Beard, “The Minor Prophets in
  Christianity”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334373012>.
- Juan Manuel Tebes, “The Edomite Involvement in the Destruction of the First
  Temple”:
  <https://journals.sagepub.com/doi/10.1177/0309089211423731>.
- Andrew Joel Danielson, *Edom in Judah*:
  <https://escholarship.org/uc/item/39t2f71m>.
- Juan Manuel Tebes, “Edom and Southern Jordan in the Iron Age”:
  <https://www.taylorfrancis.com/chapters/edit/10.4324/9780367815691-46/edom-southern-jordan-iron-age-juan-manuel-tebes>.
- John Lindsay, “The Edomite 'Acro-Sites' in Transjordan”:
  <https://poj.peeters-leuven.be/content.php?id=3291194&url=article>.
- Jacob L. Wright, “Edom as Israel's Other”:
  <https://www.cambridge.org/core/product/2BE2F11FE9B1687D7659F5E566DDB29E/core-reader>.
- CATSS, “Text and Textual Variants for the Old Greek Book of Obadiah”:
  <https://ccat.sas.upenn.edu/gopher/text/religion/biblical/lxxvar/active/04Obadiah-v7.html>.
- George E. Howard, *A New English Translation of the Septuagint: The Twelve
  Prophets*:
  <https://ccat.sas.upenn.edu/nets/edition/32-twelve-nets.pdf>.
- Israel Antiquities Authority, 4Q82:
  <https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q82-1>.
- Armin Lange, “4QXIIg (4Q82) as an Editorial Text”:
  <https://openscholar.huji.ac.il/sites/default/files/he_bible_project/files/a._lange.pdf>.
- *New Form Criticism and the Book of the Twelve*:
  <https://www.sbl-site.org/assets/pdfs/pubs/9781628370614_OA.pdf>.

Publisher, university, archive, scholarly-organization, and journal pages
establish bibliographic identity, scope, material witness, or a bounded
research claim. They do not substitute for a qualified reviewer checking every
use, locator, translation, or scholarly position.

## Retrieval coverage

The tests require a first-place Obadiah result for:

- the prophet's identity, absent patronymic, date, 587/586 BCE, seventh-century
  and Persian-period proposals;
- Edom's geography, pride, mountain security, allies, Teman, wisdom, warriors,
  and relationship to Jerusalem's fall;
- the envoy among the nations, verses 12–14's disputed grammar, gloating,
  looting, fugitives, survivors, and reciprocal judgment;
- day of YHWH, drinking on the holy mountain, survivors and holiness on Zion,
  and the houses of Jacob, Joseph, and Esau;
- Negeb, Shephelah, Ephraim, Samaria, Gilead, Zarephath, Sepharad, the plural
  deliverers, and YHWH's kingship;
- Jeremiah 49, Old Greek Abdias, 4Q82, Book-of-the-Twelve placement, and the
  absence of a secure direct New Testament quotation; and
- Edom-as-Rome reception, modern ethnic coding, racism, nationalism, land
  seizure, genocide, vengeance, displacement, and trauma-aware reading.

All pass with the existing retrieval implementation. No ranking-code change
was needed.

## Human review checklist

Verify:

- the superscription, every voice, pronoun, addressee, quotation boundary,
  reported speech, speaker shift, and collective identity;
- the five-part practical outline and every alternate unit, seam, genre, and
  rhetorical transition;
- the name Obadiah and the lack of grounds for identifying the prophet with
  another bearer of the name;
- every seventh-century, 587/586 BCE, sixth-century, Persian-period,
  collection, expansion, unity, and final-form proposal;
- Edom's highland and lowland geography, routes, polity, Negev interaction,
  southern Judah, Petra cautions, Nabataean history, Idumea, and every
  archaeological inference;
- every proposal concerning Edom's conduct during Jerusalem's catastrophe,
  including whether the sequence is documentary, rhetorical, remembered, or
  polemical;
- the envoy, first-person plural, allies, bread, trap, Teman, sages, warriors,
  and each lexical judgment;
- the tense, mood, discourse time, and translation of verses 12–14;
- day-of-YHWH, reciprocal judgment, drinking, Mount Zion, escape, holiness,
  possession, fire, and the houses of Jacob, Joseph, and Esau;
- every subject, object, place, border, exile group, and map proposed for
  verses 19–20, especially Sepharad;
- the lexical and political alternatives for the plural figures in verse 21
  and the relation of their action to YHWH's kingship;
- every MT, Old Greek, CATSS, NETS, 4Q82, versional, and textual-variant claim;
- every proposed relationship to Jeremiah 49, Joel, Amos, Genesis, Psalms,
  Lamentations, Ezekiel, Malachi, and the Twelve;
- early Jewish, rabbinic, Edom-as-Rome, later Jewish, Christian,
  christological, ecclesial, political, postcolonial, and trauma-aware
  reception;
- safeguards concerning ethnicity, hereditary guilt, antisemitism,
  anti-Arab racism, supersessionism, refugees, survivor blame, trauma,
  empire, colonialism, nationalism, war, genocide, land, displacement,
  revenge, and modern political capture; and
- every source author, title, date, URL, locator, support target, claim
  rationale, certainty label, dispute label, relationship, and application.

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

The pre-edit fixture failed in twenty places across seven content test groups;
SQLite parity alone passed. After the record rebuild:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/obadiah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_obadiah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 16.858s: OK

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,194 edges, 0 unknown targets, 0 orphaned objects
# 2,754 missing reciprocal suggestions remain as migration debt

python3 -m unittest tests/canonical_library/test_*.py
# 364 tests in 276.882s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep \
  --output docs/ckl-quality-report.md

python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep \
  --json \
  --output docs/ckl-quality-report.json

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave22-final-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave22-final-ckl.sqlite
# 620 objects; database schema 2
# fingerprint d48df68d09650c084794370c6b36838eb999f6b9adf3ecdd7264d32237d2d84d
# 35,201,024 bytes
```

The full suite emitted only the known Python 3.14 unclosed-SQLite
`ResourceWarning`s. `git diff --check` also passed.
