# Phase 5 Wave 26 Review: Habakkuk

Last updated: 2026-07-25

## Review status

The Habakkuk correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`habakkuk.json`](../framework/canonical_library/objects/books/habakkuk.json)
- [`test_habakkuk_record.py`](../tests/canonical_library/test_habakkuk_record.py)

## Corrections made

- Removed the inherited Minor Prophets placeholder, including unrelated Hosea,
  Amos, Jonah, and Nineveh values, corpus-wide dates, internal-only sourcing,
  legacy evidence labels, and false completion and review metadata.
- Rebuilt the record around Habakkuk 1:1; 1:2–4; 1:5–11; 1:12–17; 2:1;
  2:2–5; 2:6–20; 3:1–2; 3:3–15; and 3:16–19.
- Distinguished Habakkuk's framing, complaint, watch, prayer, and singing
  voices; YHWH's direct answers and manifestation; Judah's wicked, righteous,
  Torah, justice, and oppressed; Chaldeans, arrogant conqueror, taunting
  peoples, debtors, idol makers, silent earth, creation, anointed one,
  agricultural world, musicians, and later interpreters.
- Distinguished superscription, complaint, disputation, divine response,
  historical oracle, watch report, vision instruction, wisdom contrast,
  taunt, five woes, ridicule, idol polemic, temple acclamation, prayer,
  petition, hymn, divine-warrior theophany, victory song, confession, and
  musical subscription.
- Qualified the late-seventh/early-sixth-century horizon, Assyria's collapse,
  Nineveh in 612, Harran in 609, Carchemish in 605, Jehoiakim, Babylonian
  pressure, Jerusalem in 597 and 586, and the distinct ranges and perspectives
  of BM 21901 and BM 21946.
- Added bounded comparison with Neo-Babylonian cavalry, siege, deportation,
  tribute, debt, labor, brick and timber construction, wine, idols, forests,
  animals, crops, and royal self-presentation. Archaeological and inscriptional
  context is not treated as proof of each poetic detail.
- Preserved uncertainty concerning title, biography, date, addressees,
  Chaldean oracle, divine agency, wicked and righteous, watchpost, tablets,
  runner, appointed time, Habakkuk 2:4, five-woe sequence, debt wordplay,
  death or Sheol, cup, foreskin or nakedness, Lebanon, animals, idols, temple,
  chapter 3, *shigionoth*, *selah*, Teman, Paran, Cushan, Midian, cosmic
  images, anointed one, enemy head, and musical subscription.
- Added Masoretic Habakkuk, CATSS Old Greek Ambakoum, NETS, BHS, 1QpHab,
  Hebrew Bible and New Testament comparanda, critical commentaries,
  Babylonian Chronicles, Neo-Babylonian inscriptions, and early Jewish,
  Christian, artistic, postcolonial, womanist, feminist, trauma-aware, and
  ecological reception resources.
- Distinguished historical referent, prophetic complaint, divine speech,
  poetry, metaphor, textual witness, translation, pesher, New Testament
  quotation, canonical trajectory, doctrinal reception, typology, pastoral
  application, and modern analogy.
- Added safeguards concerning antisemitism, faith-versus-law anti-Judaism,
  supersessionism, anti-Iraqi and anti-Middle Eastern racism, ethnic proxies,
  quietism, fatalism, prosperity teaching, survivor blame, suicide and
  mental-health stigma, disability metaphors, sexualized humiliation,
  intoxication, dehumanization, conquest, siege, forced labor, plunder,
  genocide, ethnic cleansing, displacement, collective punishment,
  nationalism, colonialism, war propaganda, revenge, divine violence, trauma
  voyeurism, ecological destruction, and partisan enemy-mapping.
- Added twenty-eight sourced claims, forty-six current-taxonomy interpretive
  notes, twenty-four source records, twenty-one URL-bearing external sources,
  eight graph relationships, nineteen Scripture anchors, twenty-two Hebrew
  entries, eight Greek entries, section statuses, knowledge layers, a
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `habakkuk-superscription` | `textually_explicit` | `lexical_uncertainty` |
| `habakkuk-biography` | `insufficient_evidence` | `historical_uncertainty` |
| `habakkuk-date` | `probable` | `chronological_uncertainty` |
| `habakkuk-composition` | `strong_consensus` | `major_scholarly_disagreement` |
| `habakkuk-first-complaint` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-chaldean-response` | `strong_consensus` | `minor_scholarly_disagreement` |
| `habakkuk-agency` | `strong_consensus` | `major_scholarly_disagreement` |
| `habakkuk-fish-net` | `strong_consensus` | `minor_scholarly_disagreement` |
| `habakkuk-watchpost` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-vision` | `textually_explicit` | `lexical_uncertainty` |
| `habakkuk-two-four` | `textually_explicit` | `textual_variant` |
| `habakkuk-five-woes` | `strong_consensus` | `minor_scholarly_disagreement` |
| `habakkuk-debtors` | `probable` | `lexical_uncertainty` |
| `habakkuk-construction` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-glory` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-cup` | `strong_consensus` | `lexical_uncertainty` |
| `habakkuk-ecology` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-idols` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-prayer` | `textually_explicit` | `lexical_uncertainty` |
| `habakkuk-theophany` | `strong_consensus` | `major_scholarly_disagreement` |
| `habakkuk-anointed` | `textually_explicit` | `major_scholarly_disagreement` |
| `habakkuk-final-confession` | `textually_explicit` | `minor_scholarly_disagreement` |
| `habakkuk-chronicles` | `strong_consensus` | `not_disputed` |
| `habakkuk-babylonian-sources` | `strong_consensus` | `not_disputed` |
| `habakkuk-textual-witnesses` | `strong_consensus` | `textual_variant` |
| `habakkuk-pesher` | `strong_consensus` | `historical_uncertainty` |
| `habakkuk-new-testament` | `strong_consensus` | `minor_scholarly_disagreement` |
| `habakkuk-ethical-reception` | `strong_consensus` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within the record.

## Principal sources used

Primary and material witnesses include Masoretic Habakkuk, Old Greek
Ambakoum, 1QpHab, Hebrew Bible and New Testament comparanda, BM 21901,
BM 21946, and Neo-Babylonian royal inscriptions. Independent research
sources include:

- Grace Ko, “Habakkuk”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334373592>.
- Francis I. Andersen, *Habakkuk*:
  <https://yalebooks.yale.edu/book/9780300139730/habakkuk/>.
- Daniel C. Timmer, *The Theology of the Books of Nahum, Habakkuk, and
  Zephaniah*:
  <https://www.cambridge.org/core/books/theology-of-the-books-of-nahum-habakkuk-and-zephaniah/4FD8871C1A8A5EA40AF14C38DC153391>.
- Wilda C. M. Gafney, *Nahum, Habakkuk, Zephaniah*:
  <https://litpress.org/Products/E8187/Wisdom-Commentary-Nahum-Habakkuk-Zephaniah>.
- CATSS, Old Greek Habakkuk:
  <https://ccat.sas.upenn.edu/gopher/text/religion/biblical/lxxvar/4Prophets/MinorProphets/08Habakkuk.html>.
- NETS, *The Twelve Prophets*:
  <https://ccat.sas.upenn.edu/nets/edition/32-twelve-nets.pdf>.
- Israel Museum, [Commentary on Habakkuk Scroll](https://dss.collections.imj.org.il/habakkuk).
- British Museum records for
  [BM 21901](https://www.britishmuseum.org/collection/object/W_1896-0409-6)
  and
  [BM 21946](https://www.britishmuseum.org/collection/object/W_1896-0409-51).
- ORACC records for
  [Nabopolassar 01](https://oracc.museum.upenn.edu/ribo/Q005360)
  and
  [Nebuchadnezzar II 002](https://oracc.museum.upenn.edu/ribo/babylon7/Q005473).
- Kimberly R. Wagner and Brady Alan Beard,
  [“Habakkuk as a Model for Posttraumatic Christian Prophetic
  Preaching”](https://academic.oup.com/edited-volume/38566/chapter-abstract/334373012).

Publisher, university, archive, scholarly-organization, and museum pages
establish bibliographic identity, material witness, or a bounded research
claim. A qualified reviewer must still check every locator, translation,
textual reading, historical inference, and scholarly characterization.

## Retrieval coverage

The regression requires Habakkuk to rank first for questions about:

- title, prophet, date, Chaldeans, divine agency, Torah, justice, and fish;
- watchpost, tablets, runner, appointed time, and waiting;
- Habakkuk 2:4 in Masoretic, Greek, Qumran, Pauline, and Hebrews forms;
- five woes, creditors, debt, gain, construction, forced labor, and glory;
- intoxication, nakedness, foreskin, cup, Lebanon, animals, idols, and temple;
- *shigionoth*, *selah*, Teman, Paran, Cushan, Midian, exodus, creation,
  divine warrior, anointed one, and enemy head;
- trembling, crops, livestock, joy, strength, choirmaster, and instruments;
- 1QpHab, Babylonian Chronicles, Acts, Romans, Galatians, and Hebrews; and
- anti-Judaism, quietism, ethnic proxies, violence, trauma, disability,
  ecology, collective punishment, and modern political mapping.

All pass with the existing retrieval implementation. Five exact aliases
disambiguate deliberately cross-book appointed-time, musical, chronicle,
New Testament, and faith-versus-law questions.

## Human review checklist

Verify:

- every Masoretic, BHS, CATSS, NETS, 1QpHab, Old Greek, New Testament,
  translation, possessive, word order, and textual-variant statement;
- *massa*, Habakkuk's name and title, speakers, addressees, quotations,
  imperatives, pronouns, complaint-response boundaries, and seams;
- Chaldeans, Nineveh, Harran, Carchemish, Jehoiakim, 597, 586, BM 21901,
  BM 21946, Nabopolassar, Nebuchadnezzar, and every date range;
- cavalry, siege ramps, deportation, tribute, debt, forced labor,
  construction, wine, idolatry, forests, animals, crops, and archaeology;
- wicked, righteous, watchpost, tablets, runner, appointed time, *emunah*,
  inflated one, five woes, creditors, pledges, Sheol, stones, timber, cup,
  foreskin, Lebanon, animals, idols, and temple;
- *shigionoth*, *selah*, Teman, Paran, Cushan, Midian, pestilence, rivers,
  sea, sun, moon, horses, anointed one, enemy head, crop failure, and musical
  subscription;
- every proposed relationship with Exodus, Deuteronomy, Judges, Psalms,
  Isaiah, Jeremiah, Nahum, Zephaniah, Daniel, Acts, Romans, Galatians, and
  Hebrews;
- every distinction among history, complaint, divine speech, poetry,
  metaphor, witness, translation, pesher, quotation, trajectory, typology,
  doctrine, application, and analogy;
- early Jewish, Christian, rabbinic, patristic, Reformation, artistic,
  liturgical, feminist, womanist, liberationist, postcolonial, disability,
  trauma, ecological, and political reception; and
- every safeguard, source author, title, year, URL, locator, support target,
  claim rationale, certainty, dispute label, relationship, and application.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

Pre-edit baseline:

```text
python3 -m unittest tests.canonical_library.test_habakkuk_record
# 8 tests; 23 expected failures across seven content/retrieval groups
# SQLite parity alone passed
```

Focused verification:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/habakkuk.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_habakkuk_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 18.142s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 396 tests in 334.794s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,206 edges, 0 unknown targets, 0 orphaned objects
# 2,766 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave26-habakkuk.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave26-habakkuk.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 71e940f7ae9995b8d53390a5fc181d398aef12c315ae57af8a6af7cdb823baca
# 37,212,160 bytes
```

The Python 3.14 run emitted the repository's known unclosed-SQLite
`ResourceWarning` messages; they did not change the successful test result.
