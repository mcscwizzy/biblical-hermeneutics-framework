# Genesis Evidence Gap Report — G0

Transaction: `GENESIS_G0_EVIDENCE_CENSUS`

This is a read-only baseline. It measures current CKL retrieval, compiled synthesis, and published Commentary v1.2 separately. It does not authorize evidence generation or Commentary regeneration.

## Whole-book totals

- Chapters audited: 50 / 50
- CKL evidence items across chapter bundles (chapter-local counts; cross-chapter reuse is counted per chapter): 799
- Distinct evidence IDs: 350; distinct source IDs: 326.
- Coverage: GOOD 3, THIN 3, SPARSE 6, GAP 38
- Evidence categories: `{"chronology": 32, "culture": 461, "geography": 72, "history": 227, "social": 7}`

- CKL runtime: JSON fallback under CKLRepositoryConfig.stale_database_policy=fallback_to_json; local SQLite fingerprint matches JSON inventory: False. The SQLite database was not changed.

## Chapter census

| Chapter | CKL items | Synthesis units | Categories | Sources | Commentary sections / blocks | Status | Main gap taxonomy |
|---:|---:|---:|---|---:|---:|---|---|
| 1 | 58 | 12 | chronology, culture, geography, history, social | 66 | 1 / 1 | GOOD | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 2 | 41 | 9 | chronology, culture, geography, history, social | 45 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 3 | 13 | 5 | culture, geography, history | 20 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 4 | 19 | 5 | culture, geography, history | 18 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 5 | 19 | 9 | culture, geography, history | 32 | 3 / 3 | GOOD | EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 6 | 13 | 7 | culture, geography, history | 20 | 1 / 1 | THIN | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 7 | 11 | 5 | culture, geography, history | 13 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 8 | 13 | 5 | culture, geography, history | 21 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 9 | 69 | 5 | culture, geography, history, social | 68 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 10 | 56 | 3 | culture, geography, history | 47 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 11 | 21 | 3 | culture, geography, history | 29 | 1 / 1 | SPARSE | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 12 | 152 | 9 | chronology, culture, geography, history, social | 116 | 1 / 1 | THIN | EXISTING_OBJECT_ENRICHMENT_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 13 | 6 | 5 | culture, geography | 5 | 2 / 2 | SPARSE | EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 14 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 15 | 69 | 11 | chronology, culture, geography, history, social | 60 | 1 / 1 | GOOD | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 16 | 4 | 4 | culture | 7 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 17 | 50 | 8 | chronology, culture, geography, history, social | 45 | 1 / 1 | THIN | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 18 | 7 | 5 | culture, history | 14 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 19 | 5 | 5 | culture | 9 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 20 | 4 | 4 | culture | 7 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 21 | 7 | 5 | culture, history | 13 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 22 | 38 | 4 | chronology, culture, geography, history, social | 35 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 23 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 24 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 25 | 4 | 4 | culture | 6 | 1 / 1 | SPARSE | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 26 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 27 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 28 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 29 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 30 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 31 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 32 | 5 | 3 | culture, history | 8 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 33 | 12 | 3 | culture, geography, history | 12 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 34 | 5 | 5 | culture, geography | 5 | 2 / 3 | SPARSE | EXISTING_OBJECT_ENRICHMENT_REQUIRED |
| 35 | 10 | 3 | culture, geography, history | 8 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 36 | 4 | 4 | culture | 7 | 1 / 1 | SPARSE | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED, PASSAGE_APPLICABILITY_REQUIRED |
| 37 | 11 | 3 | culture, geography, history | 9 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 38 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 39 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 40 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 41 | 5 | 3 | culture, history | 9 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 42 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 43 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 44 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 45 | 5 | 3 | culture, history | 9 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 46 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 47 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 48 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 49 | 3 | 3 | culture | 4 | 1 / 1 | GAP | COMMENTARY_ONLY_ISSUE, NEW_CKL_EVIDENCE_REQUIRED |
| 50 | 6 | 4 | culture, history | 10 | 2 / 2 | SPARSE | COMMENTARY_ONLY_ISSUE, EXISTING_OBJECT_ENRICHMENT_REQUIRED |

## Strongest and weakest chapters

Strongest by status, synthesis breadth, then retrieved count: Genesis 1 (GOOD, 58 items / 12 units), Genesis 15 (GOOD, 69 items / 11 units), Genesis 5 (GOOD, 19 items / 9 units), Genesis 12 (THIN, 152 items / 9 units), Genesis 2 (GAP, 41 items / 9 units), Genesis 17 (THIN, 50 items / 8 units), Genesis 6 (THIN, 13 items / 7 units), Genesis 9 (GAP, 69 items / 5 units), Genesis 4 (GAP, 19 items / 5 units), Genesis 3 (GAP, 13 items / 5 units).

Weakest by classification and current retrieval: Genesis 14 (GAP, 3 items / 3 units), Genesis 23 (GAP, 3 items / 3 units), Genesis 24 (GAP, 3 items / 3 units), Genesis 26 (GAP, 3 items / 3 units), Genesis 27 (GAP, 3 items / 3 units), Genesis 28 (GAP, 3 items / 3 units), Genesis 29 (GAP, 3 items / 3 units), Genesis 30 (GAP, 3 items / 3 units), Genesis 31 (GAP, 3 items / 3 units), Genesis 38 (GAP, 3 items / 3 units).

## Retrieval and rendering distinctions

- Genesis evidence occurrences across chapter bundles: 799; shared items are counted once for every chapter to which the bundle admits them.
- Chapter-overlapping objects returned by CKL but yielding no admissible bundle item: 22 candidate/chapter pairs across 14 chapters.
- Chapter-overlapping objects rejected by the scripture retrieval index: 0.
- Published Commentary lineage exactly matches current prepared CKL+synthesis identities in 48 chapters: Genesis 1, Genesis 2, Genesis 3, Genesis 4, Genesis 6, Genesis 7, Genesis 8, Genesis 9, Genesis 10, Genesis 11, Genesis 13, Genesis 14, Genesis 15, Genesis 16, Genesis 17, Genesis 18, Genesis 19, Genesis 20, Genesis 21, Genesis 22, Genesis 23, Genesis 24, Genesis 25, Genesis 26, Genesis 27, Genesis 28, Genesis 29, Genesis 30, Genesis 31, Genesis 32, Genesis 33, Genesis 34, Genesis 35, Genesis 36, Genesis 37, Genesis 38, Genesis 39, Genesis 40, Genesis 41, Genesis 42, Genesis 43, Genesis 44, Genesis 45, Genesis 46, Genesis 47, Genesis 48, Genesis 49, Genesis 50.
- Exact-lineage chapters with current synthesis units absent from published Commentary: 46 (Genesis 1, Genesis 2, Genesis 3, Genesis 4, Genesis 6, Genesis 7, Genesis 8, Genesis 9, Genesis 10, Genesis 11, Genesis 14, Genesis 15, Genesis 16, Genesis 17, Genesis 18, Genesis 19, Genesis 20, Genesis 21, Genesis 22, Genesis 23, Genesis 24, Genesis 25, Genesis 26, Genesis 27, Genesis 28, Genesis 29, Genesis 30, Genesis 31, Genesis 32, Genesis 33, Genesis 35, Genesis 36, Genesis 37, Genesis 38, Genesis 39, Genesis 40, Genesis 41, Genesis 42, Genesis 43, Genesis 44, Genesis 45, Genesis 46, Genesis 47, Genesis 48, Genesis 49, Genesis 50).
- Chapters classified below GOOD because usable CKL context remains thin or sparse: 47 (Genesis 2, Genesis 3, Genesis 4, Genesis 6, Genesis 7, Genesis 8, Genesis 9, Genesis 10, Genesis 11, Genesis 12, Genesis 13, Genesis 14, Genesis 16, Genesis 17, Genesis 18, Genesis 19, Genesis 20, Genesis 21, Genesis 22, Genesis 23, Genesis 24, Genesis 25, Genesis 26, Genesis 27, Genesis 28, Genesis 29, Genesis 30, Genesis 31, Genesis 32, Genesis 33, Genesis 34, Genesis 35, Genesis 36, Genesis 37, Genesis 38, Genesis 39, Genesis 40, Genesis 41, Genesis 42, Genesis 43, Genesis 44, Genesis 45, Genesis 46, Genesis 47, Genesis 48, Genesis 49, Genesis 50).
- Chapters whose published Commentary citations are entirely later-reception evidence: 7 (Genesis 1, Genesis 2, Genesis 3, Genesis 4, Genesis 18, Genesis 19, Genesis 22).

Candidates with chapter-overlapping anchors but no admitted bundle item: Genesis 2 → 1-corinthians, Genesis 2 → ephesians, Genesis 2 → revelation, Genesis 2 → song-of-songs, Genesis 4 → jude, Genesis 6 → jude, Genesis 7 → 1-peter, Genesis 8 → 1-peter, Genesis 9 → 1-peter, Genesis 9 → basileia, Genesis 9 → berit, Genesis 9 → diatheke, Genesis 12 → bethlehem-1, Genesis 14 → hebrews, Genesis 15 → emet, Genesis 15 → james, Genesis 15 → pistis, Genesis 18 → 3-john, Genesis 19 → jude, Genesis 21 → pauline-kinship-guardianship-slavery-and-inheritance, Genesis 25 → malachi, Genesis 36 → malachi.
The diagnostic exposes overlapping anchors, CKL retrieval match, and whether each parent admitted a Commentary bundle item. It does not expose a named reason for every filtered item; no rejection reason is invented. Synthesis-unused and Commentary-unused IDs remain separate from CKL absence.

## Existing objects and priority gaps

Relevant CKL object reuse classifications: `{"ENRICH": 1, "REUSE_AS_IS": 150}`.

Top 10 chapter-level evidence gaps (ordered by current bundle count; dimensions need human review):

- Genesis 14: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.
- Genesis 23: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, archaeology_material_culture, historical_context, hebrew_worldview_concepts.
- Genesis 24: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, archaeology_material_culture, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.
- Genesis 26: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, archaeology_material_culture, historical_context, hebrew_worldview_concepts, covenant_context.
- Genesis 27: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.
- Genesis 28: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, archaeology_material_culture, historical_context, hebrew_worldview_concepts, divine_council_spiritual_worldview, covenant_context, lexical_concepts, interpretive_disputes.
- Genesis 29: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, archaeology_material_culture, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections.
- Genesis 30: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.
- Genesis 31: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, geography, historical_context, hebrew_worldview_concepts, covenant_context, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.
- Genesis 38: 3 items; review immediate_literary_context, ancient_near_eastern_context, cultural_social_context, historical_context, hebrew_worldview_concepts, intertextual_canonical_connections, lexical_concepts, interpretive_disputes.

## Proposed expansion order

Recommended first production batch after review: **primeval_origins**. Genesis 2–4 form a contiguous high-priority gap immediately after the opening chapter; assess existing creation/fall/people objects together and retain the separately sourced Genesis 1 and 5 foundations.

- **Primeval Origins (Genesis 1–Genesis 5):** ancient_near_eastern_context, archaeology_material_culture, covenant_context, cultural_social_context, divine_council_spiritual_worldview, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, interpretive_disputes, intertextual_canonical_connections, lexical_concepts, textual_manuscript_issues; source-lock effort HIGH.
- **Flood / Post-Flood (Genesis 6–Genesis 9):** ancient_near_eastern_context, archaeology_material_culture, covenant_context, cultural_social_context, divine_council_spiritual_worldview, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, lexical_concepts, textual_manuscript_issues; source-lock effort HIGH.
- **Nations / Babel (Genesis 10–Genesis 11):** ancient_near_eastern_context, archaeology_material_culture, cultural_social_context, divine_council_spiritual_worldview, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, interpretive_disputes, intertextual_canonical_connections, lexical_concepts, textual_manuscript_issues; source-lock effort HIGH.
- **Abraham Cycle (Genesis 12–Genesis 25):** ancient_near_eastern_context, archaeology_material_culture, covenant_context, cultural_social_context, divine_council_spiritual_worldview, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, interpretive_disputes, intertextual_canonical_connections, lexical_concepts; source-lock effort HIGH.
- **Jacob / Esau Cycle (Genesis 25–Genesis 36):** ancient_near_eastern_context, archaeology_material_culture, covenant_context, cultural_social_context, divine_council_spiritual_worldview, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, interpretive_disputes, intertextual_canonical_connections, lexical_concepts; source-lock effort HIGH.
- **Joseph / Judah Cycle (Genesis 37–Genesis 50):** ancient_near_eastern_context, archaeology_material_culture, covenant_context, cultural_social_context, geography, hebrew_worldview_concepts, historical_context, immediate_literary_context, interpretive_disputes, intertextual_canonical_connections, lexical_concepts; source-lock effort HIGH.

Future work should begin with the batch that combines the weakest current coverage with the most reusable, sourceable CKL additions. No batch is approved for production changes by this report.
