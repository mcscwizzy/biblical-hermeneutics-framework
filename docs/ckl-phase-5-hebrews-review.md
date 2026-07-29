# Phase 5 Wave 49 Review: Hebrews

Last updated: 2026-07-28

## Review status

The Hebrews correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`hebrews.json`](../framework/canonical_library/objects/books/hebrews.json)
- [`test_hebrews_record.py`](../tests/canonical_library/test_hebrews_record.py)

One concrete retrieval regression was corrected in
[`jeremiah.json`](../framework/canonical_library/objects/books/jeremiah.json):
an exact Jeremiah quotation-query alias now preserves the existing golden
result when the richer Hebrews record is present.

## Corrections made

- Removed false completion metadata and generic general-letter people, places,
  events, authorship, audience, persecution, and destination claims.
- Rebuilt the record around Hebrews 1:1-4:13; 4:14-10:39; 11:1-12:29; and
  13:1-25.
- Distinguished the anonymous speaker or writer, hearers, Jesus, God, Spirit,
  angels, Moses, Aaron, Melchizedek, Abraham, Sarah, the wilderness
  generation, priests, witnesses, prisoners, leaders, Timothy, Italian
  associates, and later proposed authors without inventing an author or
  complete community history.
- Qualified authorship, Pauline reception, date, provenance, destination,
  audience, language, genre, epistolary ending, temple inference, prior
  hardship, social pressure, persecution, and historical reliability.
- Preserved disputes concerning Son and wisdom traditions, angels,
  `oikoumenē`, rest, word, high-priest Christology, Melchizedek, maturity,
  impossibility warnings, oath, hope, `diathēkē`, sanctuary, sacrifice, blood,
  conscience, perfection, law, faith, witnesses, discipline, Esau, Sinai and
  Zion, kingdom, leaders, altar, outside the camp, Timothy, and Italy.
- Corrected manuscript orientation: P46 is an early substantial witness with
  lacunae; Sinaiticus preserves Hebrews after 2 Thessalonians; Alexandrinus
  also preserves the work. Manuscript sequence documents reception and does
  not prove Pauline authorship.
- Located Hebrews inside diverse Jewish scriptural and Second Temple worlds,
  and explicitly rejected antisemitism, supersessionism, anti-Judaism, and
  denigration of Torah, priesthood, sacrifice, temple worship, or living Jews.
- Added safeguards against apostasy terror, spiritual abuse, victim blaming,
  authoritarian leadership, clericalism, misogyny, anti-LGBTQ coercion,
  ableism, medical neglect, blood and violence glorification, nationalism,
  colonial mission, forced conversion, religious violence, prosperity
  extraction, and ecological neglect.
- Added thirty-two sourced claims, forty current-taxonomy notes, twenty-seven
  sources, twenty-five URL-bearing external sources, eight high-precision
  top-level aliases plus retrieval metadata, twenty normalized Scripture
  anchors, ten Hebrew entries, twenty-eight Greek entries, and eight verified
  graph relationships.

## Principal sources used

Primary controls include SBLGNT Hebrews, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46 at CSNTM](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[Codex Sinaiticus](https://www.codexsinaiticus.org/en/manuscript.aspx), and
the British Library catalogue for Codex Alexandrinus. Independent controls
include Harold Attridge, Craig Koester, Paul Ellingworth, Luke Timothy Johnson,
David deSilva, William Lane, David Moffitt, Eric Mason, George Guthrie,
Loren Stuckenbruck, David Aune, *The Jewish Annotated New Testament*, Pamela
Barmash, Jonathan Klawans, Pamela Eisenbaum, Elisabeth Schüssler Fiorenza,
Mitzi J. Smith, Warren Carter, BDAG, and related historical controls.

A qualified reviewer must verify every locator, textual reading, translation,
manuscript date, Jewish and Greco-Roman comparison, historical inference,
genre classification, and representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, placeholder removal, honest governance,
current taxonomies, sources, lexical data, graph links, safeguarding language,
and SQLite parity. Hebrews ranks first for forty book-scoped questions.

Reviewers should verify the Greek text and variants; P46 and major codices;
anonymous authorship and every named proposal; date and destination; the
Italian notice; audience and hardship; discourse structure and genre; every
quotation and Septuagintal form; Second Temple angel, Melchizedek, priestly,
sanctuary, covenant, sacrifice, and wisdom comparanda; rest; warning passages;
atonement; law and covenant; anti-supersessionist controls; faith witnesses;
women and unnamed sufferers; discipline; leadership; trauma-informed
reception; and every evidence label, source locator, Scripture anchor, graph
edge, and retrieval phrase. Do not advance the record merely because automated
checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/hebrews.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_hebrews_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

python3 -m unittest \
  tests.canonical_library.test_jeremiah_record \
  tests.canonical_library.test_hebrews_record
# 16 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 159 + 139 + 168 + 114 = 580 tests: OK after the affected 139-test
# batch was rerun following the Jeremiah retrieval safeguard

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,302 edges, 0 unknown targets, 0 orphaned objects
# 2,850 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave49-hebrews-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave49-hebrews-final.sqlite
# Database schema 2; 620 objects
# fingerprint 98d7d1f11651848c7a553708e9ff06c60fea1f1d26fc639ca0853dfcc012220c
# 49,725,440 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
