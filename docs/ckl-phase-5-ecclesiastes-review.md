# Phase 5 Wave 13 Review: Ecclesiastes

Last updated: 2026-07-24

## Review status

The Ecclesiastes correction wave is implemented and machine-verified. The
record remains `draft` / `in_review`, requires human review, has no
`last_reviewed` date, and has `section_status.human_review` set to `missing`.
Automated validation does not constitute approval.

Files for review:

- [`ecclesiastes.json`](../framework/canonical_library/objects/books/ecclesiastes.json)
- [`test_ecclesiastes_record.py`](../tests/canonical_library/test_ecclesiastes_record.py)

## Corrections made

- Removed the inherited generic wisdom placeholder, including its Job, David,
  court, temple, suffering, praise, lament, vague Solomonic, and generic
  audience material.
- Rebuilt the record around the superscription and opening poem in 1:1–11,
  Qohelet's first-person inquiry in 1:12–12:7, the closing refrain in 12:8,
  and the epilogue in 12:9–14.
- Distinguished the frame narrator, Qohelet, Qohelet's royal persona,
  represented observations and sayings, the aging poem, and the epilogue
  narrator rather than flattening every line into one voice.
- Distinguished wisdom reflection, frame narrative, royal autobiography or
  persona, investigation, observation, comparative saying, proverb,
  admonition, enjoyment refrain, time poem, aging poem, and epilogue.
- Qualified the title *Qohelet*, traditional Solomonic identification, royal
  persona, authorship, framing, composition, late linguistic evidence,
  Persian- and early Hellenistic-period proposals, and the Qumran terminus.
- Added sustained treatment of *hebel*, *yitron*, *heleq*, “under the sun,”
  toil, enjoyment, wisdom, folly, wealth, power, oppression, time, chance,
  aging, death, God, fear, gift, and judgment.
- Treated *hebel* as a multivalent vapor image rather than making
  “meaningless” an automatic translation and metaphysical conclusion in every
  occurrence.
- Distinguished the book's question about controllable, lasting gain from the
  claim that no act, relationship, pleasure, or moral distinction has value.
- Preserved the repeated enjoyment refrains as finite divine gift without
  converting them into hedonism, consumerism, or prosperity teaching.
- Read Ecclesiastes 3:1–8 as a descriptive antithetical poem rather than a
  list of moral commands, with an explicit safeguard against using “a time to
  kill” to authorize murder, abuse, war, revenge, or coercion.
- Preserved the book's observations of tears, oppression, corrupted judgment,
  hierarchy, delayed justice, and forgotten poor wisdom without using them to
  demand resignation from victims.
- Held wisdom's real comparative value together with its inability to control
  death, chance, rulers, recognition, outcomes, or God's whole work.
- Addressed 4QQohᵃ (4Q109), 4QQohᵇ (4Q110), Greek *Ecclesiast*, the Greek
  title, exceptional translation literalness, and the unresolved Aquila
  proposal.
- Put Ecclesiastes in differentiated canonical dialogue with Genesis, Psalms,
  Proverbs, Job, Sirach, Wisdom of Solomon, and proposed New Testament
  resonances.
- Added safeguards concerning clinical depression, suicidality, trauma,
  grief, aging, disability, mortality, exploited labor, overwork, wealth,
  poverty stigma, victim-blaming, oppression, and spiritualized inaction.
- Added twelve sourced claims, nineteen current-taxonomy interpretive notes,
  twenty source records, sixteen URL-bearing external sources, nine graph
  relationships, explicit section statuses and knowledge layers, a populated
  hermeneutical lens, and retrieval metadata.

## Claim review table

| Claim ID | Certainty | Dispute status |
| --- | --- | --- |
| `ecclesiastes-frame-qohelet-epilogue` | `textually_explicit` | `major_scholarly_disagreement` |
| `ecclesiastes-royal-persona-not-named-solomon` | `textually_explicit` | `major_scholarly_disagreement` |
| `ecclesiastes-date-language-qumran` | `probable` | `chronological_uncertainty` |
| `ecclesiastes-hebel-multivalent` | `strong_consensus` | `lexical_uncertainty` |
| `ecclesiastes-yitron-under-sun` | `probable` | `lexical_uncertainty` |
| `ecclesiastes-enjoyment-divine-gift` | `textually_explicit` | `major_scholarly_disagreement` |
| `ecclesiastes-time-poem-description` | `strong_consensus` | `minor_scholarly_disagreement` |
| `ecclesiastes-oppression-injustice` | `textually_explicit` | `minor_scholarly_disagreement` |
| `ecclesiastes-wisdom-relative-not-control` | `textually_explicit` | `minor_scholarly_disagreement` |
| `ecclesiastes-death-time-chance` | `textually_explicit` | `minor_scholarly_disagreement` |
| `ecclesiastes-god-fear-gift-judgment` | `textually_explicit` | `major_scholarly_disagreement` |
| `ecclesiastes-hebrew-greek-qumran-witnesses` | `textually_explicit` | `textual_variant` |

Every claim has a rationale and source IDs that resolve within the record.
Full wording and mappings are in
[`ecclesiastes.json`](../framework/canonical_library/objects/books/ecclesiastes.json).

## Sources used

Primary witnesses are Masoretic Ecclesiastes, Old Greek *Ecclesiast*,
4QQohᵃ, 4QQohᵇ, and New Testament passages proposed for passage-specific
canonical comparison. Independent sources added:

- Choon-Leong Seow, *Ecclesiastes* (Anchor Yale Bible Commentary; Yale
  University Press, 1997):
  <https://yalebooks.yale.edu/book/9780300139600/ecclesiastes/>
- Michael V. Fox, *The JPS Bible Commentary: Ecclesiastes* (Jewish
  Publication Society, 2004):
  <https://jps.org/books/jps-bible-commentary-ecclesiastes/>
- Stuart Weeks, *Ecclesiastes 1–5: A Critical and Exegetical Commentary*
  (International Critical Commentary; T&T Clark, 2020):
  <https://www.bloomsbury.com/us/ecclesiastes-15-9780567031136/>
- Tremper Longman III, *The Book of Ecclesiastes*, 2nd ed. (NICOT; Eerdmans,
  2026):
  <https://www.eerdmans.com/9780802879059/the-book-of-ecclesiastes-2nd-ed/>
- Craig G. Bartholomew, *Ecclesiastes* (Baker Commentary on the Old Testament
  Wisdom and Psalms; Baker Academic, 2009):
  <https://dev.bakeracademic.com/p/Ecclesiastes-Craig-G-Bartholomew/41449>
- Peter Enns, *Ecclesiastes* (Two Horizons Old Testament Commentary;
  Eerdmans, 2011):
  <https://www.eerdmans.com/9780802866493/ecclesiastes/>
- Mette Bundvad, *Time in the Book of Ecclesiastes* (Oxford University Press,
  2015):
  <https://academic.oup.com/book/7347>
- Douglas B. Miller, *Symbol and Rhetoric in Ecclesiastes* (Society of
  Biblical Literature, 2002):
  <https://cart.sbl-site.org/books/065002P>
- Mette Bundvad, “Ecclesiastes,” in *The Cambridge Companion to Biblical
  Wisdom Literature* (Cambridge University Press, 2022):
  <https://www.cambridge.org/core/books/abs/cambridge-companion-to-biblical-wisdom-literature/ecclesiastes/88E7F86EA58E601F569CFD4FDACE14E0>
- Erhard S. Gerstenberger, “Qoheleth in the Writings,” in *The Oxford
  Handbook of the Writings of the Hebrew Bible* (Oxford University Press,
  2018):
  <https://academic.oup.com/edited-volume/28060/chapter-abstract/212046332>
- Peter J. Gentry, *A New English Translation of the Septuagint:
  Ecclesiast* (IOSCS, 2009):
  <https://ccat.sas.upenn.edu/nets/edition/26-eccles-nets.pdf>
- University of Southern California, West Semitic Research Project,
  “Qohelet (Ecclesiastes),” 4Q109:
  <https://dornsife.usc.edu/wsrp/qohelet-ecclesiastes/>
- Israel Antiquities Authority, Leon Levy Dead Sea Scrolls Digital Library,
  “4Q Qohelet,” 4Q110:
  <https://iaa-dss.appspot.com/explore-the-archive/manuscript/4Q110-1>
- Arthur Keefer, *Ecclesiastes and the Meaning of Life in the Ancient World*
  (Cambridge University Press, 2022):
  <https://www.cambridge.org/core/books/ecclesiastes-and-the-meaning-of-life-in-the-ancient-world/8F9D3CFEF326DF6FD5E7A804C0E0DFFD>
- Paul S. Fiddes, “Wisdom as a Search for the Sum of Things” (Oxford
  University Press, 2013):
  <https://academic.oup.com/book/8422/chapter/154204498>
- Jesse M. Peterson, *Qoheleth and the Philosophy of Value* (Cambridge
  University Press, 2025):
  <https://resolve.cambridge.org/core/books/qoheleth-and-the-philosophy-of-value/877B040C17EE8B9DD60174DEC7C306F7>

Publisher, university, scholarly-organization, and manuscript-library pages
establish bibliographic identity, scope, or material witness. They do not
substitute for a qualified reviewer checking each use and locator.

## Retrieval coverage

The new tests require first-place book results for:

- Solomonic authorship;
- the meaning of *hebel*;
- *yitron* and “under the sun”;
- nihilism versus enjoyment;
- Qohelet, the frame narrator, and the epilogue;
- misuse of “a time to kill” to authorize violence;
- oppression and injustice;
- depression and grief;
- aging and disability in Ecclesiastes 12;
- 4Q109 and 4Q110;
- Greek *Ecclesiast* and its title; and
- canonical differences among Proverbs, Job, and Ecclesiastes.

All pass with the existing retrieval implementation. Exact safety-critical
aliases and semantic terms were added to the book record; no ranking-code
change was needed.

## Human review checklist

Verify:

- the bounds and voice of the superscription, opening poem, Qohelet discourse,
  closing refrain, epilogue, and every proposed editorial comment;
- whether the royal experiment is persona, fiction, autobiography, quotation,
  or another literary strategy, and what “son of David” can establish;
- every authorship, unity, redaction, institutional setting, audience, and
  date proposal;
- late Hebrew, Aramaisms, Persian loanwords, alleged Greek influence, and the
  terminus supplied by 4QQohᵃ;
- *qohelet*, *hebel*, *habel habalim*, *yitron*, *amal*, *heleq*,
  *simhah*, *tov*, *hokmah*, folly terms, *et*, *olam*, *miqreh*, *ruach*,
  and fear-of-God expressions in every cited context;
- whether each occurrence of “under the sun” and “under heaven” is represented
  accurately without importing a later two-world scheme;
- the royal projects, enslaved labor in 2:7, property, agriculture, trade,
  political hierarchy, taxes, wealth, inheritance, consumption, poverty,
  exploited labor, and social class;
- the enjoyment refrains in relation to gift, portion, toil, death, grief,
  oppression, privilege, irony proposals, and the book's final shape;
- the grammar, paired structure, agency, determinism, providence, and ethical
  reception of the time poem;
- observations concerning oppression, tears, absent comforters, corrupt
  judgment, rulers, officials, poor wisdom, delayed justice, and repair;
- wisdom's comparative value and its limits under death, chance, political
  power, lost memory, and God's inscrutability;
- human and animal death, Sheol or grave language, dust, breath or spirit,
  remembrance, afterlife claims, judgment, and later resurrection reception;
- the imagery and textual difficulties of 12:1–7 without forcing a single
  clinical body chart or demeaning older and disabled people;
- every claim concerning God as giver, actor, judge, and object of fear, and
  the relation of 12:13–14 to the preceding discourse;
- the contents, paleographic ranges, readings, and limits of 4QQohᵃ and
  4QQohᵇ;
- the title, base text, translation profile, variants, date, and possible
  Aquila relationship of Greek *Ecclesiast*;
- ancient Egyptian, Mesopotamian, Greek, Persian, and Hellenistic comparisons
  without claiming direct dependence beyond evidence;
- canonical comparison with Genesis, Psalms, Proverbs, Job, Sirach, and
  Wisdom of Solomon while preserving each book's literary voice;
- every proposed New Testament resonance, distinguishing shared vocabulary,
  quotation, allusion, analogy, typology, and later doctrine;
- Jewish canon discussion and Sukkot reading without projecting later
  reception into composition;
- Christian ascetic, christological, existential, resurrection, and
  new-creation readings without making earthly life or embodied joy worthless;
- all safeguards involving violence, abuse, suicide risk, clinical
  depression, trauma, grief, aging, disability, exploitation, overwork,
  poverty, wealth, victim-blaming, and access to care;
- every source locator, support target, certainty label, dispute label, and
  pastoral application.

Do not advance the record merely because automated checks pass. Advance only
the sections actually reviewed, and record reviewer identity and date.

## Verification

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/ecclesiastes.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests/canonical_library/test_ecclesiastes_record.py \
  tests/canonical_library/test_proverbs_record.py \
  tests/canonical_library/test_psalms_record.py \
  tests/canonical_library/test_job_record.py \
  tests/canonical_library/test_golden_queries.py \
  tests/canonical_library/test_manifest.py
# 42 tests in 40.779s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 292 tests in 141.295s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 known migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,154 edges, 0 unknown targets, 0 orphaned objects
# 2,722 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave13-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave13-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# c9a455182562a0643598288b46d959ee6db480cce1ef354d8f3f022e0db7f257
```

Known Python 3.14 unclosed-SQLite `ResourceWarning` messages remain nonfatal
test-environment noise; they did not produce test failures.

## What remains

- A qualified human reviewer must complete the checklist above and update only
  the sections actually reviewed.
- The 14 library-wide validator warnings and 2,722 reciprocal suggestions are
  pre-existing migration debt, not Ecclesiastes errors.
- Phase 5 now has twenty-one corrected book drafts and forty-five books
  remaining.
- The next controlled correction wave is Song of Songs.
