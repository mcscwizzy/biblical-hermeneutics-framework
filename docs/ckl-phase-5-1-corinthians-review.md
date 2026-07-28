# Phase 5 Wave 37 Review: 1 Corinthians

Last updated: 2026-07-28

## Review status

The 1 Corinthians correction wave is implemented and machine-verified. The
record remains `draft` / `in_review`, requires human review, has no
`last_reviewed` date, and has `section_status.human_review` set to `missing`.
Automated validation does not constitute approval.

Files for review:

- [`1-corinthians.json`](../framework/canonical_library/objects/books/1-corinthians.json)
- [`test_1_corinthians_record.py`](../tests/canonical_library/test_1_corinthians_record.py)

## Corrections made

- Removed the inherited Pauline-letter placeholder: generic mission and
  church-formation events; Titus, Rome, and a generic world-wide audience;
  broad date and authorship templates; incorrect ancient Near Eastern
  applicability; and unsupported completion metadata.
- Rebuilt the record around 1 Corinthians 1:1-4:21; 5:1-6:20; 7:1-40;
  8:1-11:1; 11:2-14:40; 15:1-58; and 16:1-24.
- Distinguished Paul and Sosthenes, Chloe's people, Apollos and Cephas,
  Stephanas's household, Crispus, Gaius, Fortunatus, Achaicus, Timothy,
  Aquila, Prisca, women and men who pray and prophesy, married and unmarried
  people, enslaved and free people, diners, workers, litigants, hungry and ill
  members, scriptural figures and voices, and later interpreters.
- Qualified Pauline authorship, Sosthenes's role, 53-55 CE dating, Ephesian
  provenance, Chloe's report, the Corinthians' lost letter, factions and
  slogans, composition integrity, audience diversity, gathering locations,
  correspondence chronology, and relation to Acts and 2 Corinthians.
- Indexed report response, question-and-answer, possible slogans, diatribe,
  rhetorical questions, irony, case judgment, vice list, household counsel,
  scriptural exempla, apostolic self-presentation, tradition reports, gift
  lists, encomium, resurrection proof, collection instruction, travel,
  commendation, greeting, anathema, and benediction.
- Addressed the cross, wisdom, power, temple, discipline, lawsuits, bodies,
  `malakoi`, `arsenokoitai`, marriage, divorce, celibacy, slavery, calling,
  virgins, idol food, conscience, rights, wilderness Israel, demons, head
  coverings, `kephale`, angels, hair, Lord's supper, class inequality, gifts,
  love, tongues, prophecy, women speaking, resurrection tradition, witnesses,
  baptism for the dead, resurrection body, Adam, collection, coworkers, and
  `Maranatha`.
- Added P15, P46, P123, Sinaiticus, Vaticanus, Alexandrinus, Claromontanus,
  NTVMR, Septuagint, Corinthian excavation and inscription evidence,
  households, associations, banquets, patronage, slavery, gender, body,
  rhetoric, philosophy, cult, law, economics, and early-reception controls.
- Added safeguards against sectarianism, celebrity leadership, authoritarian
  discipline, public shaming, sexual abuse and incest mishandling, anti-LGBTQ
  coercion, misogyny, forced marriage or celibacy, divorce coercion, slavery
  apologetics, worker exploitation, body and disability stigma, medical
  neglect, class humiliation, eucharistic exclusion, coercive gifts,
  antisemitism, supersessionism, colonial mission, religious violence,
  nationalism, conspiracy claims, partisan capture, financial extraction,
  poverty romanticization, trauma glorification, and ecological neglect.
- Added forty-four sourced claims, eighty-eight current-taxonomy interpretive
  notes, thirty-five sources, thirty-four URL-bearing external sources, three
  high-precision top-level aliases plus retrieval metadata, fifteen normalized
  Scripture anchors, ten Hebrew entries, twenty Greek entries, and nine
  verified relationships.

## Principal sources used

Primary textual and material controls include SBLGNT 1 Corinthians, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[Codex Sinaiticus](https://www.codexsinaiticus.org/en/),
[Codex Vaticanus](https://digi.vatlib.it/view/MSS_Vat.gr.1209),
[Codex Alexandrinus](https://www.bl.uk/manuscripts/FullDisplay.aspx?ref=Royal_MS_1_D_VIII),
[Codex Claromontanus](https://gallica.bnf.fr/ark:/12148/btv1b84683111),
[Ancient Corinth](https://www.ascsa.edu.gr/excavations/ancient-corinth), and
[PHI Greek Inscriptions](https://inscriptions.packhum.org/). Independent
research includes:

- Gordon D. Fee, *The First Epistle to the Corinthians*; Anthony C.
  Thiselton, *The First Epistle to the Corinthians*; Richard B. Hays,
  *First Corinthians*; Roy E. Ciampa and Brian S. Rosner, *The First Letter
  to the Corinthians*; David E. Garland, *1 Corinthians*; and Raymond F.
  Collins, *First Corinthians*.
- Margaret M. Mitchell, *Paul and the Rhetoric of Reconciliation*; Matthew
  R. Malcolm,
  [*Paul and the Rhetoric of Reversal in 1 Corinthians*](https://www.cambridge.org/core/books/paul-and-the-rhetoric-of-reversal-in-1-corinthians/941B2433019D1F7ABE0E68651DF76BA2);
  Timothy A. Brookins on Corinthian wisdom and economy; and Matthew Pawlak
  on sarcasm and Corinthian slogans.
- Dale B. Martin, *The Corinthian Body*; Antoinette Clark Wire,
  *The Corinthian Women Prophets*; Jerome Murphy-O'Connor,
  *St. Paul's Corinth*; Bruce W. Winter, *After Paul Left Corinth*; and
  John Fotopoulos, *Food Offered to Idols in Roman Corinth*.
- Jennifer A. Glancy,
  [*Slavery in Early Christianity*](https://academic.oup.com/book/7076);
  J. Albert Harrill on slavery; William Loader on sexuality; Barry Danylak
  on singleness; Dennis E. Smith on meals; Steven J. Friesen on economics;
  and Laura Salah Nasrallah on archaeology.

Publisher, university, manuscript-project, archive, museum, and scholarly
organization pages establish bibliographic identity or bounded evidence. A
qualified reviewer must verify every locator, Greek and scriptural reading,
translation, manuscript date, historical inference, and characterization of
a scholarly position.

## Retrieval and regression coverage

The 1 Corinthians-specific test was created before the record changed. Its
baseline ran eight test methods and recorded twenty-three individual failures
across structure, composition, governance, sources, claims, safeguards, and
retrieval; SQLite parity was the only passing method.

The rebuilt record ranks first for sixty-six 1 Corinthians-specific questions.
Initial broad question aliases displaced one completed Haggai query. The
top-level alias list was reduced to three high-precision titles, and ambiguous
questions were given explicit book or verse context. Both retrieval
neighborhoods and the complete 484-test CKL suite then passed without
retrieval-code changes or edits to the Haggai record or fixture.

## Human review checklist

Verify:

- SBLGNT wording; every Hebrew Bible and Septuagint comparison; P15, P46,
  P123, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus, versions,
  14:34-35 displacement, and other cited variants;
- Pauline authorship, Sosthenes's role, date, provenance, correspondence
  chronology, Chloe's people, received letter, audience, factions, slogans,
  integrity, purpose, and relation to Acts and 2 Corinthians;
- every reconstruction using Corinthian archaeology, inscriptions, colonial
  institutions, households, associations, banquets, cult, law, patronage,
  rhetoric, economics, enslaved people, and social status;
- `sophia`, `soma`, `porneia`, `malakoi`, `arsenokoitai`, `syneidesis`,
  `exousia`, `kephale`, `charisma`, `glossa`, `agape`, `soma pneumatikon`,
  `Maranatha`, and `anathema`;
- each certainty and dispute label, rationale, source locator, support target,
  Scripture anchor, graph edge, lexical entry, and retrieval phrase;
- every treatment of discipline, sexuality, marriage, divorce, celibacy,
  slavery, idol food, gender, meals, illness, gifts, women speaking,
  resurrection, money, labor, and leadership; and
- every safeguarding, antisemitism, sexuality, gender, slavery, disability,
  mental-health, medical, economic, political, ecological, and noncoercion
  boundary.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/1-corinthians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_1_corinthians_record \
  tests.canonical_library.test_haggai_record.HaggaiRecordTests.test_retrieval_answers_haggai_specific_questions \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 79 tests in 49.335s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 176 + 154 + 154 = 484 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,268 edges, 0 unknown targets, 0 orphaned objects
# 2,822 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave37-1-corinthians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave37-1-corinthians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# d565d703d4eb9fdeb58ec875e46bcb056020da65da1f7f114c461ac9418e4081
# 44,101,632 bytes
```

Python 3.14 may emit the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
