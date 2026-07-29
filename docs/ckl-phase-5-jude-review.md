# Phase 5 Wave 56 Review: Jude

Last updated: 2026-07-29

## Review status

The Jude correction wave is implemented and machine-verified. The record
remains `draft` / `in_review`, requires human review, has no `last_reviewed`
date, and has `section_status.human_review` set to `missing`. Automated
validation does not constitute approval.

Files for review:

- [`jude.json`](../framework/canonical_library/objects/books/jude.json)
- [`test_jude_record.py`](../tests/canonical_library/test_jude_record.py)

The legacy record lost book-scoped questions to James, 2 Peter, Egypt, Moses,
Balaam, Daniel, Spirit, Romans, Matthew, John, and Jude of Jerusalem records.
Exact Jude aliases now disambiguate all forty fixture questions. One completed
2 Peter query then ranked Jude first; a single exact alias was added to
[`2-peter.json`](../framework/canonical_library/objects/books/2-peter.json) as
a concrete regression safeguard, without changing that record's content.

## Corrections made

- Removed false completion metadata and generic General Epistle people,
  places, persecution, audience, authorship, date, provenance, itinerary,
  opponent-system, and church-order claims.
- Rebuilt the record around Jude 1:1-4; 1:5-16; 1:17-23; and 1:24-25.
- Distinguished Jude's explicit servant and brother-of-James designation from
  proposed historical identities; James; the called and beloved or kept
  addressees; polemically portrayed intruders; Jesus Christ; God; Spirit;
  angels; Michael; the devil; Cain; Balaam; Korah; Enoch; apostles; doubters
  and endangered people; and later interpreters.
- Refused to call Jude an apostle, decide which James he names, invent a
  complete opponent system, or treat a location, persecution, office,
  love-feast institution, or community biography as explicit.
- Qualified authorship, date, provenance, audience, genre, relation to
  2 Peter, opponent and meal reconstructions, Jewish literary traditions,
  historical reliability, canonical reception, and the doxology.
- Preserved the textual variants in verses 1, 5, and 22-23 and disputes over
  the exodus agent, angels, Sodom, lordship, glories, Michael and Moses,
  natural knowledge, Cain/Balaam/Korah analogies, love feasts, nature
  metaphors, Enoch, apostles, scoffers, Spirit language, mercy, rescue,
  garment imagery, preservation, and divine titles.
- Located the letter within Hebrew Bible and Septuagint traditions, 1 Enoch,
  the Moses tradition, Second Temple Jewish interpretation, Greco-Roman
  letter and invective forms, 2 Peter, manuscripts, early reception, and
  later doctrine without turning parallels into proof.
- Distinguished biblical wording from textual variant, lexical proposal,
  polemical characterization, historical reconstruction, Jewish literary
  reception, doctrine, pastoral application, and modern analogy.
- Added safeguards against antisemitism, supersessionism, opponent
  dehumanization, heresy-hunting, schism weaponization, sexual shaming,
  coercive discipline, surveillance, spiritual abuse, authoritarian
  leadership, anti-intellectualism, mental-health stigma, misogyny,
  anti-LGBTQ coercion, public shaming, nationalism, colonial mission, forced
  conversion, religious violence, prosperity extraction, and ecological
  neglect.
- Added twenty-nine sourced claims, thirty-nine current-taxonomy notes,
  twenty-six sources, twenty-four URL-bearing external sources, twenty-nine
  high-precision top-level aliases plus retrieval metadata, twenty normalized
  Scripture anchors, ten Hebrew entries, thirty-eight Greek entries, and five
  verified graph relationships.

## Principal sources used

Primary controls include SBLGNT Jude, the *Editio Critica Maior* Catholic
Letters, INTF/NTVMR, Papyrus 72, Codex Sinaiticus, Codex Vaticanus, Codex
Alexandrinus, NETS, the Dead Sea Scrolls Digital Library, 1 Enoch, the Moses
tradition, 2 Peter, and Eusebius. Independent controls include Richard
Bauckham, Jerome Neyrey, Peter Davids, Gene Green, Jörg Frey, Pheme Perkins,
David deSilva, *The Jewish Annotated New Testament*, BDAG, LSJ, and Bruce
Metzger.

A qualified reviewer must verify every locator, Greek form, textual reading,
translation, manuscript date and extent, Hebrew Bible and Septuagint
comparison, 1 Enoch and Moses-tradition relationship, Greco-Roman analogy,
historical inference, genre classification, reception claim, and
representation of a scholarly position.

## Retrieval and human review

The fixture checks factual structure, named and reconstructed figures,
placeholder removal, honest governance, current taxonomies, sources, lexical
data, graph links, safeguarding language, and SQLite parity. Jude ranks first
for forty book-scoped questions. The 2 Peter and Jude modules together pass
sixteen tests after the exact cross-book safeguard.

Reviewers should verify the Greek text and every variant; manuscript and
versional evidence; sender, James, audience, intruder, angel, Michael, devil,
Moses, Cain, Balaam, Korah, Enoch, apostle, scoffer, doubter, and rescue
proposal; authorship, date, provenance, genre, integrity, opponents, meals,
apostolic memory, reception, and relation to 2 Peter; faith, contention,
grace, denial, exodus, angelic prison, Sodom, fire, dreams, flesh, lordship,
glories, natural knowledge, metaphors, Enochic prophecy, Spirit, prayer,
keeping, waiting, mercy, rescue, fear, garment, preservation, joy, and
doxology; every safeguarding control; and every evidence label, source
locator, Scripture anchor, graph edge, and retrieval phrase. Do not advance
the record merely because automated checks pass.

## Machine verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/jude.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_jude_record
# 8 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 156 + 146 + 166 tests: OK
# One failure among the remaining 168 exposed the 2 Peter retrieval collision.

python3 -m unittest \
  tests.canonical_library.test_2_peter_record \
  tests.canonical_library.test_jude_record
# 16 tests: OK after the exact 2 Peter safeguard

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py \
  --root framework/canonical_library \
  --limit 10
# 620 objects, 3,311 edges, 0 unknown targets, 0 orphaned objects
# 2,859 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave56-jude-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave56-jude-final.sqlite
# Database schema 2; 620 objects
# fingerprint 62880dbe4a355a5783a701e0731dab8d8516439c5a871d73cbee1fde18dd09ef
# 52,342,784 bytes
```

The first deep-report pass identified one human-readable `1 Enoch` legacy
reference in `related_entries`. It was removed because no canonical 1 Enoch
object exists; the sourced intertextual, claim, note, and source material
remains. The regenerated report has zero unresolved source references, zero
invalid source support targets, fourteen pre-existing unresolved legacy
references, and zero Scripture-reference errors.

Python 3.14 emits the repository's known unclosed-SQLite `ResourceWarning`
messages; they do not change successful test results.
