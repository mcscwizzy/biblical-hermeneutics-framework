# Phase 5 Wave 39 Review: Galatians

Last updated: 2026-07-28

## Review status

The Galatians correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`galatians.json`](../framework/canonical_library/objects/books/galatians.json)
- [`test_galatians_record.py`](../tests/canonical_library/test_galatians_record.py)

## Corrections made

- Removed the inherited Pauline-letter placeholder: Timothy as a key person;
  Rome, Corinth, and Ephesus as unsupported places; generic mission,
  church-formation, and pastoral-instruction events; broad world-wide
  audience and authorship templates; incorrect ancient Near Eastern
  applicability; and false completion metadata.
- Rebuilt the record around Galatians 1:1-2:21; 3:1-4:31; 5:1-6:10; and
  6:11-18.
- Distinguished Paul as named sender and dominant voice; the plural Galatian
  assemblies; Barnabas, Titus, Cephas, James, John, and the Jerusalem poor;
  unnamed agitators; Abraham, Sarah, Hagar, Isaac, the scriptural voice, the
  Messiah, the Spirit, and later interpreters.
- Qualified Pauline authorship and possible scribal assistance; date and
  provenance; North- and South-Galatian destination theories; audience
  ethnicity; opponent reconstruction; the Jerusalem visits; relation to Acts;
  Titus and circumcision; the Antioch confrontation; and the rhetorical use
  of autobiography.
- Indexed prescript, curse, revelation and call, autobiography, forensic and
  deliberative rhetoric, scriptural quotation, diatribe, exemplum, allegory,
  irony, household language, vice and virtue catalog, exhortation, warning,
  autograph, and benediction.
- Addressed justification, `pistis Christou`, works of Torah, Abraham,
  promise, curse, seed, Torah's addition, angels, mediator, pedagogue,
  baptism, adoption, elemental powers, bodily weakness, eyes, Hagar and
  Sarah, freedom, circumcision, flesh, Spirit, love, fruit, restoration,
  burdens, teacher support, sowing, cross, new creation, Israel of God,
  Paul's marks, and grace.
- Added P46, P51, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi,
  Claromontanus, NTVMR, Septuagint, Galatian and Anatolian inscription,
  geography, route, ethnicity, circumcision, slavery, household, rhetoric,
  reception, queer, intersex, and disability controls.
- Added safeguards against antisemitism, supersessionism, anti-Jewish Torah
  caricature, ethnic contempt, coercive circumcision or anti-circumcision,
  anti-LGBTQ coercion, misogyny, gender erasure, slavery apologetics, worker
  exploitation, public shaming, authoritarian leadership, spiritual abuse,
  unsafe reconciliation, financial extraction, prosperity teaching,
  disability and mental-health stigma, medical neglect, trauma
  glorification, colonial mission, forced conversion, religious violence,
  nationalism, conspiracy theories, partisan capture, and ecological
  neglect.
- Added thirty-six sourced claims, sixty current-taxonomy interpretive notes,
  thirty sources, twenty-nine URL-bearing external sources, three
  high-precision top-level aliases plus retrieval metadata, sixteen
  normalized Scripture anchors, ten Hebrew entries, twenty Greek entries,
  and eight verified graph relationships.

## Principal sources used

Primary textual and material controls include SBLGNT Galatians, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[P51](https://manuscripts.csntm.org/manuscript/View/GA_P51),
[Codex Sinaiticus](https://www.codexsinaiticus.org/en/),
[Codex Vaticanus](https://digi.vatlib.it/view/MSS_Vat.gr.1209),
[Codex Alexandrinus](https://www.bl.uk/manuscripts/FullDisplay.aspx?ref=Royal_MS_1_D_VIII),
[Codex Ephraemi](https://gallica.bnf.fr/ark:/12148/btv1b8470433r),
[Codex Claromontanus](https://gallica.bnf.fr/ark:/12148/btv1b84683111),
[PHI Greek Inscriptions](https://inscriptions.packhum.org/), and
[Pleiades](https://pleiades.stoa.org/). Independent research includes:

- J. Louis Martyn, *Galatians*; John M. G. Barclay,
  *Paul: Crisis in Galatia* and *Paul and the Gift*; Bruce W. Longenecker on
  Galatians; and Beverly Roberts Gaventa on Galatians and Romans.
- Matthew Thiessen, *Paul and the Gentile Problem*; Paula Fredriksen,
  *Paul: The Pagans' Apostle*; and Mark D. Nanos,
  *The Irony of Galatians*.
- Joseph A. Marchal on intersex, eunuch, and circumcision interpretation;
  Isaac T. Soon on disability and Pauline bodies; Matthijs den Dulk on ethnic
  stereotyping; and John Riches on reception history.
- BDAG and LSJ as lexical controls, used without allowing a lexicon entry to
  settle a contextual dispute by itself.

Publisher, university, manuscript-project, archive, museum, and scholarly
organization pages establish bibliographic identity or bounded evidence. A
qualified reviewer must verify every locator, Greek and scriptural reading,
translation, manuscript date, historical inference, and characterization of
a scholarly position.

## Retrieval and regression coverage

The Galatians-specific test was created before the record changed. Its
baseline ran eight test methods and recorded twenty-eight individual failures
across structure, composition, governance, sources, claims, safeguards, and
retrieval; SQLite parity was the only passing method.

The rebuilt record ranks first for forty-one explicitly book-scoped Galatians
questions. Two broad queries initially ranked the existing Acts and adoption
records first, so the fixture now asks questions tied to Galatians'
autobiographical Jerusalem chronology and the heir-guardian-adoption sequence
of Galatians 4. A generic baptism-and-new-creation golden query also exposed
excessive general prominence; restoring the record's established importance
score preserved the expected theme ranking while all book-scoped questions
continued to pass. No retrieval-code changes or neighboring-record edits were
needed.

## Human review checklist

Verify:

- SBLGNT wording; every Hebrew Bible and Septuagint comparison; P46, P51,
  Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus, early
  versions, and every cited textual variant;
- Pauline authorship, possible scribal assistance, integrity, date,
  provenance, North- and South-Galatian destinations, audience ethnicity,
  opponents, purpose, Jerusalem visits, Titus, Antioch, and relation to Acts
  and other Pauline letters;
- every reconstruction using Galatian and Anatolian geography, inscriptions,
  archaeology, households, patronage, rhetoric, enslavement, circumcision,
  ethnicity, philosophy, social status, and travel;
- `euangelion`, `apokalypsis`, `dikaioo`, `pistis Christou`, `erga nomou`,
  `epangelia`, `sperma`, `katara`, `nomos`, `paidagogos`, `huiothesia`,
  `stoicheia tou kosmou`, `peritome`, `eleutheria`, `sarx`, `pneuma`,
  `agape`, `karpos tou pneumatos`, `kaine ktisis`, and `stigmata`;
- each certainty and dispute label, rationale, source locator, support target,
  Scripture anchor, graph edge, lexical entry, and retrieval phrase;
- every treatment of Jews and Judaism, Torah, gentiles, circumcision, bodily
  difference, sex and gender, enslavement, freedom, authority, polemic,
  suffering, illness, disability, discipline, money, and leadership; and
- every safeguarding, antisemitism, sexuality, gender, slavery, disability,
  mental-health, medical, economic, political, ecological, and noncoercion
  boundary.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/galatians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_galatians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 192 + 151 + 157 = 500 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,274 edges, 0 unknown targets, 0 orphaned objects
# 2,828 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave39-galatians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave39-galatians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b38c3543f0b98688e29da6d25e18804b8afe62d933005609059a36b9b314a859
# 45,240,320 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
