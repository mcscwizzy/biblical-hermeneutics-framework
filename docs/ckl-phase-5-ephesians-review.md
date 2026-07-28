# Phase 5 Wave 40 Review: Ephesians

Last updated: 2026-07-28

## Review status

The Ephesians correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`ephesians.json`](../framework/canonical_library/objects/books/ephesians.json)
- [`test_ephesians_record.py`](../tests/canonical_library/test_ephesians_record.py)

## Corrections made

- Removed the inherited Pauline placeholder: Timothy and Titus as principal
  people; Rome and Corinth as asserted places; generic mission,
  church-formation, and pastoral-instruction events; an inaccurate Second
  Temple audience claim; unsupported completion metadata; and legacy
  certainty labels.
- Rebuilt the record around Ephesians 1:1–2:10; 2:11–3:21; 4:1–5:20;
  5:21–6:9; and 6:10–24.
- Distinguished the named Pauline voice from modern authorship conclusions;
  Tychicus; gentile and Jewish participants; apostles, prophets, evangelists,
  pastors, and teachers; wives, husbands, children, fathers or parents,
  enslaved people, masters, the scriptural voice, rulers and powers, the
  Messiah, the Spirit, and later interpreters.
- Qualified direct Pauline, secretary-mediated, associate, and Pauline-school
  proposals; early-60s and roughly 70–90 CE dates; provenance and imprisonment
  theories; omission of “in Ephesus”; circular and Laodicean proposals;
  audience reconstruction; and the literary relationship to Colossians.
- Indexed blessing, prayer, doxology, election, adoption, inheritance,
  sealing, cosmic headship, grace, faith, works, reconciliation, one new
  humanity, household, temple, mystery, unity, gifts, old and new humanity,
  Spirit-shaped worship, household code, armor, prayer, Tychicus, and
  benediction.
- Preserved disputes concerning predestination; the grammar of Ephesians 2:8;
  flesh; dividing wall; commandments and Torah; apostles and prophets;
  descent; ministry gifts; head and body; Ephesians 5:14; submission,
  marriage, parenting, slavery, rulers and powers, and spiritual warfare.
- Added manuscript, Septuagint, Ephesian archaeology, Artemis, household,
  enslavement, lexical, social-historical, literary, theological, and
  reception controls.
- Added safeguards against antisemitism, supersessionism, predestination
  fatalism, clericalism, marital rape and coercive control, child abuse,
  anti-LGBTQ coercion, sexual abuse, slavery apologetics, worker exploitation,
  ableism, mental-health stigma, medical neglect, dangerous exorcism,
  militarism, nationalism, conspiracy theories, partisan capture, colonial
  mission, forced conversion, financial extraction, public shaming, trauma
  glorification, and ecological neglect.
- Added twenty-eight sourced claims, forty-six current-taxonomy interpretive
  notes, twenty-four URL-bearing sources, three high-precision top-level
  aliases plus retrieval metadata, sixteen normalized Scripture anchors, ten
  Hebrew entries, twenty Greek entries, and eight verified graph
  relationships.

## Principal sources used

Primary textual and material controls include SBLGNT Ephesians, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[P49](https://manuscripts.csntm.org/manuscript/Group/GA_P49),
[P92](https://manuscripts.csntm.org/manuscript/View/GA_P92),
[Codex Sinaiticus](https://codexsinaiticus.org/),
[UNESCO Ephesus](https://whc.unesco.org/en/list/1018/), and the
[British Museum Artemis sanctuary stela](https://www.britishmuseum.org/collection/object/G_1870-0715-6).
Independent controls include:

- Andrew T. Lincoln, *Ephesians*; Harold W. Hoehner, *Ephesians*; Frank
  Thielman, *Ephesians*; Lynn H. Cohick, *The Letter to the Ephesians*;
  Ernest Best, *A Critical and Exegetical Commentary on Ephesians*; and
  Margaret Y. MacDonald, *Colossians and Ephesians*.
- Clinton E. Arnold on powers and Ephesian context; Timothy G. Gombis on the
  letter's dramatic and political imagery; Margaret Y. MacDonald on children
  and Roman households; and Jennifer A. Glancy on slavery and bodies.
- BDAG and LSJ as lexical controls, without treating dictionary glosses as
  sufficient to settle contextual disputes.

Publisher, university, manuscript-project, archive, museum, and scholarly
organization pages establish bibliographic identity or bounded evidence. A
qualified reviewer must verify every locator, Greek and scriptural reading,
translation, manuscript date, historical inference, and characterization of
a scholarly position.

## Retrieval and regression coverage

The Ephesians fixture checks eight areas: factual structure, removal of the
placeholder, honest governance, current claim and note taxonomies, sources and
lexical data, book-scoped retrieval, interpretive safeguards, and SQLite
parity. The rebuilt record ranks first for thirty-two explicitly book-scoped
questions covering composition, textual history, theology, ethics, reception,
and safeguarding. No retrieval-code or neighboring-record change was needed.

## Human review checklist

Verify:

- SBLGNT wording; Hebrew Bible and Septuagint comparisons; P46, P49, P92,
  Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus, versions, and
  every textual claim, especially “in Ephesus”;
- direct Pauline, secretary-mediated, associate, and Pauline-school proposals;
  dates, provenance, imprisonment, destination, circularity, audience,
  purpose, integrity, Tychicus, and relation to Colossians and Acts;
- every use of Ephesian and Anatolian archaeology, Artemis evidence, Roman
  households, associations, patronage, slavery, gender, childhood, labor,
  rhetoric, and cosmic-power comparanda;
- `en Christō`, election and predestination terms, `apolytrōsis`,
  `mystērion`, `pistis`, `charis`, `erga`, `sarx`, `nomos`, `kainos
  anthrōpos`, `ekklēsia`, `sōma`, `kephalē`, `plērōma`, `hypotassō`,
  `doulos`, and `panoplia`;
- each certainty and dispute label, rationale, source locator, support target,
  Scripture anchor, graph edge, lexical entry, and retrieval phrase; and
- every treatment of Jews and Judaism, Torah, gentiles, election, authority,
  bodies, sexuality, marriage, children, enslavement, labor, disability,
  mental health, medicine, powers, violence, mission, money, politics, and
  creation.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/ephesians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_ephesians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 200 + 151 + 157 = 508 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,277 edges, 0 unknown targets, 0 orphaned objects
# 2,831 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave40-ephesians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave40-ephesians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b0a3ab5baeab87f3932601a3ead69174f85da0591c0fdd5218ff656d48a5842c
# 45,711,360 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
