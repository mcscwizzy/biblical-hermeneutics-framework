# ED-3 research-depth priorities

## Purpose and method

This is a source-led backlog for later, bounded research. It does not authorize a new evidence wave and it does not treat filling every chapter gap as the goal. The underlying chapter inventory is the ED-2 master [research backlog](../ed2-master/research-backlog.csv), with 1,189 unique book/chapter rows. Phase 7 also reran `ckl_coverage_report.py` against the current branch. Its JSON report was written outside the repository to `/tmp/ed3-current-coverage.json` (SHA-256 `d2b33bfe6c63c15c44113f26935661052cd8307813d5c8ea4a5211154e2b416c`); command: `.venv/bin/python tools/ckl_coverage_report.py --json /tmp/ed3-current-coverage.json`. The audit covers all 1,189 chapters.

Priorities consider: (1) historical/cultural opportunity; (2) whether credible primary editions, inscriptions, manuscript witnesses, or archaeological publications can be accessed; (3) linguistic and literary complexity; (4) current passage-level depth and source traceability; (5) reader value; and (6) uncertainty and the effort needed to verify a claim. A high uncertainty score triggers specialist review, not automatic expansion. P0 means a strong case for planning a small source-verifiable investigation; P1 means a real depth, scope, or review gap; P2 means a focused opportunity when sources or reader need justify it; P3 means monitor and work only when a specific question merits it. These are editorial priorities, not quality ratings.

## Reproduced chapter census

| Category | Chapters |
|---|---:|
| Passage-specific CKL material | 1,089 |
| Contextual-only | 56 |
| Entity-only | 2 |
| No eligible CKL material | 41 |
| Incomplete/unknown | 1 |
| **Total** | **1,189** |

Zero-eligible chapters remain: **Numbers** 3, 5, 7, 8; **1 Kings** 2, 5, 7, 10, 13; **2 Kings** 1, 6, 7, 11, 12, 13; **1 Chronicles** 14, 18, 19; **2 Chronicles** 2, 4, 8, 9, 17, 21, 22, 23, 27; **Proverbs** 5, 12, 13, 18, 19, 20, 21; **Ezekiel** 6, 7, 15, 19, 21, 29, 30. The chapter lists are eligibility signals only.

Contextual-only chapters (56): **Numbers** 6, 11, 12, 15, 17, 21, 25; **1 Kings** 4, 6, 16, 20; **2 Kings** 3, 8, 20, 21; **1 Chronicles** 2, 4, 5, 7, 8, 20, 24, 25, 26, 27; **2 Chronicles** 24; **Nehemiah** 7; **Esther** 10; **Psalms** 36, 54, 68, 84, 85, 93, 95, 104, 112, 136; **Proverbs** 3; **Ezekiel** 4, 5, 12, 14, 17, 20, 35, 41, 42, 44, 45, 46; **Amos** 4, 6; **Zechariah** 10; **Luke** 9, 14. Entity-only: **1 Kings 14** and **2 Chronicles 13**. **Obadiah 1** remains incomplete/unknown and needs a census/anchor check.

## Thin-depth signals already in covered chapters

The independent strict chapter retrieval scan (report version 2.0, 2026-11-11) found 669 chapters with at least two eligible CKL items, 479 with exactly one, and 41 with none. Thus 1,148 chapters have at least one strict passage retrieval, while 479 are a one-item signal that merits qualitative checking. The strict report’s evidence-count distribution is 223 chapters with 6+ items, 446 with 2–5, 479 with 1, and 41 with 0; mean 4.12, median 2. The detailed ED-2 taxonomy separately reports 1,089 passage-specific chapters, 56 contextual-only, 2 entity-only, 41 with no eligible material, and 1 incomplete/unknown. These are different measures: the strict scan counts retrieved CKL records, while the ED-2 taxonomy distinguishes passage-specific from contextual/entity eligibility. Do not substitute one for the other.

Across the detailed ledger, 268 passage-specific chapters have at most two eligible CKL items. There are 494 unique candidate chapters in the union of those 268 and the 479 strict one-item chapters (253 overlap). The [thin-passage candidate CSV](thin-passage-candidates.csv) provides both measures, typed evidence counts, source traceability, historical/language/literary/primary-source counts, and any ED-2 IDs. These are screening signals, not judgments of scholarly adequacy or instructions to author 494 items. A single well-sourced item can be useful; several items can still leave important questions unanswered.

The largest strict one-item concentrations are Psalms (116 chapters), Jeremiah (34), Isaiah and Ezekiel (31 each), 1 Chronicles (22), 1 Samuel (20), 2 Chronicles (18), 2 Samuel (17), Deuteronomy (13), and Numbers (12). Select individual passages only where a source-accessible question has reader value; primary witness inspection and source verification may be the correct deliverable even when no CKL wording changes.

## Book-by-book backlog

The detailed vector is **specific / contextual-only / entity-only / zero-eligible / incomplete**. Strict retrieval is **two-or-more / one / zero** items from `ckl_coverage_report.py`.

| Book | Detailed census S/C/E/0/? | Strict direct retrieval ≥2 / 1 / 0 | Specific chapters with ≤2 eligible items | Priority and source-led next question |
|---|---|---|---:|---|
| Genesis | 50/0/0/0/0 | 50 / 0 / 0 | 0 | **P3.** Separate comparative literature and later reception from direct evidence about narrated events; require chronology and source locators. |
| Exodus | 40/0/0/0/0 | 35 / 5 / 0 | 0 | **P2.** Test historical reconstructions against Egyptian/regional inscriptions and archaeology; separate narrated event, proposed date, composition, and transmission. |
| Leviticus | 27/0/0/0/0 | 17 / 10 / 0 | 9 | **P1.** Prioritize ritual vocabulary, priestly textual history, and bounded comparisons with ancient law/ritual corpora. |
| Numbers | 25/7/0/4/0 | 20 / 12 / 4 | 8 | **P0.** Compare census, itinerary, and ritual claims with exact editions, inscription records, and site surveys; leave uncertain wilderness identifications open. |
| Deuteronomy | 34/0/0/0/0 | 21 / 13 / 0 | 11 | **P1.** Review treaty/law comparisons against primary editions and Hebrew/Old Greek evidence; distinguish analogy from direct dependence. |
| Joshua | 24/0/0/0/0 | 15 / 9 / 0 | 3 | **P2.** Use site-specific stratigraphy and inscription reports; do not generalize one site’s chronology to the full conquest narrative. |
| Judges | 21/0/0/0/0 | 14 / 7 / 0 | 0 | **P3.** Use material and inscriptional evidence for named places, peoples, and practices; prioritize precise claims over generalized setting. |
| Ruth | 4/0/0/0/0 | 4 / 0 / 0 | 0 | **P3.** Review gleaning, kinship, and land-redemption language against Hebrew usage and legal texts without treating analogy as identity. |
| 1 Samuel | 31/0/0/0/0 | 11 / 20 / 0 | 15 | **P1.** Check Philistine/Israelite material-culture claims and royal institutions against published excavation and inscription records. |
| 2 Samuel | 24/0/0/0/0 | 7 / 17 / 0 | 12 | **P1.** Verify dynastic, geographic, and royal claims against inscriptions and archaeology; keep narrated reign, event, and composition distinct. |
| 1 Kings | 12/4/1/5/0 | 10 / 7 / 5 | 3 | **P0.** Test Omride, royal, and regional claims against published Mesha/Assyrian inscriptions and site reports; separate royal propaganda from narrative. |
| 2 Kings | 15/4/0/6/0 | 15 / 4 / 6 | 0 | **P0.** Prioritize Assyrian and Babylonian royal accounts, siege/deportation evidence, and exact archaeological publication links. |
| 1 Chronicles | 16/10/0/3/0 | 4 / 22 / 3 | 7 | **P0.** Compare selected passages with Samuel–Kings and published temple/Persian-period evidence; do not infer composition date from a parallel alone. |
| 2 Chronicles | 25/1/1/9/0 | 9 / 18 / 9 | 16 | **P0.** Review Kings parallels, temple/cult claims, and external inscriptions with object identity and publication provenance. |
| Ezra | 10/0/0/0/0 | 8 / 2 / 0 | 0 | **P3.** Compare administrative and diaspora claims with Achaemenid documentary collections and published editions. |
| Nehemiah | 12/1/0/0/0 | 5 / 8 / 0 | 0 | **P2.** For chapter 7, compare personnel/administrative claims with published Persian-period documentary editions and avoid unsupported name matches. |
| Esther | 9/1/0/0/0 | 2 / 8 / 0 | 0 | **P2.** Review Persian court and diaspora setting through comparative texts and Greek/Hebrew transmission; parallels alone do not establish a specific event. |
| Job | 42/0/0/0/0 | 42 / 0 / 0 | 0 | **P3.** Prioritize identifiable Hebrew lexemes, poetic form, and edited ancient wisdom parallels; state where analogy ends. |
| Psalms | 140/10/0/0/0 | 34 / 116 / 0 | 115 | **P1.** Select a few of the 115 low-count chapters where manuscripts/versions, superscriptions, poetic structure, cultic context, or reception have verifiable editions. |
| Proverbs | 23/1/0/7/0 | 5 / 19 / 7 | 14 | **P0.** Compare MT and Old Greek witnesses and Hebrew vocabulary with critical editions and bounded ancient wisdom parallels. |
| Ecclesiastes | 12/0/0/0/0 | 1 / 11 / 0 | 2 | **P2.** Resolve low-count chs. 4 and 10 through Hebrew syntax and legitimate commentary locators; keep date proposals attributed. |
| Song of Songs | 8/0/0/0/0 | 0 / 8 / 0 | 0 | **P3.** Use Hebrew poetic language and edited love-poetry comparisons; distinguish genre resemblance from literary dependence. |
| Isaiah | 66/0/0/0/0 | 35 / 31 / 0 | 23 | **P1.** Use the Great Isaiah Scroll and other witnesses, imperial-era inscriptions, and literary seam studies only where the claim has an exact locator. |
| Jeremiah | 52/0/0/0/0 | 18 / 34 / 0 | 8 | **P1.** Prioritize MT/Old Greek comparison and dated Babylonian-period documents; separate narrated event, composition, and transmission. |
| Lamentations | 5/0/0/0/0 | 2 / 3 / 0 | 0 | **P3.** Focus on Hebrew poetic form and witnesses; do not derive a single date from genre alone. |
| Ezekiel | 29/12/0/7/0 | 10 / 31 / 7 | 14 | **P0.** Review exilic chronology, Hebrew/versional readings, and temple measurements using critical editions and qualified Babylonian-period studies. |
| Daniel | 12/0/0/0/0 | 8 / 4 / 0 | 0 | **P2.** Compare Aramaic/Hebrew usage, manuscript witnesses, and Persian/Seleucid context; distinguish setting, composition, and manuscript dates. |
| Hosea | 14/0/0/0/0 | 6 / 8 / 0 | 1 | **P2.** For ch. 5 and related cultic language, verify Hebrew idiom with lexicons and inscriptional contexts at exact locators. |
| Joel | 3/0/0/0/0 | 2 / 1 / 0 | 0 | **P3.** Treat locust imagery, cultic setting, and proposed date as separate questions; require direct comparative sources. |
| Amos | 7/2/0/0/0 | 4 / 5 / 0 | 0 | **P2.** For contextual-only chs. 4 and 6, check social and place claims against published archaeology/inscriptions and Hebrew rhetoric. |
| Obadiah | 0/0/0/0/1 | 1 / 0 / 0 | 0 | **P1.** Resolve the single-chapter anchor/identity and retrieval pathway first; treat this as a census issue until repaired. |
| Jonah | 4/0/0/0/0 | 2 / 2 / 0 | 0 | **P2.** Check claims about Nineveh and Assyria against published evidence without assuming genre or date. |
| Micah | 7/0/0/0/0 | 3 / 4 / 0 | 0 | **P2.** Tie named-place and Assyrian-period claims to published sources while preserving uncertainty about composition. |
| Nahum | 3/0/0/0/0 | 3 / 0 / 0 | 0 | **P2.** Human review should lead; any follow-up should directly inspect Qumran/Greek witnesses and published Nineveh excavation reports. |
| Habakkuk | 3/0/0/0/0 | 1 / 2 / 0 | 0 | **P2.** Keep historical reference separate from Qumran reception; the Habakkuk Pesher documents reception, not original referent. |
| Zephaniah | 3/0/0/0/0 | 3 / 0 / 0 | 0 | **P3.** Review Josianic/Assyrian horizons only where sources separate narrated threat, composition, and transmission. |
| Haggai | 2/0/0/0/0 | 2 / 0 / 0 | 0 | **P2.** Use Persian-period dated notices and temple reconstruction evidence with primary editions that expose chronology and provenance. |
| Zechariah | 13/1/0/0/0 | 10 / 4 / 0 | 1 | **P2.** Review ch. 10’s context and Persian-period proposals with Hebrew/Greek edition evidence and explicitly attributed dating. |
| Malachi | 4/0/0/0/0 | 4 / 0 / 0 | 0 | **P2.** Resolve `patristic-minor-prophets` locator from the collection contents or a defensible section locator before further research. |
| Matthew | 28/0/0/0/0 | 22 / 6 / 0 | 2 | **P2.** For chs. 8–9, pursue only a bounded Greek/Semitic lexical or source-relation question whose source can be inspected. |
| Mark | 16/0/0/0/0 | 14 / 2 / 0 | 0 | **P1.** For 7:3, examine critical apparatus and manuscript/version evidence before making cultural or lexical claims about the disputed reading. |
| Luke | 22/2/0/0/0 | 17 / 7 / 0 | 4 | **P1.** Select one passage on Greek syntax, women’s roles, meals, or Sabbath practice and verify it against an exact primary text and bounded historical source. |
| John | 21/0/0/0/0 | 18 / 3 / 0 | 0 | **P2.** Chapter eligibility is complete; work only on a specific, sourced textual, lexical, or historical question. |
| Acts | 28/0/0/0/0 | 28 / 0 / 0 | 0 | **P2.** Select specific civic, legal, epigraphic, or travel claims and compare them with local inscriptions and institutional editions. |
| Romans | 16/0/0/0/0 | 16 / 0 / 0 | 0 | **P3.** Coverage is dense; preserve bounded, source-located work on Greek rhetoric or Second Temple texts. |
| 1 Corinthians | 16/0/0/0/0 | 16 / 0 / 0 | 0 | **P3.** Review social, cultic, and lexical claims before adding more; ground Corinth-specific context in published records. |
| 2 Corinthians | 13/0/0/0/0 | 13 / 0 / 0 | 0 | **P3.** Add only where manuscript, rhetoric, or historical reconstruction is tied to an exact source and passage. |
| Galatians | 6/0/0/0/0 | 6 / 0 / 0 | 0 | **P3.** Maintain distinctions among Paul’s rhetoric, narrated audience, and later reception; prioritize lexical verification. |
| Ephesians | 6/0/0/0/0 | 5 / 1 / 0 | 0 | **P3.** Pursue Greek lexical/intertextual questions only when the cited source and passage locator are exact. |
| Philippians | 4/0/0/0/0 | 4 / 0 / 0 | 0 | **P3.** Review Roman-colony context where specific epigraphic or documentary evidence changes passage interpretation. |
| Colossians | 4/0/0/0/0 | 4 / 0 / 0 | 0 | **P3.** Limit work on the opponents to claims supported by an identifiable source and passage-level evidence. |
| 1 Thessalonians | 5/0/0/0/0 | 5 / 0 / 0 | 0 | **P3.** Target specific civic, cultic, or lexical claims; separate local context from assumptions about the community. |
| 2 Thessalonians | 3/0/0/0/0 | 2 / 1 / 0 | 0 | **P3.** Keep authorship, apocalyptic language, and textual claims attributed and disputed. |
| 1 Timothy | 6/0/0/0/0 | 4 / 2 / 0 | 0 | **P3.** Focus on verifiable lexical and social-institutional context tied to the letter’s stated setting. |
| 2 Timothy | 4/0/0/0/0 | 3 / 1 / 0 | 0 | **P3.** Use exact language, transmission, or historical questions; do not state contested authorship conclusions as fact. |
| Titus | 3/0/0/0/0 | 2 / 1 / 0 | 0 | **P3.** For Cretan context or Greek usage, tie each proposal to a traceable source and separate setting from authorship chronology. |
| Philemon | 1/0/0/0/0 | 1 / 0 / 0 | 0 | **P3.** If pursued, focus on slavery/household status or letter rhetoric with carefully qualified comparative sources. |
| Hebrews | 13/0/0/0/0 | 10 / 3 / 0 | 0 | **P3.** Compare Greek Scripture and Second Temple texts at exact locators; distinguish scriptural reuse from later reception. |
| James | 5/0/0/0/0 | 4 / 1 / 0 | 0 | **P3.** Use Greek and wisdom-literature comparisons where primary texts can be inspected; keep date/author proposals separate. |
| 1 Peter | 5/0/0/0/0 | 4 / 1 / 0 | 0 | **P3.** Distinguish provincial context, scriptural reuse, and later reception; attach a date and source to each. |
| 2 Peter | 3/0/0/0/0 | 3 / 0 / 0 | 0 | **P3.** Prioritize Greek, intertext, and textual history; retain authorship and dating dispute. |
| 1 John | 5/0/0/0/0 | 4 / 1 / 0 | 0 | **P3.** Continue only for a specific Greek, literary, or early reception question with exact source support. |
| 2 John | 1/0/0/0/0 | 1 / 0 / 0 | 0 | **P3.** A future question should test epistolary form or social setting with direct comparative evidence. |
| 3 John | 1/0/0/0/0 | 1 / 0 / 0 | 0 | **P3.** Focus on verifiable epistolary conventions or early reception rather than broad historical certainty. |
| Jude | 1/0/0/0/0 | 1 / 0 / 0 | 0 | **P3.** Verify intertexts and reception separately using the source text actually cited; preserve disputed identifications. |
| Revelation | 22/0/0/0/0 | 18 / 4 / 0 | 0 | **P1.** Prioritize city-specific Asia Minor inscriptions, civic cult records, and Greek witnesses; avoid one-to-one identifications without local primary evidence. |

## Recommended sequence

1. **P0 planning set:** Numbers, 1 Kings, 2 Kings, 1 Chronicles, 2 Chronicles, Proverbs, Ezekiel. Select a few passages where an accessible primary text, critical edition, or excavation publication answers a reader-relevant question; complete a source packet and independent review before any writing.
2. **P1 depth and provenance checks:** Psalms, 1 Samuel, 2 Samuel, Deuteronomy, Leviticus, Isaiah, Jeremiah, Mark, Luke, Revelation, and Obadiah. Use the thin-candidate data and specific gaps above to choose bounded cases; source and textual verification may be the work product even when no new evidence is warranted.
3. **P2 targeted opportunities:** contextual-only chapters and other focused questions where a source-led task can be answered cleanly. First establish exact passage eligibility and traceable bibliography.
4. **P3 watchlist:** retain coverage, but add material only when a specific historical, linguistic, literary, or reader question has a strong source path.

No held or excluded NE-10 relationship is a backlog candidate for promotion by this process. Research depth review does not modify NE-9C/NE-10 governance or frozen checkpoints.
