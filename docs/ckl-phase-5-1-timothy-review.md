# Phase 5 Wave 45 Review: 1 Timothy

Last updated: 2026-07-28

## Review status

The 1 Timothy correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`1-timothy.json`](../framework/canonical_library/objects/books/1-timothy.json)
- [`test_1_timothy_record.py`](../tests/canonical_library/test_1_timothy_record.py)

## Corrections made

- Removed Titus, Rome, Corinth, generic events, inaccurate ancient-context
  claims, unsupported completion metadata, and legacy certainty labels
  inherited from the Pauline placeholder.
- Rebuilt the record around 1 Timothy 1:1-20; 2:1-3:16; 4:1-5:2; 5:3-6:2;
  and 6:3-21.
- Distinguished Paul and Timothy as named sender and recipient; possible
  secretary or Pauline-school composition; teachers of different doctrine;
  women and men; overseers, deacons, elders, widows, enslaved and free people,
  wealthy members, households, named figures, and later interpreters.
- Qualified authorship, date, secretary, provenance, destination, audience,
  opponents, church-order development, integrity, purpose, Acts chronology,
  and relation to 2 Timothy and Titus.
- Preserved disputes concerning myths and genealogies, law, `arsenokoitai`,
  dress, teaching, `authentein`, Adam and Eve, childbearing, overseers,
  deacons, women in 3:11, confession and its textual variant, asceticism,
  bodily training, gifts, widow enrollment, elder pay and discipline, slavery,
  wealth, and falsely named knowledge.
- Added safeguards against antisemitism, supersessionism, homophobia,
  misogyny, silencing women, authoritarian office, clericalism, elder
  impunity, victim blaming, unsafe accusation procedures, slavery apologetics,
  worker exploitation, poverty and disability shame, medical neglect,
  coerced asceticism, prosperity extraction, nationalism, militarism,
  colonial mission, forced conversion, religious violence, public shaming,
  and ecological neglect.
- Added thirty-three sourced claims, forty-three current-taxonomy notes,
  twenty-five sources, twenty-three URL-bearing external sources, six
  top-level aliases plus retrieval metadata, nineteen normalized Scripture
  anchors, ten Hebrew entries, twenty-three Greek entries, and eight graph
  links.

## Principal sources used

Primary controls include SBLGNT 1 Timothy, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P133 / P.Oxy. 81.5259](https://portal.sds.ox.ac.uk/articles/online_resource/P_Oxy_LXXXI_5259_1_Timothy_3_13-4_8/21185737),
[Codex Sinaiticus](https://codexsinaiticus.org/en/manuscript.aspx?book=47&lid=en&side=r&zoomslider=0),
and digitized Vaticanus and Alexandrinus controls. Independent controls
include I. Howard Marshall, Philip H. Towner, Luke Timothy Johnson, Raymond F.
Collins, Annette Bourland Huizenga, Cynthia Long Westfall, Bruce W. Winter,
Carolyn Osiek, Margaret Y. MacDonald, Jennifer A. Glancy, Kathy Ehrensperger,
Paul Trebilco, David E. Aune, Bart D. Ehrman, *The Jewish Annotated New
Testament*, and BDAG.

A qualified reviewer must verify every locator, textual reading, translation,
manuscript date, historical inference, archaeological characterization, and
representation of a scholarly position.

## Retrieval and regression coverage

The fixture checks factual structure, placeholder removal, honest governance,
current taxonomies, sources, lexical data, book-scoped retrieval, safeguards,
and SQLite parity. 1 Timothy ranks first for forty book-scoped questions,
including the broad comparison with Acts, Titus, and 2 Timothy. Broad topic
queries for Paul, Timothy, Ephesus, elders, deacons, Scripture, faith, and
grace continue to prefer focused topic records; the fixture tests the letter's
specific evidence clusters instead.

## Human review checklist

Verify:

- Greek, Hebrew Bible, Septuagint, papyrus, codex, versional, and textual
  claims, especially the opening of 3:16;
- authorship, secretary, Pauline-school models, date, provenance, destination,
  audience, opponents, Acts chronology, integrity, purpose, and relation to
  the other Pastoral Epistles;
- Ephesian archaeology and inscriptions, Roman Asia, households, patronage,
  associations, education, gender, widows, offices, slavery, wealth,
  pseudepigraphy, and early reception;
- all twenty-three Greek entries, especially `heterodidaskaleō`, `mythos`,
  `genealogia`, `arsenokoitēs`, `hēsychia`, `authenteō`, `teknogonia`,
  `episkopos`, `diakonos`, `eusebeia`, `anagnōsis`, `charisma`,
  `presbyteros`, `doulos`, `autarkeia`, `philargyria`, `parathēkē`, and
  `gnōsis`;
- gender, leadership, widow, elder-accusation, health, slavery, labor, wealth,
  and safeguarding treatments with direct input from affected readers; and
- every certainty label, source locator, Scripture anchor, graph edge, and
  retrieval phrase.

Do not advance the record merely because automated checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/1-timothy.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_1_timothy_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 203 + 140 + 37 + 168 = 548 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,290 edges, 0 unknown targets, 0 orphaned objects
# 2,842 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave45-1-timothy-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave45-1-timothy-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 051832232271440b1e7ecf7f2abfcdf20918c940ce012c4fcb88e68b49dc8d18
# 47,869,952 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
