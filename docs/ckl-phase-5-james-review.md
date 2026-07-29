# Phase 5 Wave 50 Review: James

Last updated: 2026-07-28

## Review status

The James correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`james.json`](../framework/canonical_library/objects/books/james.json)
- [`test_james_record.py`](../tests/canonical_library/test_james_record.py)

No other canonical record required a retrieval safeguard in this wave.

## Corrections made

- Removed false completion metadata and generic General Epistle people,
  places, persecution, false-teaching, audience, authorship, date, and
  provenance claims.
- Rebuilt the record around James 1:1-27; 2:1-26; 3:1-18; 4:1-5:6; and
  5:7-20.
- Distinguished James the named sender from the disputed identification with
  James the brother of Jesus; the twelve tribes in diaspora; teachers,
  elders, laborers, merchants, rich and poor hearers, sick people, and
  wanderers; and Abraham, Rahab, Job, and Elijah.
- Qualified authorship, secretary or mediated-authorship proposals,
  pseudepigraphy, date, Jerusalem provenance, audience composition, diaspora,
  Jewish and gentile hearers, genre, Jesus-tradition parallels, Pauline
  comparison, social scenarios, and historical reliability.
- Preserved disputes concerning testing and temptation, perfection,
  double-mindedness, firstfruits, implanted word, religion, law of liberty,
  partiality, royal law, faith and works, justification, Abraham, Rahab,
  teachers, speech, wisdom, world friendship, James 4:5, judging, merchants,
  wealth, parousia, Job, oaths, oil, healing, confession, Elijah, and
  restoration.
- Located James within Jewish Torah, wisdom, prophetic, diaspora, and
  apocalyptic discourse without turning comparanda into proof of direct
  dependence or a single sectarian audience.
- Distinguished the biblical wording from lexical proposals, historical
  reconstruction, social-world comparison, doctrine, reception, pastoral
  application, and modern analogy.
- Added safeguards against antisemitism, supersessionism, class and caste
  contempt, poverty romanticization, worker exploitation, ableism, disability
  and illness shame, medical neglect, coercive confession, public shaming,
  spiritual abuse, authoritarian teaching, misogyny, anti-LGBTQ coercion,
  racism, nationalism, colonial mission, forced conversion, religious
  violence, prosperity extraction, and ecological neglect.
- Added thirty-two sourced claims, forty-two current-taxonomy notes,
  twenty-seven sources, twenty-six URL-bearing external sources, eight
  high-precision top-level aliases plus retrieval metadata, eighteen
  normalized Scripture anchors, ten Hebrew entries, twenty-nine Greek entries,
  and eight verified graph relationships.

## Principal sources used

Primary controls include SBLGNT James, the *Editio Critica Maior* Catholic
Letters, INTF/NTVMR, P20 and P23 catalogue records, Codex Vaticanus, Codex
Sinaiticus, NETS, the Dead Sea Scrolls Digital Library, Josephus, and Philo.
Independent controls include Dale Allison, Luke Timothy Johnson, Peter Davids,
Douglas Moo, Scot McKnight, Patrick Hartin, Martin Dibelius, Roy Bowen Ward,
Alicia Batten, John Kloppenborg, David deSilva, *The Jewish Annotated New
Testament*, Hector Avalos, BDAG, and LSJ.

A qualified reviewer must verify every locator, Greek form, textual reading,
translation, manuscript date and extent, Hebrew Bible and Septuagint
comparison, Jewish and Greco-Roman analogy, historical inference, genre
classification, and representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, placeholder removal, honest governance,
current taxonomies, sources, lexical data, graph links, safeguarding language,
and SQLite parity. James ranks first for forty book-scoped questions.

Reviewers should verify the Greek text and variants, especially James 4:5;
P20, P23, Vaticanus, and Sinaiticus; every authorship and date proposal;
Jerusalem provenance; diaspora and audience reconstructions; rhetorical
structure and genre; Jewish wisdom and Jesus-tradition parallels; law and
Torah; faith, works, justification, Abraham, Rahab, and Pauline comparison;
poverty, wealth, patronage, labor, and wages; teachers and speech; merchants;
parousia; Job and Elijah traditions; oaths; ancient oil and healing practice;
confession; restoration; anti-supersessionist and trauma-informed controls;
and every evidence label, source locator, Scripture anchor, graph edge, and
retrieval phrase. Do not advance the record merely because automated checks
pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/james.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_james_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 154 + 144 + 168 + 122 = 588 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,305 edges, 0 unknown targets, 0 orphaned objects
# 2,853 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave50-james-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave50-james-final.sqlite
# Database schema 2; 620 objects
# fingerprint 37d7af4e293d02706b04822862ea492bfd707136bc913f2e5f95fcaf3f35915b
# 50,020,352 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
