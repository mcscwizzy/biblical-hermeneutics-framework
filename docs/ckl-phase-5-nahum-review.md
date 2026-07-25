# Phase 5 Wave 25 Review: Nahum

Last updated: 2026-07-25

## Review status

The Nahum correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`nahum.json`](../framework/canonical_library/objects/books/nahum.json)
- [`test_nahum_record.py`](../tests/canonical_library/test_nahum_record.py)

## Corrections made

- Removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, and Jonah values, corpus-wide dates and setting, internal-only
  sourcing, legacy evidence labels, and false `complete` and review metadata.
- Rebuilt the record around Nahum 1:1; 1:2–8; 1:9–15; 2:1–13; 3:1–7;
  3:8–13; and 3:14–19, preserving Masoretic/common-English numbering and
  uncertainty about speakers, addressees, sequence, quotation boundaries, and
  seams.
- Distinguished Nahum the Elkoshite, framing and prophetic voices, YHWH's
  direct speech and reported action, Judah and Jacob, the good-news messenger,
  the wicked counselor or Belial figure, Nineveh as city and feminized
  personification, the Assyrian king, scatterer, soldiers, captives, children,
  officials, merchants, scribes, shepherds, nobles, peoples, nations, lions,
  locusts, and later interpreters.
- Distinguished superscription, burden or oracle, vision-book title,
  divine-warrior hymn and theophany, proposed partial acrostic, judgment and
  salvation oracle, messenger announcement, siege and battle poem, lion
  fable, taunt, woe, city lament, gendered personification, rhetorical
  comparison, funeral address, dirge, and international response.
- Qualified Elkosh, the 663–612 BCE historical window, Nineveh's development
  under Sennacherib, Esarhaddon's and Ashurbanipal's reigns, the sack of
  Thebes, Assyrian civil conflict and contraction, the Babylonian-Median
  campaign, and Nineveh's fall in 612 BCE.
- Added bounded use of Nineveh's walls, gates, palaces, roads, canals,
  reliefs, royal inscriptions, trade, tribute, deportation, lion imagery, the
  Ashurbanipal inscriptions, and Babylonian Chronicle BM 21901. Royal and
  Babylonian sources are identified as perspective-bearing witnesses rather
  than neutral verification of every poetic detail.
- Preserved uncertainty concerning the title, acrostic, chapter 1 order,
  wicked plotter, Belial, numbering, messenger, scatterer, battle vocabulary,
  river gates, palace and pool, literal-flood theory, lion symbolism,
  translation and ethics of 3:4–7, Thebes' allies, Put, sorcery, locust and
  office terms, shepherds, nobles, king, wound, authorship, unity, redaction,
  date, purpose, and shaping within the Twelve.
- Added Masoretic Nahum, Old Greek Naoum, CATSS, NETS, BHS, 4Q82, 4Q169
  Pesher Nahum, Hebrew Bible and New Testament comparanda, critical
  commentaries, womanist and feminist work, Qumran research, museum records,
  royal inscriptions, and reception resources.
- Distinguished biblical text, historical reconstruction, ancient royal
  propaganda, archaeological comparison, textual witness, translation,
  pesher, verbal parallel, canonical contrast, later reception, christological
  trajectory, postcolonial analogy, and pastoral application.
- Added safeguards concerning antisemitism, supersessionism, anti-Iraqi and
  anti-Middle Eastern racism, modern Assyrian ethnic proxies, collective
  guilt, survivor and disaster blame, sexualized humiliation, rape culture,
  misogyny, sex-worker stigma, child-killing imagery, trauma voyeurism,
  siege, torture, plunder, genocide, ethnic cleansing, displacement,
  collective punishment, revenge, vigilantism, nationalism, colonialism,
  ecological destruction, war propaganda, and partisan enemy-mapping.
- Added twenty-seven sourced claims, forty-six current-taxonomy interpretive
  notes, twenty-five source records, twenty-two URL-bearing external sources,
  eight graph relationships, fifteen Scripture anchors, twenty Hebrew entries,
  eight Greek entries, section statuses, knowledge layers, a hermeneutical
  lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `nahum-superscription` | `textually_explicit` | `lexical_uncertainty` |
| `nahum-elkosh` | `insufficient_evidence` | `historical_uncertainty` |
| `nahum-date` | `probable` | `chronological_uncertainty` |
| `nahum-composition` | `strong_consensus` | `major_scholarly_disagreement` |
| `nahum-acrostic` | `disputed` | `major_scholarly_disagreement` |
| `nahum-divine-character` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-refuge` | `textually_explicit` | `minor_scholarly_disagreement` |
| `nahum-addressees` | `strong_consensus` | `major_scholarly_disagreement` |
| `nahum-numbering` | `textually_explicit` | `not_disputed` |
| `nahum-good-news` | `textually_explicit` | `minor_scholarly_disagreement` |
| `nahum-scatterer` | `probable` | `historical_uncertainty` |
| `nahum-siege-poem` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-water` | `plausible` | `archaeological_uncertainty` |
| `nahum-lions` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-bloody-city` | `textually_explicit` | `not_disputed` |
| `nahum-gendered-rhetoric` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-thebes` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-children` | `textually_explicit` | `not_disputed` |
| `nahum-locusts` | `probable` | `lexical_uncertainty` |
| `nahum-failed-leaders` | `textually_explicit` | `lexical_uncertainty` |
| `nahum-wound` | `textually_explicit` | `minor_scholarly_disagreement` |
| `nahum-chronicle` | `strong_consensus` | `not_disputed` |
| `nahum-assyrian-sources` | `strong_consensus` | `not_disputed` |
| `nahum-textual-witnesses` | `strong_consensus` | `textual_variant` |
| `nahum-pesher` | `strong_consensus` | `historical_uncertainty` |
| `nahum-new-testament` | `strong_consensus` | `minor_scholarly_disagreement` |
| `nahum-ethical-reception` | `strong_consensus` | `not_disputed` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and mappings are in
[`nahum.json`](../framework/canonical_library/objects/books/nahum.json).

## Principal sources used

Primary and material witnesses include Masoretic Nahum, Old Greek Naoum,
4Q82, 4Q169, Hebrew Bible and New Testament comparanda, the Fall of Nineveh
Chronicle, Ashurbanipal's royal inscriptions, and Nineveh palace art.
Independent research sources include:

- Bo H. Lim, “Nahum”:
  <https://academic.oup.com/edited-volume/38566/chapter-abstract/334373533>.
- Duane L. Christensen, *Nahum*:
  <https://yalebooks.yale.edu/book/9780300144796/nahum/>.
- Julia M. O'Brien, *Nahum*:
  <https://www.sbl-site.org/wp-content/uploads/2025/01/OBrienNahum.pdf>.
- Wilda C. M. Gafney, *Nahum, Habakkuk, Zephaniah*:
  <https://litpress.org/Products/E8187/Wisdom-Commentary-Nahum-Habakkuk-Zephaniah>.
- Daniel C. Timmer, *The Theology of the Books of Nahum, Habakkuk, and
  Zephaniah*:
  <https://www.cambridge.org/core/books/theology-of-the-books-of-nahum-habakkuk-and-zephaniah/4FD8871C1A8A5EA40AF14C38DC153391>.
- CATSS, Old Greek Nahum:
  <https://ccat.sas.upenn.edu/gopher/text/religion/biblical/lxxvar/4Prophets/MinorProphets/07Nahum.html>.
- NETS, *The Twelve Prophets*:
  <https://ccat.sas.upenn.edu/nets/edition/32-twelve-nets.pdf>.
- Israel Antiquities Authority records for
  [4Q82](https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q82-1)
  and
  [4Q169](https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q169-1).
- British Museum records for
  [BM 21901](https://www.britishmuseum.org/collection/object/W_1896-0409-6)
  and the
  [Assyrian lion-hunt galleries](https://www.britishmuseum.org/collection/galleries/assyria-lion-hunts).
- *The Royal Inscriptions of Ashurbanipal*:
  <https://oracc.museum.upenn.edu/rinap/downloads/0RINAP5_2_final.pdf>.
- Metropolitan Museum of Art, “Egypt in the Third Intermediate Period”:
  <https://www.metmuseum.org/essays/egypt-in-the-third-intermediate-period-1070-712-b-c>.

Publisher, university, archive, scholarly-organization, and museum pages
establish bibliographic identity, material witness, or a bounded research
claim. A qualified reviewer must still check every locator, translation,
textual reading, archaeological inference, and scholarly characterization.

## Retrieval coverage

The regression requires Nahum to rank first for questions about:

- Nahum, Elkosh, date, authorship, unity, oracle title, and the acrostic;
- Exodus 34, divine jealousy, vengeance, patience, power, goodness, and
  refuge;
- the wicked counselor, Belial, numbering, good-news messenger, and Isaiah;
- the scatterer, shields, garments, chariots, spears, river gates, palace,
  pool, flood theory, plunder, and lion den;
- bloody city, prostitution, sorcery, exposure, sex workers, gendered
  violence, and divine speech;
- Thebes, No-amon, 663 BCE, Egypt, Cush, Put, Libya, captives, and children;
- locusts, merchants, scribes, guards, commanders, shepherds, nobles, the
  Assyrian king, irreparable wound, and nations' applause;
- BM 21901, Nineveh in 612 BCE, Assyrian inscriptions, reliefs, and
  archaeology;
- Old Greek Naoum, 4Q82, 4Q169, Jonah, Romans, Isaiah, and Revelation; and
- antisemitism, ethnic proxies, anti-Iraqi racism, supersessionism, revenge,
  war propaganda, genocide, collective punishment, trauma, and modern
  political mapping.

All pass with the existing retrieval implementation. Two exact aliases
disambiguate deliberately cross-book Exodus 34 and Jonah/Nahum questions.

## Human review checklist

Verify:

- every Hebrew, Old Greek, BHS, CATSS, NETS, 4Q82, 4Q169, versional,
  numbering, translation, and textual-variant statement;
- the title, *massa*, *hazon*, Nahum, Elkosh, acrostic sequence, poem order,
  speakers, addressees, direct speech, pronouns, imperatives, and seams;
- the 663 and 612 anchors, Sennacherib, Esarhaddon, Ashurbanipal, Thebes,
  Assyrian civil conflict, Babylonians, Medes, and every date range;
- Nineveh's geography, walls, gates, canals, river, palace, roads, chariots,
  trade, tribute, deportation, siege, plunder, fire, and flood claims;
- BM 21901, each royal inscription and relief, museum metadata, ideological
  qualification, and claimed relationship to Nahum;
- the wicked counselor, Belial, good-news messenger, scatterer, battle
  vocabulary, pool, lions, bloody city, sorcery, exposure, Thebes' allies,
  children, locust terms, offices, shepherds, nobles, king, wound, and
  applause;
- every proposed relationship with Exodus, Psalms, Isaiah, Jonah, Micah,
  Zephaniah, Jeremiah, Ezekiel, Romans, Revelation, and the Twelve;
- every distinction among historical referent, poetry, personification,
  metaphor, textual witness, pesher, canonical trajectory, typology,
  ecclesial application, and modern analogy;
- early Jewish, Christian, womanist, feminist, postcolonial, trauma-aware,
  ecological, artistic, liturgical, and political reception; and
- every safeguard, source author, title, date, URL, locator, support target,
  claim rationale, certainty label, dispute label, graph relation, and
  application.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

Pre-edit baseline:

```text
python3 -m unittest tests.canonical_library.test_nahum_record
# 8 tests; 25 expected failures across seven content/retrieval groups
# SQLite parity alone passed
```

Final focused verification:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/nahum.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_nahum_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 17.853s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 388 tests in 320.569s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,203 edges, 0 unknown targets, 0 orphaned objects
# 2,763 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave25-nahum.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave25-nahum.sqlite
# 620 objects; schema 2; fingerprint
# b18535bd7ff7307361fe9a6b3528499be722fc8b9fd552390aac2eeb166c1572
# 36,687,872 bytes
```
