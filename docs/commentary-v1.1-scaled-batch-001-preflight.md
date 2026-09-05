# Commentary v1.1 Scaled Batch 001 Evidence Preflight

This is a Luna deterministic evidence certification. Terra was not run and no reader-facing prose was generated.

## Selection and population

- Candidate pool: 70 chapters; target: 50; evaluated: 70.
- Current deterministic low-information population: 935 eligible and 153 insufficient (historical reference: 935 / 153).
- Mixed selection: genre/availability round-robin, reader-benefit signals for ordering only, maximum five chapters per book in the pool.
- Replacements used: 3.

## Final certification

- Status: **LOCKED**
- Final locked chapters: 50
- Availability: {'AVAILABLE': 26, 'THIN': 24}
- Genre: {'apocalyptic': 6, 'gospel': 8, 'law': 6, 'narrative': 8, 'poetry': 7, 'prophecy': 8, 'wisdom': 7}
- Evidence count statistics: {'min': 1, 'median': 3.0, 'mean': 7.44, 'max': 78, 'distribution': {1: 17, 2: 7, 3: 6, 4: 1, 5: 5, 6: 1, 7: 2, 8: 1, 9: 2, 13: 2, 14: 1, 17: 1, 19: 1, 27: 1, 67: 1, 78: 1}}

## Final PASS chapters

Daniel 9, Matthew 23, Acts 7, Psalms 78, Ezekiel 43, Ecclesiastes 9, Revelation 3, Matthew 8, Leviticus 21, 1 Chronicles 29, Psalms 79, Ezekiel 8, Proverbs 29, Revelation 16, Matthew 12, Deuteronomy 28, 2 Chronicles 35, Lamentations 2, Isaiah 66, Matthew 11, Deuteronomy 15, 2 Chronicles 26, Psalms 132, Isaiah 62, Proverbs 14, Daniel 11, Luke 11, 2 Kings 23, Lamentations 4, Jeremiah 51, Proverbs 30, Luke 20, Leviticus 13, 2 Chronicles 29, Psalms 18, Jeremiah 19, Proverbs 17, Revelation 1, Luke 22, Deuteronomy 7, Joel 2, Psalms 89, Jeremiah 33, Ecclesiastes 8, Luke 16, Leviticus 14, 1 Chronicles 16, Ezekiel 11, Proverbs 7, Revelation 11

## Candidate pool

Daniel 9, Matthew 23, Deuteronomy 32, Acts 7, Psalms 78, Ezekiel 43, Ecclesiastes 9, Revelation 3, Matthew 8, Leviticus 21, 1 Chronicles 29, Psalms 79, Ezekiel 8, Proverbs 29, Revelation 16, Matthew 12, Deuteronomy 28, 2 Chronicles 35, Lamentations 2, Isaiah 66, Job 1, Matthew 11, Deuteronomy 15, 2 Chronicles 26, Psalms 132, Isaiah 62, Proverbs 14, Daniel 11, Luke 11, Leviticus 19, 2 Kings 23, Lamentations 4, Jeremiah 51, Proverbs 30, Luke 20, Leviticus 13, 2 Chronicles 29, Psalms 18, Jeremiah 19, Proverbs 17, Revelation 1, Luke 22, Deuteronomy 7, Joel 2, Psalms 89, Jeremiah 33, Ecclesiastes 8, Luke 16, Leviticus 14, 1 Chronicles 16, Ezekiel 11, Proverbs 7, Revelation 11, Matthew 24, Leviticus 16, Acts 5, Jeremiah 32, 2 Samuel 15, Ezekiel 23, Daniel 8, Luke 2, Deuteronomy 18, 2 Chronicles 20, Ezekiel 24, Job 15, 1 Kings 3, Isaiah 47, Revelation 20, Numbers 14, Haggai 2

## Quarantines

- **Deuteronomy 32** — CROSS_BOOK_PARENT_REUSE, WORD_STUDY_BROAD_PARENT_ANCHOR. One non-lexical CKL parent is attached across unrelated books in the evaluated pool.; One non-lexical CKL parent is attached across unrelated books in the evaluated pool.; The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.
- **Job 1** — CROSS_BOOK_PARENT_REUSE. One non-lexical CKL parent is attached across unrelated books in the evaluated pool.; One non-lexical CKL parent is attached across unrelated books in the evaluated pool.
- **Leviticus 19** — WORD_STUDY_BROAD_PARENT_ANCHOR. The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.; The word-study parent has a broad or cross-book authored anchor set.

## Anomaly patterns

- Word-study anomalies: 8
- Archaeology anomalies: 0
- Later-reception anomalies: 0
- Broad-anchor anomalies: 12
- Presentation-role anomalies: 0
- Template-evidence anomalies: 0
- Evidence-count outliers: 9 review signals; none auto-quarantined.

## Regression controls

- **Genesis 1** — PASS: no archaeology entities/items; no word studies
- **Zephaniah 1** — PASS: Josiah-era overview retained
- **Luke 1** — PASS: Luke-Acts relation is language_literary
- **Leviticus 1** — PASS: ritual context is historical_context
- **1 Samuel 28** — PASS: THIN; two evidence items; apparition disputed
- **Numbers 3** — PASS: DATA_GAP; zero evidence
- **canary_artifacts** — PASS: 26 prose-control artifact fingerprints unchanged

## Systemic CKL concern

Template-shaped CKL background and cross-testament reception records remain a systemic review surface. This batch quarantines only deterministic semantic/presentation blockers; it does not repair CKL records. Any repeated template or broad-parent pattern should be handled in a separate Luna evidence-cleanup task.

The batch is eligible for a future Terra Medium Batch 001 generation only after the locked manifest is consumed and its hashes are rechecked immediately before generation.
