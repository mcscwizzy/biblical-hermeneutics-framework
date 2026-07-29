# Phase 5 Wave 47 Review: Titus

Last updated: 2026-07-28

## Review status

The Titus correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`titus.json`](../framework/canonical_library/objects/books/titus.json)
- [`test_titus_record.py`](../tests/canonical_library/test_titus_record.py)

## Corrections made

- Removed generic Pastoral-book context, false ancient-context and completion
  metadata, unsupported Rome, Corinth, Ephesus, mission, and itinerary claims,
  and legacy evidence labels.
- Rebuilt the record around Titus 1:1-16; 2:1-15; and 3:1-15.
- Distinguished Paul and Titus; elders and overseers; age, gender, and status
  groups; enslaved people; rhetorically portrayed opponents; Artemas,
  Tychicus, Zenas, Apollos, households, patrons, rulers, and later
  interpreters without inventing one opponent group or settled polity.
- Qualified Pauline, secretary-assisted, and Pauline-school authorship; date;
  provenance; destination; relation to Acts and the other Pastorals; church
  order; personal-note historicity; and the proposed Nicopolis itinerary.
- Preserved disputes concerning elder-overseer relations, household
  qualifications, circumcision and opponent language, the Cretan quotation,
  purity, gendered instruction, slavery, `epiphaneia`, rulers, washing of
  regeneration, Spirit renewal, justification, good works, controversies,
  `hairetikos`, discipline, and closing travel.
- Corrected manuscript orientation: P32 preserves Titus 1:11-15 and 2:3-8;
  Sinaiticus and later witnesses preserve more of the letter; surviving
  Vaticanus ends before the Pastorals and is not a Titus witness.
- Added safeguards against antisemitism, supersessionism, anti-Cretan ethnic
  contempt, misogyny, anti-LGBTQ coercion, authoritarian office, clericalism,
  victim blaming, slavery apologetics, worker exploitation, nationalism,
  militarism, colonial mission, forced conversion, religious violence,
  public shaming, prosperity extraction, and ecological neglect.
- Added thirty-three sourced claims, forty current-taxonomy notes, twenty-two
  sources, twenty URL-bearing external sources, eight top-level aliases plus
  retrieval metadata, fifteen normalized Scripture anchors, ten Hebrew
  entries, twenty-five Greek entries, and eight graph links.

## Principal sources used

Primary controls include SBLGNT Titus, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[P32 at CSNTM](https://manuscripts.csntm.org/Manuscript/Group/GA_P32),
[Codex Sinaiticus](https://codexsinaiticus.org/en/manuscript.aspx), and
digitized Vaticanus and Alexandrinus controls. Independent controls include
I. Howard Marshall, Philip H. Towner, Raymond F. Collins, Annette Bourland
Huizenga, Matthijs den Dulk, J. Albert Harrill, Carolyn Osiek, Margaret
Y. MacDonald, Jennifer A. Glancy, Kathy Ehrensperger, *The Jewish Annotated
New Testament*, BDAG, David E. Aune, Bart D. Ehrman, Richard P. Saller, and
Cretan epigraphic resources.

A qualified reviewer must verify every locator, textual reading, translation,
manuscript date, historical inference, genre classification, and
representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, placeholder removal, honest governance,
current taxonomies, sources, lexical data, graph links, safeguarding language,
and SQLite parity. Titus ranks first for forty book-scoped questions.

Reviewers should verify manuscript and lexical claims; all Cretan and Roman
comparanda; authorship and chronology; office and household reconstruction;
the identification and treatment of opponents; the Cretan quotation and its
reception; gender and slavery; rulers and discipline; baptism, regeneration,
justification, and good works; and every evidence label, source locator,
Scripture anchor, graph edge, and retrieval phrase. Do not advance the record
merely because automated checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/titus.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_titus_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 161 + 133 + 168 + 102 = 564 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,296 edges, 0 unknown targets, 0 orphaned objects
# 2,848 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave47-titus-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave47-titus-final.sqlite
# Database schema 2; 620 objects
# fingerprint 0091cbfc3d646087e0116045efd024103c2e0ca302752b70487e34dab3cbcbba
# 48,766,976 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
