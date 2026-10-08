# Genesis G0 Evidence Census

## Purpose and transaction boundary

Transaction `GENESIS_G0_EVIDENCE_CENSUS` establishes a reproducible, chapter-by-chapter baseline of what the current CKL and Commentary v1.2 pipeline can retrieve for Genesis 1–50. It classifies coverage and recommends a bounded future expansion plan. It does not add or repair production evidence, compile new Commentary, change Commentary v1.2, or promote a release.

The final state is `GENESIS_G0_EVIDENCE_CENSUS_COMPLETE`. Work stops after the census is reviewed. Later evidence expansion, evidence source-locking, selective synthesis, chapter regeneration, human review, and promotion require separate transactions.

## Audit methodology

1. Record the exact clean master commit and feature-branch merge base.
2. Record the current Commentary v1.2 release manifest identity, release checksum index identity and byte hash, plus CKL object count, inventory fingerprint, and byte signature when available.
3. For each Genesis chapter, call the current `framework.commentary.production.inputs.prepare_chapter` path. This invokes current CKL retrieval, EvidenceBundle construction, passage applicability, synthesis compilation, and synthesis validation without calling a prose model.
4. Load the published Commentary v1.2 artifact and release publication row for the same chapter. Count sections and blocks and record the evidence IDs cited by those blocks.
5. Enumerate CKL candidates through the production scripture-reference index and reuse the anchor-field semantics of `tools/diagnose_scripture_retrieval.py`. Parse candidate anchors once, use production scripture retrieval for each chapter, and compare chapter-overlapping candidates with evidence materialized into the prepared bundle. This reports candidate-level exclusions separately from bundle items unused by synthesis. If the API does not expose a rejection reason, record that limitation instead of inferring one.
6. Inventory all CKL objects whose own references, Genesis book-object relationships, or retrieved parent identity connect them to Genesis. Preserve their source, dispute, confidence, and type metadata for human review.
7. Audit three non-Genesis controls through the same chapter preparation path: Isaiah 36 (recent geography impact), Acts 16 and Revelation 18 (unrelated controls documented unchanged in the recent selective geography transaction).
8. Recompute the frozen release and CKL signatures after the read-only audit and require exact equality.

All generated files are deterministic JSON or Markdown without generation timestamps. Input hashes and tool versions are included so a later run can be compared exactly.

## Chapter classification

Each chapter receives one overall classification based on passage-applicable, source-backed evidence that reaches production preparation, synthesis coverage, and dimension breadth:

- `GOOD`: multiple useful passage-specific dimensions reach synthesis; no padding is needed.
- `THIN`: useful evidence reaches synthesis, but at least one important applicable dimension remains materially unsupported.
- `SPARSE`: one or two useful dimensions, or evidence dominated by broad book-level context or later reception.
- `GAP`: no meaningful passage-specific evidence is usable by synthesis.

The deterministic baseline treats an item as meaningfully passage-specific when its accepted chapter/verse anchor overlaps the current chapter and its semantic relationship is not `LATER_RECEPTION` or `GENERIC_BACKGROUND`. `BOOK_CONTEXT` items remain eligible when they carry a chapter-specific anchor. A chapter is `GAP` when no such item reaches synthesis; `SPARSE` when at most two such items reach synthesis or no more than two applicable dimensions have at least two synthesized items; `GOOD` when at least six such items reach synthesis and at least five applicable dimensions have two or more items; otherwise it is `THIN`. These thresholds make the machine classification repeatable; the human report retains dimension-level evidence so reviewers can correct an applicability judgment.

Counts are supporting measures, not substitutes for this classification. Evidence dimensions may be `NOT_APPLICABLE`; a relevant but absent dimension is a gap. Immediate literary context, ANE context, culture/social context, geography, archaeology/material culture, narrated/compositional/reception history, Hebrew concepts, divine-council/spiritual worldview, covenant, intertextuality, textual criticism, lexical concepts, and interpretive disputes are assessed only where passage context warrants them.

## Evidence and provenance fields

For every bundled item, retain ID, parent object and type, chapter anchor, category, source IDs and source class, confidence, dispute status, semantic relationship, passage applicability scope, anchor source/specificity, and compiler use. A bundled item is “usable by synthesis” only if an emitted synthesis unit cites its ID. A published Commentary item is separately “consumed” only if a v1.2 block cites it. Missing candidate-level exclusion reasons are reported as uninstrumented rather than inferred.

Source support is classified as primary (Scripture, ancient primary source, excavation/museum record), secondary (academic book, journal article, scholarly reference), internal orientation, or unresolved. Source class does not itself prove a claim. Later canonical reception is not counted as immediate Genesis context. Shared ancient motifs do not establish direct literary dependence. Disputed claims preserve their recorded confidence and dispute state.

## Coverage and remediation taxonomy

The census provides numeric retrieval and synthesis counts, source counts, evidence-category counts, confidence and dispute distributions, Commentary section/block counts, and evidence IDs. Every recommendation uses one of: `NEW_CKL_EVIDENCE_REQUIRED`, `EXISTING_OBJECT_ENRICHMENT_REQUIRED`, `PASSAGE_APPLICABILITY_REQUIRED`, `SOURCE_PROVENANCE_REPAIR_REQUIRED`, `GEOGRAPHY_LINK_REQUIRED`, `RELATIONSHIP_LINK_REQUIRED`, `SYNTHESIS_APPLICABILITY_ISSUE`, `COMMENTARY_ONLY_ISSUE`, or `NO_ACTION_REQUIRED`.

Do not create a new object when a durable existing object can be enriched or linked. Future claims should use Scripture for direct observations, primary ancient texts/artifacts for comparison, archaeological publications or museum/excavation records for material claims, established academic reference works, then bounded scholarly syntheses. Do not copy copyrighted commentary prose or bulk-copy Tyndale notes.

## Controls and immutable production guardrails

Controls use the same preparation and validation path, while Genesis remains the only census population. Current input identities are compared with the published release lineage. Whole CKL and Commentary identities are captured before and after to prove that the audit itself changes nothing. G0 may write only audit tooling, tests, documentation, and deterministic files under `.bhf-data/bhf-commentary-candidates/genesis-g0-evidence-census/`. Production CKL, CKL source locks, synthesis, published Commentary, Commentary v1.2 release metadata/checksums, and release identity must remain byte-for-byte unchanged.

## Future expansion batches

The planning artifact groups chapters by coherent evidence domain: Primeval Origins (1–5), Flood/Post-Flood (6–9), Nations/Babel (10–11), Abraham Cycle (12–25), Jacob/Esau Cycle (25–36), and Joseph/Judah Cycle (37–50). The census may split or revise these ranges when retrieval and object relationships justify it. This plan authorizes no production evidence changes.
