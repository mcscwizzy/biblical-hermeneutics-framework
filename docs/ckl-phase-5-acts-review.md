# Phase 5 Wave 35 Review: Acts

Last updated: 2026-07-25

## Review status

The Acts correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`acts.json`](../framework/canonical_library/objects/books/acts.json)
- [`test_acts_record.py`](../tests/canonical_library/test_acts_record.py)

## Corrections made

- Removed the inherited Gospel template: generic ministry, crucifixion, and
  resurrection events; Synoptic disputes; overconfident Lukan authorship;
  incorrect ancient Near Eastern applicability; and false completion
  metadata.
- Rebuilt the record around Acts 1:1-2:47; 3:1-5:42; 6:1-8:40; 9:1-12:25;
  13:1-15:35; 15:36-19:20; 19:21-21:16; 21:17-26:32; and 27:1-28:31.
- Distinguished narrator, implied author, Theophilus, risen Jesus, Spirit,
  angels, Scripture, the Eleven, women disciples, Jesus' family, Peter,
  Stephen, Philip, the Seven, Jewish and Samaritan groups, the Ethiopian
  official, Paul and companions, named women, households, workers, enslaved
  people, officials, prisoners, soldiers, sailors, islanders, and later
  interpreters.
- Qualified internal anonymity, later attribution to Luke, common-authorship
  and coordinated-publication models, the `we` passages, sources, speeches,
  date, provenance, audience, historical reliability, Roman citizenship, and
  the open ending.
- Indexed historiographic narrative, biography and institutional-origin
  comparisons, summaries, calls, visions, signs, healings, exorcisms,
  speeches, councils, trials, prison scenes, journeys, riots, voyage,
  shipwreck, hospitality, and open ending.
- Addressed restoration, ascension, Matthias, Pentecost languages, Greek
  Joel, communal property, Ananias and Sapphira, Gamaliel, the Seven,
  Stephen, Samaria, the Ethiopian official, Paul's three call accounts,
  Galatians, Cornelius, Herod and Josephus, Antioch, Bar-Jesus, the Jerusalem
  council, decree variants, women leaders, households, exorcism, Areopagus,
  Gallio, Ephesus, the collection, Agabus, Torah purification, trials,
  Agrippa and Bernice, voyage, snakebite, Malta, Rome, and Paul's unreported
  fate.
- Added P45, P53, P74, Sinaiticus, Vaticanus, Bezae, NTVMR, Septuagint,
  inscriptions, archaeology, Josephus, Roman-law, and nautical controls.
- Added safeguards against antisemitism, supersessionism, collective Jewish
  guilt, anti-Samaritan and anti-African stereotypes, racializing the
  Ethiopian official, imperial and anti-Roman racism, colonial mission,
  forced conversion, religious violence, Christian nationalism,
  authoritarian unity, clerical and financial coercion, poverty
  romanticization, misogyny, anti-LGBTQ coercion, slavery and worker
  exploitation, disability and mental-health stigma, dangerous exorcism,
  medical neglect, snake handling, victim blame, trauma glorification,
  prison abuse, anti-intellectualism, conspiracy claims, and ecological harm.
- Added forty-two sourced claims, eighty-one current-taxonomy interpretive
  notes, thirty-seven sources, thirty-five URL-bearing external sources,
  sixty-two aliases, twenty-one normalized Scripture anchors, sixteen Hebrew
  entries, thirty-two Greek entries, and nine verified relationships.

## Principal sources used

Primary textual and material controls include SBLGNT Acts, NETS, P45, P53,
P74, Codex Sinaiticus, Codex Vaticanus, Codex Bezae, and INTF/NTVMR.
Independent research includes:

- Matthew L. Skinner,
  [“The Acts of the Apostles”](https://doi.org/10.1017/9781108888882.015),
  and A. E. Harvey,
  [“The Acts of the Apostles”](https://doi.org/10.1017/CBO9780511811371.009).
- Daniel Marguerat,
  [*The First Christian Historian*](https://doi.org/10.1017/CBO9780511488061),
  and Charles H. Talbert,
  [“The Acts of the Apostles: Monograph or Bios?”](https://doi.org/10.1017/CBO9780511555176.004).
- Loveday C. A. Alexander, *Acts in Its Ancient Literary Context*; Robert C.
  Tannehill, *The Narrative Unity of Luke-Acts*; Patricia Walters,
  *The Assumed Authorial Unity of Luke and Acts*; and William Sanger Campbell,
  *The We Passages in the Acts of the Apostles*.
- Craig S. Keener, *Acts: An Exegetical Commentary*; Jacob Jervell,
  *The Theology of the Acts of the Apostles*; and Drew W. Billings,
  [*Acts of the Apostles and the Rhetoric of Roman Imperialism*](https://doi.org/10.1017/9781316946251).
- Amy-Jill Levine, editor, *A Feminist Companion to the Acts of the
  Apostles*; F. Scott Spencer on the Ethiopian official; Luke Timothy Johnson
  on possessions; and research on anti-Judaism and supersessionism.
- Josephus, the Gallio inscription, Ancient Corinth resources, UNESCO
  Ephesus, Heritage Malta, Roman-law research, and ancient-seafaring research.

Publisher, university, museum, manuscript-project, and scholarly-organization
pages establish bibliographic identity or bounded evidence. A qualified
reviewer must verify every locator, reading, translation, date, historical
inference, and characterization of a scholarly position.

## Retrieval and regression coverage

The Acts-specific test was created before the record changed. Its baseline ran
eight tests and recorded fifty-one expected failures across structure,
authorship, governance, sources, evidence, safeguards, and retrieval; SQLite
parity was the only passing area.

The rebuilt record now ranks first for fifty-nine Acts-specific questions.
An existing Amos-specific query initially tied with Acts after enrichment;
redundant top-level Acts 15 anchors were removed while the council remained
fully represented in structure, claims, notes, and sources. Acts and Amos then
passed together, and the complete 468-test CKL suite passed without retrieval
code changes or edits to the Amos record.

## Human review checklist

Verify:

- SBLGNT wording; Greek scriptural quotations; P45, P53, P74, Sinaiticus,
  Vaticanus, Bezae, Old Latin, Syriac, Coptic, and other versions;
- anonymity, later Lukan attribution, Luke-Acts authorship and publication,
  `we` passages, speeches, sources, date, provenance, audience, purpose,
  historical reliability, Roman citizenship, and the ending;
- every comparison with Pauline letters, Josephus, inscriptions, archaeology,
  Roman law, civic institutions, and ancient seafaring;
- every account of Jewish groups, Samaritans, the Ethiopian official, Roman
  actors, women, households, enslaved people, workers, disabled and sick
  people, people described through spirits, prisoners, and islanders;
- each certainty and dispute label, claim rationale, source locator, support
  target, graph edge, lexical entry, and retrieval alias;
- baptism, Spirit reception, ecclesiology, mission, wealth, Torah, temple,
  circumcision, food, resurrection, empire, suffering, and providence; and
- every antisemitism, racism, coercion, safeguarding, disability, medical,
  gender, sexuality, economic, trauma, prison, political, and ecological
  safeguard.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/acts.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_acts_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 31.394s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 160 + 154 + 154 = 468 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,259 edges, 0 unknown targets, 0 orphaned objects
# 2,815 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave35-acts-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave35-acts-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 059064f7668d71e5cdbd12504a28ad5c2a65d01f1faf862f90548901f30752dc
# 42,840,064 bytes
```

Python 3.14 emitted the repository's known unclosed-SQLite `ResourceWarning`
messages; they did not change successful test results.
