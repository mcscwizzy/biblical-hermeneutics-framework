# Phase 5 Wave 21 Review: Amos

Last updated: 2026-07-25

## Review status

The Amos correction wave is implemented and machine-verified at the focused
level. The record remains `draft` / `in_review`, requires human review, has no
`last_reviewed` date, and has `section_status.human_review` set to `missing`.
Automated validation does not constitute approval.

Files for review:

- [`amos.json`](../framework/canonical_library/objects/books/amos.json)
- [`test_amos_record.py`](../tests/canonical_library/test_amos_record.py)

## Corrections made

- Removed the inherited Minor Prophets placeholder, including unrelated Hosea,
  Jonah, and Nineveh values, generic corpus-wide dates and setting, obsolete
  evidence labels, internal-only orientation sourcing, and the false
  `complete` status and review date.
- Rebuilt the record around Amos 1:1–2; 1:3–2:16; 3:1–6:14; 7:1–9:10; and
  9:11–15, while preserving alternative outlines and compositional questions.
- Distinguished Amos of Tekoa, YHWH's direct and reported speech, the
  first-person vision voice, the third-person Bethel narrator, Amaziah,
  Jeroboam II, Uzziah, national and urban collectives, powerful people,
  oppressed people, merchants, judges, Nazirites, prophets, neighboring
  peoples, and David's fallen booth.
- Distinguished superscription, nations oracle, accusation, judgment,
  summons, rhetorical-question chain, lament, woe, doxology, vision,
  wordplay, biographical narrative, disputation, salvation oracle, and
  prophetic poetry.
- Qualified the mid-eighth-century superscription setting, Tekoa, Amos's
  occupation and social status, northern ministry, the earthquake, prosperity
  and inequality, Assyrian expansion, Judean transmission, disciples,
  collection, redaction, final form, and shaping within the Twelve.
- Addressed election and accountability, justice and righteousness, gate
  adjudication, debt, land, labor, taxation, elite luxury, sexual
  exploitation, dishonest trade, worship, sacrifice, song, sanctuaries, day
  of YHWH, remnant, exile, creation, famine of hearing, judgment,
  intercession, prophetic vocation, and restoration.
- Preserved uncertainty concerning the nations sequence, calls to seek and
  live, doxological fragments, Sikkuth and Kiyyun, the five visions, *anak*,
  Amaziah's authority, Amos 7:14, summer-fruit wordplay in translation, the
  altar vision, textual difficulties, Amos 9:11–15's date and unity, and
  David's fallen booth.
- Added Masoretic Amos, Old Greek Amos, 4Q78, 4Q82, other Judean Desert
  witnesses, prophetic intertexts, Acts 7, Acts 15, commentary, theology,
  literary, social-justice, creation, violence, gender, archaeology, form,
  textual-variant, and reception-history anchors.
- Distinguished historical referent, literary form, textual witness,
  quotation, canonical trajectory, Jewish reception, christological
  reception, ecclesial application, and modern analogy.
- Added safeguards concerning poverty romanticization, class contempt,
  wealth shaming without exploitation, blaming poor people, coercive charity,
  debt and labor abuse, racism, misogynistic reuse of the cows-of-Bashan
  metaphor, sexual violence, clergy and prophetic abuse, anti-ritual and
  anti-Jewish readings, antisemitism, supersessionism, empire, colonialism,
  nationalism, war, genocide, land, disaster blame, divine violence,
  vengeance, and partisan capture of justice language.
- Added twenty-two sourced claims, thirty-nine current-taxonomy interpretive
  notes, twenty-two source records, nineteen URL-bearing external sources,
  seven graph relationships, fifteen structured Scripture anchors, fifteen
  Hebrew entries, ten Greek entries, explicit section statuses and knowledge
  layers, a populated hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `amos-superscription-identity` | `textually_explicit` | `historical_uncertainty` |
| `amos-rulers-date` | `strong_consensus` | `chronological_uncertainty` |
| `amos-earthquake` | `textually_explicit` | `archaeological_uncertainty` |
| `amos-nations-sequence` | `textually_explicit` | `minor_scholarly_disagreement` |
| `amos-election-accountability` | `textually_explicit` | `minor_scholarly_disagreement` |
| `amos-economic-exploitation` | `textually_explicit` | `historical_uncertainty` |
| `amos-worship-justice` | `textually_explicit` | `major_scholarly_disagreement` |
| `amos-day-yhwh` | `textually_explicit` | `historical_uncertainty` |
| `amos-five-visions` | `textually_explicit` | `major_scholarly_disagreement` |
| `amos-intercession` | `textually_explicit` | `minor_scholarly_disagreement` |
| `amos-amaziah-bethel` | `textually_explicit` | `historical_uncertainty` |
| `amos-occupation` | `disputed` | `lexical_uncertainty` |
| `amos-anak-vision` | `disputed` | `lexical_uncertainty` |
| `amos-summer-fruit` | `textually_explicit` | `minor_scholarly_disagreement` |
| `amos-famine-hearing` | `textually_explicit` | `minor_scholarly_disagreement` |
| `amos-altar-vision` | `textually_explicit` | `textual_variant` |
| `amos-david-booth` | `textually_explicit` | `major_scholarly_disagreement` |
| `amos-restoration-ending` | `textually_explicit` | `major_scholarly_disagreement` |
| `amos-hebrew-greek-witnesses` | `strong_consensus` | `textual_variant` |
| `amos-acts7-reuse` | `textually_explicit` | `textual_variant` |
| `amos-acts15-reuse` | `textually_explicit` | `major_scholarly_disagreement` |
| `amos-composition-final-form` | `probable` | `major_scholarly_disagreement` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and mappings are in
[`amos.json`](../framework/canonical_library/objects/books/amos.json).

## Sources used

Primary witnesses include Masoretic Amos, Old Greek Amos, 4Q78, 4Q82, other
Judean Desert Amos witnesses, prophetic comparanda, Acts 7, and Acts 15.
Independent research sources include:

- Göran Eidevall, *Amos*:
  <https://yalebooks.yale.edu/book/9780300178784/amos/>.
- M. Daniel Carroll R., *The Book of Amos*:
  <https://www.eerdmans.com/9780802825384/the-book-of-amos/>.
- Walter Houston, “Amos”:
  <https://academic.oup.com/reference/62341/reference-article-abstract/554094758>.
- J. Blake Couey, “Amos,” in *The Oxford Handbook of the Minor Prophets*:
  <https://academic.oup.com/edited-volume/38566/chapter/334373262>.
- Graham R. Hamborg, “Book of Amos”:
  <https://www.cambridge.org/core/books/abs/hosea-joel-and-amos/book-of-amos/38376818DCC62BB9E6A9F3FDAAB50BDF>.
- John Barton, *The Theology of the Book of Amos*:
  <https://assets.cambridge.org/97805218/55778/frontmatter/9780521855778_frontmatter.pdf>.
- Daniel L. Smith-Christopher, “The Problem of Justice as Social Criticism in
  the Twelve Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334371947>.
- Ethan Schwartz, “Beyond Athens and Jerusalem”:
  <https://www.cambridge.org/core/journals/harvard-theological-review/article/beyond-athens-and-jerusalem-integrating-classical-philosophy-into-the-comparative-study-of-the-hebrew-bible-and-the-ancient-near-east/E1604C0E38EE155E430787A17A6B16ED>.
- Howard Moltz, “A Literary Interpretation of the Book of Amos”:
  <https://www.cambridge.org/core/journals/horizons/article/abs/literary-interpretation-of-the-book-of-amos/113FD6856E389485F0089CE443DCDC64>.
- Susan Gillingham, “Who Makes the Morning Darkness”:
  <https://www.cambridge.org/core/journals/scottish-journal-of-theology/article/who-makes-the-morning-darkness-god-and-creation-in-the-book-of-amos/7F89BE421F0AE1B15F1C6FFF18003946>.
- *New Form Criticism and the Book of the Twelve*:
  <https://www.sbl-site.org/assets/pdfs/pubs/9781628370614_OA.pdf>.
- Julia M. O'Brien, “Overview: Approaching the Minor Prophets”:
  <https://academic.oup.com/edited-volume/38566/chapter/334371096>.
- Jerome F. D. Creach, “Violence in the Old Testament”:
  <https://academic.oup.com/edited-volume/62249/chapter-abstract/551374654>.
- Steven A. Austin, Gordon W. Franz, and Eric G. Frost, “Amos's Earthquake”:
  <https://www.researchgate.net/publication/298846141_Amos%27s_earthquake_An_extraordinary_Middle_East_seismic_event_of_750_BC>.
- George E. Howard, *A New English Translation of the Septuagint: The Twelve
  Prophets*:
  <https://ccat.sas.upenn.edu/nets/edition/32-twelve-nets.pdf>.
- CATSS, “Amos Greek Variants File”:
  <https://ccat.sas.upenn.edu/gopher/text/religion/biblical/lxxvar/active/03Amos.html>.
- Israel Antiquities Authority, 4Q78:
  <https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q78-1>.
- Israel Antiquities Authority, 4Q82:
  <https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q82-1>.
- Armin Lange, “4QXIIg (4Q82) as an Editorial Text”:
  <https://openscholar.huji.ac.il/sites/default/files/he_bible_project/files/a._lange.pdf>.

Publisher, university, archive, scholarly-organization, and journal pages
establish bibliographic identity, scope, material witness, or a bounded
research claim. They do not substitute for a qualified reviewer checking every
use and locator. The CATSS file identifies itself as provisional. The
archaeoseismic source presents an influential correlation proposal, not proof
of an exact year, magnitude, epicenter, or layer.

## Retrieval coverage

The tests require a first-place Amos result for:

- Amos, Tekoa, occupation, social status, Jeroboam II, Uzziah, date, and the
  earthquake;
- the nations sequence, three/four formula, election, and accountability;
- cows of Bashan, gendered rhetoric, misogyny, sexual exploitation, debt,
  labor, courts, poor people, and dishonest trade;
- justice and righteousness, rejected worship, sacrifice, music, ritual, and
  the day of YHWH;
- Sikkuth, Kiyyun, the five visions, intercession, Amaziah, Bethel,
  professional prophecy, *anak*, summer fruit, and famine of hearing;
- David's fallen booth, restoration, Old Greek Amos, 4Q78, and 4Q82;
- Acts 7, Acts 15, Israel, gentile inclusion, antisemitism, and
  supersessionism; and
- partisan capture, nationalism, colonialism, vengeance, and violence.

All pass with the existing retrieval implementation. No ranking-code change
was needed.

## Human review checklist

Verify:

- every speaker, addressee, collective, narrator transition, quotation, and
  reported speech;
- every place, king, sanctuary, nation, people, social group, occupation,
  institution, and proposed historical correlation;
- the Uzziah-Jeroboam synchronism, proposed ministry date, earthquake notice,
  archaeology, Assyrian horizon, prosperity, inequality, and Samaria evidence;
- the practical outline, nations sequence, summonses, accusations, laments,
  woes, doxologies, five visions, Bethel narrative, altar vision, and ending;
- every claim about *noqed*, *boqer*, sycamore figs, *mishpat*, *tsedaqah*,
  poor-person terms, *anak*, *qayits/qets*, famine, and David's booth;
- every debt, pledge, land, labor, tax, court, commercial, luxury, worship,
  sexual, and war-crime reconstruction;
- the cows-of-Bashan metaphor and safeguards against misogyny, body shaming,
  racism, sexual violence, victim blaming, and institutional evasion;
- election, exodus, covenant, day of YHWH, remnant, intercession, judgment,
  exile, creation, ecological disruption, restoration, and land;
- every proposal about Amos 5:25–27, Sikkuth, Kiyyun, Greek forms, Acts 7,
  and anti-Jewish misuse;
- every proposal about Amos 9:11–15, date, unity, Davidic referent, Masoretic
  Edom, Greek humanity, Acts 15, gentile inclusion, and ecclesial application;
- the MT, Old Greek, 4Q78, 4Q82, 5QAmos, MurXII, CATSS, and other versional
  evidence and every textual claim;
- authorship, historical Amos, disciples, collections, Judean transmission,
  redaction, literary-production, final-form, and Twelve-shaping models;
- Jewish and rabbinic reception and whether the source set represents them
  adequately before Christian reception;
- Black, civil-rights, liberation, womanist, political, postcolonial, and
  ecological reception without collapsing distinct voices;
- safeguards concerning poverty, wealth, charity, debt, labor, courts,
  clergy, prophets, disaster, antisemitism, supersessionism, empire,
  colonialism, nationalism, war, genocide, land, divine violence, vengeance,
  and partisan capture; and
- every source locator, support target, certainty label, dispute label,
  relationship, and pastoral application.

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

The pre-edit fixture correctly failed in twenty places across seven content
test groups; SQLite parity alone passed. After the record rebuild:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/amos.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_amos_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 16.294s: OK

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,192 edges, 0 unknown targets, 0 orphaned objects
# 2,752 missing reciprocal suggestions remain as migration debt

python3 -m unittest tests/canonical_library/test_*.py
# 356 tests in 251.029s: OK

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
  --output /private/tmp/bhf-phase5-wave21-final-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave21-final-ckl.sqlite
# 620 objects; database schema 2
# fingerprint 31356a8bf9bc6325121549155cc5b09884555a79967651b1ee5a2fe4038b86fc
# 34,738,176 bytes
```

The full suite emitted only the known Python 3.14 unclosed-SQLite
`ResourceWarning`s. `git diff --check` also passed.
