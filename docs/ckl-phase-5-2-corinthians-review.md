# Phase 5 Wave 38 Review: 2 Corinthians

Last updated: 2026-07-28

## Review status

The 2 Corinthians correction wave is implemented and machine-verified. The
record remains `draft` / `in_review`, requires human review, has no
`last_reviewed` date, and has `section_status.human_review` set to `missing`.
Automated validation does not constitute approval.

Files for review:

- [`2-corinthians.json`](../framework/canonical_library/objects/books/2-corinthians.json)
- [`test_2_corinthians_record.py`](../tests/canonical_library/test_2_corinthians_record.py)

## Corrections made

- Removed the inherited Pauline-letter placeholder: generic mission and
  church-formation events; Rome and Ephesus as an unsupported place set; a
  generic world-wide audience; broad date and authorship templates; incorrect
  ancient Near Eastern applicability; and false completion metadata.
- Rebuilt the record around 2 Corinthians 1:1-2:13; 2:14-7:4; 7:5-16;
  8:1-9:15; 10:1-13:10; and 13:11-14.
- Distinguished Paul and Timothy, the Corinthian assembly and Achaian saints,
  Titus, unnamed collection delegates, Macedonian assemblies, Jerusalem
  saints, the offender, injured party, reconciled majority, rival apostles,
  rhetorical interlocutors, Moses and scriptural voices, patrons, laborers,
  enslaved and free people, women and men, afflicted and disabled people, and
  later interpreters.
- Qualified Pauline authorship, Timothy's role, mid-50s dating, Macedonian
  provenance, travel chronology, the painful visit and severe letter, Titus's
  missions, the offender and injured party, letter integrity and partition
  theories, opponents, purpose, audience, and relation to Acts and
  1 Corinthians.
- Indexed blessing, travel apology, autobiography, scriptural exposition,
  contrast, metaphor, hardship catalog, ambassadorial appeal, holiness
  exhortation, collection rhetoric, commendation, irony, invective, parody,
  boasting, fool's speech, vision report, warning, examination, restoration,
  greeting, and benediction.
- Addressed affliction, comfort, conscience, forgiveness, triumph, aroma,
  sufficiency, letter and Spirit, covenant, Moses' veil, transformation,
  earthen vessels, outer and inner person, heavenly dwelling, judgment,
  knowing Messiah according to flesh, new creation, reconciliation,
  ambassador language, grief, collection, equality, accountability, sowing,
  rivals, hardships, visions, thorn, signs, weakness, discipline,
  self-examination, and the triadic blessing.
- Added P46, P99, Sinaiticus, Vaticanus, Alexandrinus, Claromontanus, NTVMR,
  Septuagint, Corinthian excavation and inscription evidence, travel,
  patronage, benefaction, rhetoric, economics, collection, disability, and
  heavenly-ascent controls.
- Added safeguards against antisemitism and supersessionism; coerced
  forgiveness and unsafe reconciliation; trauma and suffering glorification;
  disability and mental-health stigma; medical neglect and dangerous
  exorcism; sexual abuse, misogyny, and anti-LGBTQ coercion; slavery and worker
  exploitation; financial extraction and prosperity teaching; public
  shaming, surveillance, authoritarian leadership, colonial mission, forced
  conversion, religious violence, nationalism, conspiracy claims, partisan
  capture, and ecological neglect.
- Added forty sourced claims, seventy-five current-taxonomy interpretive
  notes, thirty sources, twenty-nine URL-bearing external sources, three
  high-precision top-level aliases plus retrieval metadata, fifteen normalized
  Scripture anchors, ten Hebrew entries, twenty Greek entries, and eight
  verified relationships.

## Principal sources used

Primary textual and material controls include SBLGNT 2 Corinthians, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[Codex Sinaiticus](https://www.codexsinaiticus.org/en/),
[Codex Vaticanus](https://digi.vatlib.it/view/MSS_Vat.gr.1209),
[Codex Alexandrinus](https://www.bl.uk/manuscripts/FullDisplay.aspx?ref=Royal_MS_1_D_VIII),
[Codex Claromontanus](https://gallica.bnf.fr/ark:/12148/btv1b84683111),
[Ancient Corinth](https://www.ascsa.edu.gr/excavations/ancient-corinth), and
[PHI Greek Inscriptions](https://inscriptions.packhum.org/). Independent
research includes:

- Victor Paul Furnish, *II Corinthians*; Murray J. Harris,
  *The Second Epistle to the Corinthians*; Margaret E. Thrall,
  *A Critical and Exegetical Commentary on the Second Epistle to the
  Corinthians*; and Mark A. Seifrid,
  *The Second Letter to the Corinthians*.
- Fredrick J. Long,
  [*Ancient Rhetoric and Paul's Apology*](https://www.cambridge.org/core/books/ancient-rhetoric-and-pauls-apology/03B345935C4E9DCCC7478EF3EC600925);
  Ivor H. Jones on letter unity; Christopher Forbes on irony and boasting;
  and Scott B. Andrews on hardship catalogs.
- Scott J. Hafemann on Moses, covenant, triumph, suffering, and ministry;
  Timothy B. Savage on power in weakness; Tim Basselin on disability
  interpretation; and Paula Gooder on heavenly ascent.
- David J. Downs and Bruce W. Longenecker on the Jerusalem collection; Bart
  B. Bruehler on giving rhetoric; Steven J. Friesen on economics; Matthew
  Thiessen on Jewish Paul; and Bruce W. Winter on Greco-Roman civic and
  benefaction contexts.

Publisher, university, manuscript-project, archive, museum, and scholarly
organization pages establish bibliographic identity or bounded evidence. A
qualified reviewer must verify every locator, Greek and scriptural reading,
translation, manuscript date, historical inference, and characterization of
a scholarly position.

## Retrieval and regression coverage

The 2 Corinthians-specific test was created before the record changed. Its
baseline ran eight test methods and recorded twenty-six individual failures
across structure, composition, governance, sources, claims, safeguards, and
retrieval; SQLite parity was the only passing method.

The rebuilt record ranks first for forty-seven explicitly book-scoped
2 Corinthians questions. One broad `new creation` query initially ranked the
existing theme record first, so the fixture now asks the verse-specific
question at 2 Corinthians 5:17. The complete 492-test CKL suite passed without
retrieval-code changes or edits to neighboring completed records.

## Human review checklist

Verify:

- SBLGNT wording; every Hebrew Bible and Septuagint comparison; P46, P99,
  Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus, versions, and
  every cited textual variant;
- Pauline authorship, Timothy's role, date, provenance, correspondence
  sequence, painful visit, severe letter, Titus's missions, offender, injured
  party, audience, opponents, integrity, purpose, and relation to Acts and
  1 Corinthians;
- every reconstruction using Corinthian and Macedonian archaeology,
  inscriptions, travel, households, assemblies, patronage, benefaction,
  slavery, rhetoric, visions, economics, and social status;
- `paraklesis`, `thlipsis`, `thriambeuo`, `osme`, `hikanos`, `gramma`,
  `pneuma`, `diatheke`, `katargeo`, `kalymma`, `katoptrizomai`,
  `ostrakinos`, `katallage`, `presbeuo`, `kaine ktisis`, `isotes`,
  `hilarotes`, `hyperlian apostoloi`, and `skolops te sarki`;
- each certainty and dispute label, rationale, source locator, support target,
  Scripture anchor, graph edge, lexical entry, and retrieval phrase;
- every treatment of forgiveness, reconciliation, covenant, Jews and
  Judaism, suffering, embodiment, disability, judgment, giving, authority,
  polemic, visions, discipline, and leadership; and
- every safeguarding, antisemitism, sexuality, gender, slavery, disability,
  mental-health, medical, economic, political, ecological, and noncoercion
  boundary.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/2-corinthians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_2_corinthians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# focused suite passed

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 184 + 151 + 157 = 492 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,271 edges, 0 unknown targets, 0 orphaned objects
# 2,825 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave38-2-corinthians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave38-2-corinthians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 6143bd5bf47f7ceb9e69e17bd58b4947f5ea953d34d532289178f8ef72a640b5
# 44,666,880 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
