# Phase 5 Wave 46 Review: 2 Timothy

Last updated: 2026-07-28

## Review status

The 2 Timothy correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`2-timothy.json`](../framework/canonical_library/objects/books/2-timothy.json)
- [`test_2_timothy_record.py`](../tests/canonical_library/test_2_timothy_record.py)

## Corrections made

- Removed generic Pauline-book context, false ancient-context and completion
  metadata, unsupported Corinth and itinerary claims, and legacy evidence
  labels.
- Rebuilt the record around 2 Timothy 1:1-18; 2:1-26; 3:1-17; and 4:1-22.
- Distinguished the named sender and recipient; family members, supporters,
  opponents, coworkers, greeters, learning women, households, and later
  interpreters without turning compressed notices into complete biographies.
- Qualified Pauline, secretary-assisted, composite, and Pauline-school
  authorship; date; provenance; imprisonment; relation to Acts and the other
  Pastorals; testament form; personal-note historicity; and martyrdom
  reconstruction.
- Preserved disputes concerning the gift, Spirit of fear, deposit,
  Onesiphorus, metaphors, resurrection error, `orthotomeō`, vessels, Jannes
  and Jambres, learning women, sacred writings, `theopneustos`, canon,
  sufficiency, farewell, defense, coworkers, books, parchments, and greetings.
- Corrected manuscript orientation: Sinaiticus preserves 2 Timothy, while the
  surviving Vaticanus ends before the Pastorals and is not a witness to the
  book.
- Added safeguards against antisemitism, supersessionism, misogyny,
  anti-LGBTQ coercion, authoritarian office, clericalism, martyrdom and trauma
  glorification, militarism, productivity coercion, anti-intellectualism,
  disability and mental-health shame, medical neglect, public shaming,
  slavery apologetics, worker exploitation, nationalism, colonial mission,
  forced conversion, religious violence, prosperity extraction, and
  ecological neglect.
- Added thirty-one sourced claims, forty-one current-taxonomy notes,
  twenty-two sources, twenty URL-bearing external sources, seven top-level
  aliases plus retrieval metadata, nineteen normalized Scripture anchors, ten
  Hebrew entries, twenty-five Greek entries, and eight graph links.

## Principal sources used

Primary controls include SBLGNT 2 Timothy, NETS,
[INTF/NTVMR](https://ntvmr.uni-muenster.de/),
[Codex Sinaiticus](https://codexsinaiticus.org/en/manuscript.aspx?book=48&lid=en&side=r&zoomslider=0),
and digitized Vaticanus, Alexandrinus, Ephraemi, and Claromontanus controls.
Independent controls include I. Howard Marshall, Philip H. Towner, Luke
Timothy Johnson, Raymond F. Collins, Craig A. Smith, Annette Bourland
Huizenga, Cynthia Long Westfall, Carolyn Osiek, Margaret Y. MacDonald,
Jennifer A. Glancy, Kathy Ehrensperger, *The Jewish Annotated New Testament*,
BDAG, David E. Aune, and Bart D. Ehrman.

A qualified reviewer must verify every locator, textual reading, translation,
manuscript date, historical inference, genre classification, and
representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, placeholder removal, honest governance,
current taxonomies, sources, lexical data, graph links, safeguarding language,
and SQLite parity. 2 Timothy ranks first for forty book-scoped questions.

Reviewers should verify manuscript and lexical claims; all historical and
literary reconstructions; Roman social comparanda; treatments of women,
leaders, suffering, mental health, labor, violence, Scripture, canon,
inspiration, and sufficiency; and every evidence label, source locator,
Scripture anchor, graph edge, and retrieval phrase. Do not advance the record
merely because automated checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/2-timothy.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_2_timothy_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 161 + 133 + 94 + 168 = 556 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,293 edges, 0 unknown targets, 0 orphaned objects
# 2,845 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave46-2-timothy-final.sqlite
# Database schema 2; 620 objects
# fingerprint da421e34670b9a81395868b33f85261f7e7db7a0aaf6bf1e5b87cffc789b54cb
# 48,369,664 bytes
```

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
