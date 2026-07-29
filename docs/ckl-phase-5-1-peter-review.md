# Phase 5 Wave 51 Review: 1 Peter

Last updated: 2026-07-28

## Review status

The 1 Peter correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`1-peter.json`](../framework/canonical_library/objects/books/1-peter.json)
- [`test_1_peter_record.py`](../tests/canonical_library/test_1_peter_record.py)
- [`hosea.json`](../framework/canonical_library/objects/books/hosea.json)

Hosea received one exact top-level alias to preserve its existing first-place
ranking for a question about 1 Peter's reuse of Hosea's people-and-mercy
language. No other canonical record required a retrieval safeguard.

## Corrections made

- Removed false completion metadata and generic General Epistle people,
  places, false-teaching, audience, persecution, authorship, date, and
  provenance claims.
- Rebuilt the record around 1 Peter 1:1-2:10; 2:11-4:11; and 4:12-5:14.
- Distinguished Peter the named sender from historical authorship proposals;
  elect sojourners across Pontus, Galatia, Cappadocia, Asia, and Bithynia;
  Silvanus and Mark; elders and younger people; enslaved household members,
  wives, husbands, rulers, and masters; outsiders; Noah and Sarah; and later
  interpreters.
- Qualified direct Petrine authorship, secretarial or collaborative models,
  pseudepigraphy, date, Babylon or Rome, destination route, audience
  ethnicity, relation to Paul, legal and social hostility, household practice,
  and historical reliability.
- Preserved disputes concerning election and diaspora, foreknowledge, new
  birth, ransom, imperishable seed, spiritual milk, living stones, royal
  priesthood, authorities, slavery, suffering and atonement, household
  submission, spirits in prison, Noah, baptism, proclamation to the dead,
  love covering sins, fiery trial, judgment, elders, the adversary, Silvanus,
  Babylon, Mark, and the closing kiss.
- Located 1 Peter within Jewish scriptural, Second Temple, Roman provincial,
  association, patronage, slavery, household, and apocalyptic contexts
  without turning comparanda into proof of dependence or a single audience.
- Distinguished biblical wording from lexical proposals, historical
  reconstruction, social-world comparison, doctrine, reception, pastoral
  application, and modern analogy.
- Added safeguards against antisemitism, supersessionism, xenophobia, ethnic
  nationalism, colonial settlement, slavery apologetics, trafficking, worker
  exploitation, coercive submission, domestic abuse, victim blaming,
  suffering glorification, authoritarian government and leadership,
  misogyny, anti-LGBTQ coercion, public shaming, forced conversion, religious
  violence, prosperity extraction, and ecological neglect.
- Added thirty-two sourced claims, forty-three current-taxonomy notes,
  twenty-seven sources, twenty-six URL-bearing external sources, eight
  high-precision top-level aliases plus retrieval metadata, twenty-four
  normalized Scripture anchors, ten Hebrew entries, thirty Greek entries, and
  eight verified graph relationships.

## Principal sources used

Primary controls include SBLGNT 1 Peter, the *Editio Critica Maior* Catholic
Letters, INTF/NTVMR, Papyrus 72, Codex Vaticanus, Codex Sinaiticus, NETS, the
Dead Sea Scrolls Digital Library, Josephus, and Philo. Independent controls
include Paul Achtemeier, John Elliott, Karen Jobes, Ramsey Michaels, Peter
Davids, Joel Green, David Horrell, David Balch, Jennifer Glancy, Pheme Perkins,
Everett Ferguson, John Kloppenborg, David deSilva, *The Jewish Annotated New
Testament*, BDAG, and LSJ.

A qualified reviewer must verify every locator, Greek form, textual reading,
translation, manuscript date and extent, Hebrew Bible and Septuagint
comparison, Jewish and Greco-Roman analogy, historical inference, genre
classification, and representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, provincial and personal distinctions,
placeholder removal, honest governance, current taxonomies, sources, lexical
data, graph links, safeguarding language, and SQLite parity. 1 Peter ranks
first for forty book-scoped questions.

Reviewers should verify the Greek text and variants; Papyrus 72, Vaticanus,
and Sinaiticus; every authorship and date proposal; the role of Silvanus;
Babylon and Rome; the provincial sequence; audience demographics; social and
legal hostility; relation to Pauline traditions; election and diaspora;
priesthood and people-of-God language; slavery and households; authorities
and freedom; Messiah's suffering and atonement; spirits in prison; Noah;
baptism; proclamation to the dead; fiery trial and judgment; elders and
younger people; adversary language; anti-supersessionist and trauma-informed
controls; and every evidence label, source locator, Scripture anchor, graph
edge, and retrieval phrase. Do not advance the record merely because
automated checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/1-peter.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_1_peter_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 145 + 146 + 168 + 137 = 596 tests
# One Hosea ranking regression was found; after the exact-alias safeguard,
# both affected 146- and 168-test batches pass. The unaffected batches pass.

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,308 edges, 0 unknown targets, 0 orphaned objects
# 2,856 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave51-1-peter-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave51-1-peter-final.sqlite
# Database schema 2; 620 objects
# fingerprint b822a4c64aa47bbd5d5c3445b3f556c23ee3fe3d2f5748ea6c50467f1e4714ab
# 50,397,184 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
