# Commentary v1.1 Scaled Batch 006 Evidence Preflight

This is a Luna deterministic evidence certification. Terra was not run and no reader-facing prose was generated.

## Selection and population

- Candidate pool: 66 chapters; target: 65; evaluated: 66; skipped outside the pool: 882.
- Current deterministic low-information population: 935 eligible and 153 insufficient (historical reference: 935 / 153).
- Mixed selection: genre/availability round-robin, reader-benefit signals for ordering only, with a five-chapter-per-book soft preference that yields to the requested pool size.
- Replacements used: 0.
- Excluded prior/canary references: 882.

## Final certification

- Status: **LOCKED**
- Final locked chapters: 65
- Availability: {'AVAILABLE': 42, 'THIN': 23}
- Genre: {'law': 3, 'narrative': 20, 'poetry': 26, 'prophecy': 9, 'wisdom': 7}
- Evidence count statistics: {'min': 1, 'median': 2, 'mean': 4.57, 'p90': 10, 'p95': 13, 'max': 32, 'distribution': {1: 22, 2: 12, 3: 5, 4: 6, 5: 5, 6: 1, 7: 3, 8: 2, 9: 2, 10: 1, 11: 2, 13: 1, 18: 1, 31: 1, 32: 1}}
- Semantic relationship totals: {'BOOK_CONTEXT': 81, 'COMPARATIVE_CONTEXT': 2, 'DIRECT_CONTEXT': 135, 'GENERIC_BACKGROUND': 63, 'INTERTEXTUAL_REUSE': 2, 'LATER_RECEPTION': 14}.
- Presentation-role totals: {'archaeology_geography': 4, 'dig_deeper': 31, 'historical_context': 171, 'language_literary': 88, 'significance': 3}.

## Final PASS chapters

Numbers 17, Nahum 2, Psalms 95, Jeremiah 40, Job 27, Numbers 30, 1 Chronicles 25, Psalms 133, Jeremiah 45, Numbers 36, Amos 3, Psalms 136, Isaiah 64, Job 40, 1 Chronicles 8, Psalms 41, Isaiah 46, Song of Songs 8, Psalms 150, Ezekiel 2, Job 28, Esther 10, Isaiah 12, Job 21, Song of Songs 5, Isaiah 15, Job 25, 1 Chronicles 3, Isaiah 39, 1 Chronicles 7, Esther 7, Hosea 7, Zechariah 4, Judges 10, Zephaniah 2, Jonah 3, Song of Songs 2, Jonah 4, Hosea 14, Malachi 4, Zechariah 5, Psalms 127, Psalms 3, Psalms 85, Psalms 134, Psalms 82, Psalms 130, Isaiah 25, Psalms 114, Psalms 10, Psalms 120, Psalms 123, Psalms 129, Psalms 93, Psalms 147, Psalms 121, Psalms 125, Psalms 13, Psalms 117, Psalms 128, Job 35, Psalms 124, Psalms 126, Psalms 131, Job 8

## Candidate pool

Numbers 17, Nahum 2, Psalms 95, Jeremiah 40, Job 27, Numbers 30, 1 Chronicles 25, Psalms 133, Jeremiah 45, Numbers 36, Amos 3, Psalms 136, Isaiah 64, Job 40, 1 Chronicles 8, Psalms 41, Isaiah 46, Song of Songs 8, Psalms 150, Ezekiel 2, Job 28, Esther 10, Isaiah 12, Job 21, Song of Songs 5, Isaiah 15, Job 25, 1 Chronicles 3, Isaiah 39, 1 Chronicles 7, Esther 7, Hosea 7, Zechariah 4, Judges 10, Zephaniah 2, Jonah 3, Song of Songs 2, Jonah 4, Hosea 14, Malachi 4, Zechariah 5, Psalms 127, Psalms 3, Psalms 85, Psalms 134, Psalms 82, Psalms 130, Isaiah 25, Psalms 114, Psalms 10, Psalms 120, Psalms 123, Psalms 129, Psalms 93, Psalms 147, Psalms 121, Psalms 125, Psalms 13, Psalms 117, Psalms 128, Job 35, Psalms 124, Psalms 126, Psalms 131, Job 8, Psalms 23

## Quarantines

- **Psalms 23** — WORD_STUDY_BROAD_PARENT_ANCHOR. The word-study parent has a broad or cross-book authored anchor set.

## Anomaly patterns

- Word-study anomalies: 10
- Archaeology anomalies: 0
- Later-reception anomalies: 0
- Broad-anchor anomalies: 10
- Presentation-role anomalies: 0
- Template-evidence anomalies: 0
- Evidence-count outliers: 5 review signals; none auto-quarantined.
- Textual-evidence routing anomalies: 0.

## Luke 22 routing review

The `luke-meal-variant` claim is a direct CKL claim owned by the `luke` book parent. Its stored category is `geography`, but its claim text concerns manuscript witnesses, shorter/longer readings, and textual-variant uncertainty. The prior projector treated the legacy category as a presentation instruction and routed it to `archaeology_geography`.

The shared rule now gives narrow textual-variant signals precedence over legacy geography/archaeology facets. Luke 22 routes to `language_literary`; interpretive textual notes can route to `interpretive_questions`. The original Batch 001 lock and prose artifact remain unchanged. The reconstructed hash changed from `ffde3ebe0c02e5c41f530158730c25ed8f7122950abf4ddd4b0995588ee6230e` to `dabf2f65b9dc00872535abcca1d8d7206d24a846e5390d1e128cdc4459b204f7`, with evidence IDs unchanged, so Luke 22 requires future corrective recertification before any prose regeneration.

## Regression controls

- **Genesis 1** — PASS: no archaeology entities/items; no word studies
- **Zephaniah 1** — PASS: Josiah-era overview retained
- **Luke 1** — PASS: Luke-Acts relation is language_literary
- **Leviticus 1** — PASS: ritual context is historical_context
- **1 Samuel 28** — PASS: THIN; two evidence items; apparition disputed
- **Numbers 3** — PASS: DATA_GAP; zero evidence
- **Luke 22** — PASS: textual variant is language_literary; no textual routing blocker; no Terra textual suppression
- **canary_artifacts** — PASS: 26 prose-control artifact fingerprints unchanged
- **batch_001_terra_artifacts** — PASS: 50 Batch 001 Terra artifact fingerprints unchanged
- **batch_002_terra_artifacts** — PASS: 100 Batch 002 Terra artifact fingerprints unchanged
- **batch_003_terra_artifacts** — PASS: 150 Batch 003 Terra artifact fingerprints unchanged

## Textual routing

- Batch 002 POSSIBLE_EVIDENCE_REVIEW records audited: 27.
- Primary root-cause distribution: {'LEGACY_CATEGORY_OVERRIDE': 0, 'MISSING_CLAIM_TYPE': 10, 'MISSING_NOTE_TYPE': 0, 'MISSING_EVIDENCE_TYPE': 0, 'PARENT_METADATA_INHERITANCE': 0, 'PRESENTATION_ROLE_HEURISTIC': 7, 'TEXTUAL_WITNESS_MISCLASSIFICATION': 2, 'INTERPRETIVE_TEXTUAL_UNCERTAINTY': 8, 'OTHER': 0}.
- Contributing root-cause distribution (primary plus secondary): {'LEGACY_CATEGORY_OVERRIDE': 12, 'MISSING_CLAIM_TYPE': 10, 'MISSING_NOTE_TYPE': 0, 'MISSING_EVIDENCE_TYPE': 0, 'PARENT_METADATA_INHERITANCE': 0, 'PRESENTATION_ROLE_HEURISTIC': 15, 'TEXTUAL_WITNESS_MISCLASSIFICATION': 2, 'INTERPRETIVE_TEXTUAL_UNCERTAINTY': 8, 'OTHER': 0}.
- Deterministic precedence: explicit claim_type, note_type, evidence_type, source_kind, semantic relationship, parent type, then a narrow claim-text fallback; physical manuscript discovery remains archaeology while manuscript-reading claims route to language/textual context.
- Corpus scan: 66 regeneration-eligible chapters and 22 textual records; 15 chapters affected.
- Routing before: {'historical_context': 17, 'language_literary': 5}.
- Routing after: {'language_literary': 22}.
- Routing corrections: {'historical_context -> language_literary': 17}.
- Interpretive_questions assignments: 0; Dig Deeper assignments: 0.
- Unresolved ambiguous cases: [].
- Historical reconstructed hash-impact records: 40; Terra-omitted affected items: 17; regeneration recommendations: 10.
- Terra suppression simulation: 0 evaluated chapters required suppression; final 150 required none.

## Audit detail

- Candidate pool: 66; evaluated: 66; PASS: 65; QUARANTINE: 1; DATA_GAP: 0; replacements: 0; final locks: 65.
- Verdict counts including manifest-derived exclusions: {'PASS': 65, 'QUARANTINE': 1, 'SKIP_ALREADY_GENERATED': 600, 'SKIP_CANARY': 26, 'SKIP_PRIOR_QUARANTINE': 256}.
- Availability: {'AVAILABLE': 42, 'THIN': 23}; genres: {'law': 3, 'narrative': 20, 'poetry': 26, 'prophecy': 9, 'wisdom': 7}; books: {'1 Chronicles': 4, 'Amos': 1, 'Esther': 2, 'Ezekiel': 1, 'Hosea': 2, 'Isaiah': 6, 'Jeremiah': 2, 'Job': 7, 'Jonah': 2, 'Judges': 1, 'Malachi': 1, 'Nahum': 1, 'Numbers': 3, 'Psalms': 26, 'Song of Songs': 3, 'Zechariah': 2, 'Zephaniah': 1}.
- Evidence statistics: {'min': 1, 'median': 2, 'mean': 4.57, 'p90': 10, 'p95': 13, 'max': 32, 'distribution': {1: 22, 2: 12, 3: 5, 4: 6, 5: 5, 6: 1, 7: 3, 8: 2, 9: 2, 10: 1, 11: 2, 13: 1, 18: 1, 31: 1, 32: 1}}.
- Anomaly raw counts: {'DISPUTED_OVERVIEW_CANDIDATE': 53, 'WORD_STUDY_BROAD_PARENT_ANCHOR': 10}.
- Anomaly blocking counts: {'WORD_STUDY_BROAD_PARENT_ANCHOR': 10}.
- Backend disagreements: {'json_sqlite_result_id_disagreements': 0, 'json_sqlite_evidence_id_disagreements': 0, 'json_sqlite_hash_disagreements': 0, 'semantic_leakage': 0, 'presentation_role_blockers': 0, 'textual_routing_anomalies': 0}.
- Audit signals (raw / blocking): {'word_study': {'raw': 10, 'blocking': 10}, 'cross_book_reuse': {'raw': 0, 'blocking': 0}, 'broad_anchor': {'raw': 10, 'blocking': 10}, 'textual_routing': {'raw': 0, 'blocking': 0}, 'archaeology': {'raw': 0, 'blocking': 0}, 'later_reception': {'raw': 0, 'blocking': 0}, 'presentation_role': {'raw': 0, 'blocking': 0}, 'template_evidence': {'raw': 0, 'blocking': 0}, 'evidence_count_outliers': {'raw': 5, 'blocking': 0}, 'json_sqlite_disagreement': {'raw': 0, 'blocking': 0}, 'backend_hash_disagreement': {'raw': 0, 'blocking': 0}, 'semantic_leakage': {'raw': 0, 'blocking': 0}}.
- Artifact fingerprints: canary/supplemental PASS; Batch 001 PASS; Batch 002 PASS; Batch 003 PASS.
- Terra was not run; prose_generated remains false.


## Systemic CKL concern

Template-shaped CKL background, cross-testament reception records, broad word-study parents, and cross-book parent reuse remain systemic review surfaces. This batch quarantines deterministic blockers; it does not repair evidence. Any repeated template or broad-parent pattern should be handled in a separate Luna evidence-cleanup task.

The batch is eligible for a future Terra Medium Batch 006 generation only after the locked manifest is consumed and its hashes are rechecked immediately before generation.
