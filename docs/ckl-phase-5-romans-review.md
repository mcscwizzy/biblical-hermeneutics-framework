# Phase 5 Wave 36 Review: Romans

Last updated: 2026-07-25

## Review status

The Romans correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`romans.json`](../framework/canonical_library/objects/books/romans.json)
- [`test_romans_record.py`](../tests/canonical_library/test_romans_record.py)

## Corrections made

- Removed the inherited Pauline-letter template: generic mission and church
  events; Titus and Ephesus; generic audience, structure, authorship disputes,
  and completion metadata; incorrect ancient Near Eastern applicability; and
  unsupported claims of a single Roman congregation.
- Rebuilt the record around Romans 1:1-17; 1:18-3:20; 3:21-4:25; 5:1-8:39;
  9:1-11:36; 12:1-15:13; 15:14-33; and 16:1-27.
- Distinguished Paul as sender, Tertius as scribe, Phoebe as commended
  `diakonos` and `prostatis`, implied Roman audiences, Jewish and gentile
  rhetorical interlocutors, weak and strong participants, governing
  authorities, scriptural figures and voices, enslaved and free networks,
  coworkers, women leaders, households, and later interpreters.
- Qualified Pauline authorship, scribal process, Phoebe's probable carrier
  role, 56-58 CE dating, Corinth-Cenchreae provenance, Claudian policy,
  audience composition, occasion, purpose, Jerusalem collection, Spain plan,
  letter integrity, Romans 16, and the mobile doxology.
- Indexed letter forms, diatribe, rhetorical interlocutors and questions,
  scriptural catenae, Abraham exemplum, Adam-Messiah comparison, analogy,
  personification, lament, paraenesis, recommendation, household greetings,
  warnings, benediction, and doxology.
- Addressed divine righteousness or justice, `pistis Christou`, wrath,
  sexuality, creation knowledge, judgment, conscience, works of Torah,
  `hilasterion`, justification, Abraham, Romans 5:1 and 5:12, original sin,
  baptism, slavery metaphors, Romans 7's speaker, flesh and Spirit, creation's
  groaning, suffering, prayer, predestination, Israel, election, `telos`,
  olive tree, all Israel, irrevocable gifts, living sacrifice, gifts,
  enemies, authorities, debt, love, food, days, weak and strong, collection,
  Phoebe, Junia, Prisca, households, warnings, and manuscript endings.
- Added P10, P26, P27, P31, P40, P46, P61, Sinaiticus, Vaticanus,
  Alexandrinus, Claromontanus, NTVMR, Septuagint, Roman and Corinthian
  archaeology, Suetonius, inscriptions, social history, and reception
  controls.
- Added safeguards against antisemitism, supersessionism, collective Jewish
  guilt, legalistic caricatures of Judaism, anti-Roman racism, anti-LGBTQ
  coercion, misogyny, erasure of women, slavery apologetics, worker
  exploitation, body shame, disability and mental-health stigma, coerced
  baptism, original-sin blame, predestination fatalism, suicide harm,
  silencing lament, unlimited government obedience, authoritarianism,
  nationalism, colonial mission, forced conversion, religious violence,
  financial extraction, victim blame, trauma glorification, ecological
  neglect, conspiracy claims, partisan capture, and territorial seizure.
- Added forty-eight sourced claims, seventy-eight current-taxonomy
  interpretive notes, forty sources, thirty-nine URL-bearing external
  sources, seventy-one aliases, fourteen normalized Scripture anchors, ten
  Hebrew entries, twenty-five Greek entries, and ten verified relationships.

## Principal sources used

Primary textual and material controls include SBLGNT Romans, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P46](https://manuscripts.csntm.org/manuscript/View/GA_P46),
[Codex Sinaiticus](https://www.codexsinaiticus.org/en/manuscript.aspx),
[Codex Vaticanus](https://digi.vatlib.it/view/MSS_Vat.gr.1209),
[Codex Alexandrinus](https://www.bl.uk/manuscripts/FullDisplay.aspx?ref=Royal_MS_1_D_VIII),
and
[Codex Claromontanus](https://manuscripts.csntm.org/manuscript/View/GA_06).
Independent research includes:

- Michael Wolter, *The Letter to the Romans*; Beverly Roberts Gaventa,
  *When in Romans*; Stanley K. Stowers, *A Rereading of Romans*; and Douglas
  A. Campbell, *The Deliverance of God*.
- Mark D. Nanos, *The Mystery of Romans*; Philip F. Esler, *Conflict and
  Identity in Romans*; Matthew Thiessen, *Paul and the Gentile Problem*; and
  Paula Fredriksen, *Paul: The Pagans' Apostle*.
- Christopher D. Stanley,
  [*Paul and the Language of Scripture*](https://doi.org/10.1017/CBO9780511896552);
  Mark Reasoner, *The Strong and the Weak*; Susan Grove Eastman, *Paul and
  the Person*; and Jouette M. Bassler, *Divine Impartiality*.
- Eldon Jay Epp, *Junia: The First Woman Apostle*; M. Sybrandi,
  [“Women Leaders Lost in Translation?”](https://ora.ox.ac.uk/objects/uuid:9e7a3c57-7bad-459c-95ec-f89152135e9d);
  Lynn Cohick on women in earliest Christianity; and E. Randolph Richards on
  ancient letter production.
- William Loader on ancient sexuality; J. Albert Harrill and John Byron on
  slavery; Jerry L. Sumney on Romans 13; Bruce Longenecker on the poor; David
  Horrell on ecological interpretation; and Sarah Whittle on consecration.
- [Suetonius, *Claudius* 25.4](https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.02.0061:life=cl.:chapter=25),
  [Ancient Corinth](https://corinth.ascsa.net/), and
  [PHI Greek Inscriptions](https://inscriptions.packhum.org/).

Publisher, university, manuscript-project, archive, museum, and scholarly
organization pages establish bibliographic identity or bounded evidence. A
qualified reviewer must verify every locator, Greek and scriptural reading,
translation, manuscript date, historical inference, and characterization of
a scholarly position.

## Retrieval and regression coverage

The Romans-specific test was created before the record changed. Its baseline
ran eight test methods and recorded thirty-eight individual failures across
structure, composition, governance, sources, claims, safeguards, and
retrieval; SQLite parity was the only passing method.

The rebuilt record now ranks first for sixty-eight Romans-specific questions.
Enrichment initially displaced completed Hosea and Joel intertext questions
and one golden new-creation query. Redundant top-level reception anchors and
incidental indexing phrases were reduced while Romans' Israel, Torah,
baptism, and creation content remained represented in structure, claims,
notes, and sources. The focused neighborhood and the complete 476-test CKL
suite then passed without retrieval-code changes or edits to the Hosea, Joel,
or golden-query fixtures.

## Human review checklist

Verify:

- SBLGNT wording; every Hebrew Bible and Septuagint comparison; P10, P26,
  P27, P31, P40, P46, P61, Sinaiticus, Vaticanus, Alexandrinus,
  Claromontanus, versions, Romans 5:1, Romans 16, and doxology variants;
- Pauline authorship, Tertius's role, Phoebe's titles and probable carrier
  role, date, provenance, Claudian policy, audiences, purpose, collection,
  Spain, integrity, and circulation;
- every reconstruction using Rome, Corinth, Cenchreae, Suetonius,
  inscriptions, households, associations, patronage, enslavement, civic
  office, travel, and empire;
- `dikaiosyne theou`, `pistis Christou`, `erga nomou`, `hilasterion`, `sarx`,
  `pneuma`, `telos`, `diakonos`, `prostatis`, and Junia's name and syntax;
- each certainty and dispute label, rationale, source locator, support target,
  Scripture anchor, graph edge, lexical entry, and retrieval alias;
- every treatment of sexuality, Torah and Judaism, justification, original
  sin, baptism, slavery, Romans 7, suffering, predestination, Israel, Romans
  13, weak and strong, women, households, money, and mission; and
- every antisemitism, sexuality, gender, slavery, disability, mental-health,
  medical, safeguarding, political, economic, trauma, ecological, and
  noncoercion safeguard.

Do not advance the record merely because automated checks pass. Advance only
after a qualified human reviewer records decisions and remaining issues.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/romans.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_romans_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 31.555s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 168 + 154 + 154 = 476 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,264 edges, 0 unknown targets, 0 orphaned objects
# 2,818 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave36-romans-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave36-romans-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 7d8b96ada95ae5ca995d6c8337fb7275cf1edfdffa424bd7e9ac8b5d7a09560e
# 43,405,312 bytes
```

Python 3.14 emitted the repository's known unclosed-SQLite `ResourceWarning`
messages; they did not change successful test results.
