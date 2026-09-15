# Commentary v1.2 Genesis 1 consolidation root-cause audit

Status: diagnostic only. No renderer was invoked, no accepted commentary was
rewritten, Gate v2 remains `CANDIDATE_ONLY`, and no CKL or v1.1 artifact was
changed by this audit.

## 1. Executive finding

The primary classification is **MIXED**, with **PACKET_STRUCTURE_CAUSE** as the
stronger causal mechanism and **RENDERER_PROMPT_CAUSE** as the immediate
instructional incentive. This is not primarily a synthesis-compiler failure.

Genesis 1 has 49 generated units and 25 deterministic idea clusters. The
accepted output has 49 blocks, consumes every unit exactly once, and puts zero
blocks across two or more synthesis units. Thus:

* `49 units -> 49 blocks` (100% one-unit blocks; mean and median = 1.0).
* 36 units belong to 12 duplicate/parallel clusters, but the renderer was not
  given those cluster memberships.
* 34 of 49 blocks participate in a deterministic redundant or near-duplicate
  prose relation; those blocks contain 1,324 of 1,627 words (81.38%). This is
  a lexical upper-bound signal, not a claim that every shared topical word is
  semantically redundant.
* The compiler preserved provenance correctly: 31 units are single-evidence
  units, 14 are shared-parent units, 4 are shared-entity units, and 9 are
  relationship units. The problem is that the presentation contract exposes
  these as flat peers rather than as reader-level groups.

The smallest next change should therefore be a prompt-only experiment under a
new prompt identity, `1.3`. A deterministic `ReaderSynthesisPlan` is warranted
as a follow-up or fallback because prompt 1.2 has no access to the quality-only
cluster membership, class, or priority information.

## 2. Genesis block-to-synthesis, evidence, and cluster mapping

The final column is `synthesis-unit-count / evidence-record-count`. Evidence
IDs are the exact IDs cited by the accepted block. Word counts use the same
case-insensitive token rule as the diagnostic code and total 1,627.

| block | section kind | verse refs | synthesis IDs | evidence IDs | words | idea cluster | units / evidence |
|---|---|---|---|---|---:|---|---:|
| block_1 | chronology | Genesis 1:1-31 | syn_chronology_4d389e9b8f3a | creation-doctrine-framework:timeline:0<br>creation-doctrine-framework:timeline:1<br>creation-doctrine-framework:timeline:2<br>creation-doctrine-framework:timeline:3<br>creation-doctrine-framework:timeline:4 | 23 | idea_cluster_37efee8bd0be | 1 / 5 |
| block_2 | chronology | Genesis 1:1-31 | syn_chronology_768538e95314 | creation-doctrine-framework:timeline:5 | 3 | idea_cluster_37efee8bd0be | 1 / 1 |
| block_3 | cultural_context | Genesis 1:1-31 | syn_cultural_context_048db383ff38 | creation:ancient_near_east_context:0<br>creation:hebraic_worldview:0 | 68 | idea_cluster_3ab76c466471 | 1 / 2 |
| block_4 | cultural_context | Genesis 1:1-31 | syn_cultural_context_093852396ae8 | creation-doctrine-framework:ancient_near_east_context:0<br>creation-doctrine-framework:hebraic_worldview:0<br>creation-doctrine-framework:original_audience:0<br>creation-doctrine-framework:second_temple_context:0 | 75 | idea_cluster_79b0bdbeecaf | 1 / 4 |
| block_5 | cultural_context | Genesis 1:1-2 | syn_cultural_context_09f7c52b02bd | water-and-spirit-theme:ancient_near_east_context:0 | 42 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_6 | cultural_context | Genesis 1:26-28 | syn_cultural_context_165d53188040 | image-of-god-theme:ancient_near_east_context:0<br>image-of-god-theme:hebraic_worldview:0<br>image-of-god-theme:second_temple_context:0 | 50 | idea_cluster_dd4bd3062e88 | 1 / 3 |
| block_7 | cultural_context | Genesis 1:1-2 | syn_cultural_context_199584b04720 | pneumatology:ancient_near_east_context:0 | 42 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_8 | cultural_context | Genesis 1:26-28 | syn_cultural_context_290610291b84 | what-is-the-image-of-god:ancient_near_east_context:0 | 17 | idea_cluster_b602be3fedeb | 1 / 1 |
| block_9 | cultural_context | Genesis 1:1-2 | syn_cultural_context_5203177a8820 | what-does-ruach-mean:ancient_near_east_context:0 | 21 | idea_cluster_641cf7d62880 | 1 / 1 |
| block_10 | cultural_context | Genesis 1:1-2 | syn_cultural_context_83f4ab2bd2a1 | spiritual-gifts:ancient_near_east_context:0 | 43 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_11 | cultural_context | Genesis 1:2 | syn_cultural_context_897fd84558ba | what-is-the-holy-spirit:ancient_near_east_context:0 | 16 | idea_cluster_6e54c4995ea6 | 1 / 1 |
| block_12 | cultural_context | Genesis 1:1-5 | syn_cultural_context_924475388c75 | light-and-darkness-theme:ancient_near_east_context:0 | 40 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_13 | cultural_context | Genesis 1:1-31 | syn_cultural_context_a7cc835b48eb | creation-theme:ancient_near_east_context:0 | 18 | idea_cluster_00224f98a22d | 1 / 1 |
| block_14 | cultural_context | Genesis 1:2 | syn_cultural_context_be52dafff1c5 | what-is-the-significance-of-the-holy-spirit:ancient_near_east_context:0 | 16 | idea_cluster_6e54c4995ea6 | 1 / 1 |
| block_15 | cultural_context | Genesis 1:1-31 | syn_cultural_context_d3b7718a2e24 | creation-doctrine:ancient_near_east_context:0 | 43 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_16 | cultural_context | Genesis 1:2 | syn_cultural_context_ea6ffeeb54a6 | spirit-theme:ancient_near_east_context:0 | 23 | idea_cluster_1b4648a605bb | 1 / 1 |
| block_17 | cultural_context | Genesis 1:1-31 | syn_cultural_context_f22381a2cd3d | new-creation-theme:ancient_near_east_context:0 | 42 | idea_cluster_be62c2a60783 | 1 / 1 |
| block_18 | historical_context | Genesis 1:26-28 | syn_historical_context_00264bb93148 | image-of-god-theme:historical_context:0 | 24 | idea_cluster_490f52fd9a1a | 1 / 1 |
| block_19 | historical_context | Genesis 1:1-2 | syn_historical_context_0ef554e79ca1 | pneumatology:historical_context:0 | 11 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_20 | historical_context | Genesis 1:1-31 | syn_historical_context_12d76d5bd424 | creation-doctrine:historical_context:0 | 12 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_21 | historical_context | Genesis 1:1-2 | syn_historical_context_4ca3d78007b3 | water-and-spirit-theme:historical_context:0 | 14 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_22 | historical_context | Genesis 1:1-31 | syn_historical_context_674245f7af9c | creation-doctrine-framework:historical_context:0<br>creation-doctrine-framework:historical_setting:0 | 35 | idea_cluster_c2ee8d8e5b02 | 1 / 2 |
| block_23 | historical_context | Genesis 1:1-5 | syn_historical_context_70587f676cdf | light-and-darkness-theme:historical_context:0 | 14 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_24 | historical_context | Genesis 1:2 | syn_historical_context_79e192e5af74 | what-is-the-holy-spirit:historical_context:0 | 19 | idea_cluster_dfe847c59ba0 | 1 / 1 |
| block_25 | historical_context | Genesis 1:26-28 | syn_historical_context_97639385b2e7 | what-is-the-image-of-god:historical_context:0 | 19 | idea_cluster_42d2f7781d9f | 1 / 1 |
| block_26 | historical_context | Genesis 1:1-2 | syn_historical_context_a32a88d8141c | spiritual-gifts:historical_context:0 | 12 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_27 | historical_context | Genesis 1:1-31 | syn_historical_context_c22d3d2c63c1 | creation-theme:historical_context:0 | 21 | idea_cluster_dd017f4556a2 | 1 / 1 |
| block_28 | historical_context | Genesis 1:1-31 | syn_historical_context_d650cb8d7a97 | creation:historical_context:0 | 18 | idea_cluster_07acf6651210 | 1 / 1 |
| block_29 | historical_context | Genesis 1:2 | syn_historical_context_e18bc0272c4d | what-is-the-significance-of-the-holy-spirit:historical_context:0 | 19 | idea_cluster_dfe847c59ba0 | 1 / 1 |
| block_30 | historical_context | Genesis 1:1-31 | syn_historical_context_eb07da4828dc | new-creation-theme:historical_context:0 | 13 | idea_cluster_ec7dc4532c85 | 1 / 1 |
| block_31 | historical_context | Genesis 1:1-2 | syn_historical_context_f0d01e8a963f | what-does-ruach-mean:historical_context:0 | 18 | idea_cluster_06f5118ed9a7 | 1 / 1 |
| block_32 | historical_context | Genesis 1:2 | syn_historical_context_f378866106de | spirit-theme:historical_context:0 | 16 | idea_cluster_21d7fd8ad2c7 | 1 / 1 |
| block_33 | interpretive_questions | Genesis 1:26-27 | syn_interpretive_questions_104b452d03db | col-image<br>col-new-humanity | 30 | idea_cluster_a508d699bcd8 | 1 / 2 |
| block_34 | interpretive_questions | Genesis 1:20-28 | syn_interpretive_questions_4abfca502108 | zephaniah-creation-reversal | 24 | idea_cluster_e0a8e6eb0419 | 1 / 1 |
| block_35 | interpretive_questions | Genesis 1:1-5 | syn_interpretive_questions_4b06eb55d452 | john-logos | 33 | idea_cluster_b9f4988183ec | 1 / 1 |
| block_36 | interpretive_questions | Genesis 1:3 | syn_interpretive_questions_ed658ab06804 | 2-corinthians:interpretive_note:21 | 23 | idea_cluster_8f57468944f2 | 1 / 1 |
| block_37 | surrounding_passages | — | syn_surrounding_passages_02324dc7bcd9 | enuma-elish-cosmic-ordering-comparison<br>enuma-elish-cosmic-ordering-comparison:passage-relevance<br>mesopotamian-creation-and-flood-comparisons:interpretive_note:0 | 56 | idea_cluster_dc19b676e546 | 1 / 3 |
| block_38 | surrounding_passages | — | syn_surrounding_passages_311399d9709e | genesis-literary-movement | 25 | idea_cluster_987a03cd3a49 | 1 / 1 |
| block_39 | surrounding_passages | — | syn_surrounding_passages_3c5ff4c1ad4a | genesis-ane-comparative-context<br>genesis:interpretive_note:0<br>genesis:interpretive_note:1<br>genesis:interpretive_note:2 | 91 | idea_cluster_987a03cd3a49 | 1 / 4 |
| block_40 | surrounding_passages | — | syn_surrounding_passages_68d0c434dd51 | enuma-elish-cosmic-ordering-comparison<br>enuma-elish-cosmic-ordering-comparison:passage-relevance<br>mesopotamian-creation-and-flood-comparisons:interpretive_note:0 | 56 | idea_cluster_dc19b676e546 | 1 / 3 |
| block_41 | surrounding_passages | — | syn_surrounding_passages_89969fb357a1 | genesis-ane-comparative-context<br>genesis:interpretive_note:0<br>genesis:interpretive_note:1<br>genesis:interpretive_note:2 | 91 | idea_cluster_987a03cd3a49 | 1 / 4 |
| block_42 | surrounding_passages | — | syn_surrounding_passages_89e2fa039257 | genesis-ordered-worldview-observation<br>genesis-ordered-worldview-observation:passage-relevance | 35 | idea_cluster_dc19b676e546 | 1 / 2 |
| block_43 | surrounding_passages | — | syn_surrounding_passages_9a6be1bbec10 | genesis-ordered-worldview-observation<br>genesis-ordered-worldview-observation:passage-relevance | 35 | idea_cluster_dc19b676e546 | 1 / 2 |
| block_44 | why_it_matters | Genesis 1:1-31 | syn_why_it_matters_08c846785ce8 | creation-doctrine-framework:timeline:0<br>creation-doctrine-framework:timeline:1<br>creation-doctrine-framework:timeline:2<br>creation-doctrine-framework:timeline:3<br>creation-doctrine-framework:timeline:4 | 23 | idea_cluster_37efee8bd0be | 1 / 5 |
| block_45 | why_it_matters | Genesis 1:1-31 | syn_why_it_matters_1170572dc806 | creation-doctrine-framework:historical_context:0<br>creation-doctrine-framework:historical_setting:0 | 35 | idea_cluster_c2ee8d8e5b02 | 1 / 2 |
| block_46 | why_it_matters | Genesis 1:1-31 | syn_why_it_matters_55c6c474fbf2 | creation-doctrine-framework:ancient_near_east_context:0<br>creation-doctrine-framework:hebraic_worldview:0<br>creation-doctrine-framework:original_audience:0<br>creation-doctrine-framework:second_temple_context:0 | 75 | idea_cluster_79b0bdbeecaf | 1 / 4 |
| block_47 | why_it_matters | Genesis 1:26-27 | syn_why_it_matters_8c410550b6f6 | col-image<br>col-new-humanity | 30 | idea_cluster_a508d699bcd8 | 1 / 2 |
| block_48 | why_it_matters | Genesis 1:26-28 | syn_why_it_matters_b65d737371b0 | image-of-god-theme:ancient_near_east_context:0<br>image-of-god-theme:hebraic_worldview:0<br>image-of-god-theme:second_temple_context:0 | 50 | idea_cluster_dd4bd3062e88 | 1 / 3 |
| block_49 | why_it_matters | Genesis 1:1-31 | syn_why_it_matters_cdd67602b1d1 | creation:ancient_near_east_context:0<br>creation:hebraic_worldview:0 | 68 | idea_cluster_3ab76c466471 | 1 / 2 |

The same table provides the complete block-to-cluster map. The 12 non-singleton
clusters are: `37efee8bd0be` (blocks 1,2,44), `3ab76c466471` (3,49),
`6e54c4995ea6` (11,14), `79b0bdbeecaf` (4,46), `987a03cd3a49` (38,39,41),
`a508d699bcd8` (33,47), `be62c2a60783` (5,7,10,12,15,17),
`c2ee8d8e5b02` (22,45), `dc19b676e546` (37,40,42,43),
`dd4bd3062e88` (6,48), `dfe847c59ba0` (24,29), and `ec7dc4532c85`
(19,20,21,23,26,30). The other 13 clusters are singleton clusters.

## 3. Prose repetition audit

The deterministic audit compares normalized content words, Jaccard overlap,
shorter-block containment, and sorted-term sequence similarity. It classifies
all 1,176 pairs as follows:

| classification | pairs |
|---|---:|
| DISTINCT | 1,131 |
| RELATED | 10 |
| REDUNDANT | 18 |
| NEAR_DUPLICATE | 17 |

Examples:

* `block_1` / `block_44`: NEAR_DUPLICATE, the chronology “creation declared
  good / human vocation / fall / Christ” is repeated in `why_it_matters`.
* `block_3` / `block_49`: NEAR_DUPLICATE, the same ANE comparison and ordered
  creation explanation is repeated in cultural context and `why_it_matters`.
* `block_6` / `block_48`: NEAR_DUPLICATE, image-of-God royal imagery and
  universal human dignity are repeated.
* `block_11` / `block_14`: NEAR_DUPLICATE, the same Spirit-not-impersonal-force
  claim is repeated under two parent records.
* `block_37` / `block_40`: NEAR_DUPLICATE, the same Babylonian/Marduk
  comparison is emitted twice.
* `block_39` / `block_41`: NEAR_DUPLICATE, the same Genesis 1–11 / ANE literary
  environment paragraph is emitted twice.
* `block_42` / `block_43`: NEAR_DUPLICATE, the same speaking/separating/naming/
  blessing/evaluating/resting observation is emitted twice.
* `block_5`, `block_7`, `block_10`, `block_12`, `block_15`, and `block_17` are
  one high-fact-overlap cluster: their prose repeats the same “ancient
  background includes covenant, worship, kingship, wisdom, prophetic critique”
  template for water/Spirit, pneumatology, spiritual gifts, light/darkness,
  creation doctrine, and new creation.

Topic result: creation/order, image of God, ANE comparison, Spirit/ruach,
chronology, later/intertextual material, surrounding passages, and
`why_it_matters` all have either duplicate cluster ancestry or repeated prose.
The 12 duplicate/parallel clusters account for 36 unit assignments and 1,352
words of block prose. The lexical overlap proxy marks 1,324 words as belonging
to blocks that overlap another block. It cannot determine the exact number of
unique reader insights, but it establishes that a large majority of the prose
is not independently additive at block level.

## 4. Consolidation metrics

| metric | Genesis 1 | Ruth 3 | 2 Samuel 6 | John 1 | Isaiah 6 | Revelation 12 | Leviticus 16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SYNTHESIS_UNITS_PER_BLOCK` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.3000 |
| `IDEA_CLUSTERS_PER_BLOCK` | 0.5102 | 0.8333 | 0.5455 | 0.4468 | 0.7647 | 0.8000 | 1.1000 |
| `EVIDENCE_IDS_PER_BLOCK` | 1.7347 | 1.3333 | 1.0000 | 1.9362 | 1.3529 | 1.4000 | 1.8000 |
| `BLOCKS_PER_IDEA_CLUSTER` | 1.9600 | 1.2000 | 1.8333 | 2.2381 | 1.3077 | 1.2500 | 0.9091 |
| `PROSE_WORDS_PER_IDEA_CLUSTER` | 65.0800 | 44.8000 | 45.0000 | 85.2381 | 41.3846 | 31.0000 | 63.6364 |
| `REDUNDANT_BLOCK_RATIO` | 0.6939 | 0.3333 | 0.5455 | 0.7660 | 0.4706 | 0.4000 | 0.0000 |
| block count | 49 | 6 | 11 | 47 | 17 | 5 | 10 |
| regex word count | 1,627 | 224 | 270 | 1,790 | 538 | 124 | 700 |
| meaningful clusters consumed | 25 | 5 | 6 | 21 | 13 | 4 | 11 |
| exactly-one-unit blocks | 49 | 6 | 11 | 47 | 17 | 5 | 6 |
| multi-unit blocks | 0 | 0 | 0 | 0 | 0 | 0 | 4 |

`CORE_TO_OPTIONAL_PROSE_RATIO` is undefined for all seven accepted outputs
because the current classifier assigns no consumed cluster to `OPTIONAL`.
Genesis has 2 `CORE`, 19 `SUPPORTING`, and 4 `DISPUTED` clusters; both current
`CORE` classifications arise from surrounding-passage units under the present
quality-only classifier. This reinforces that quality classes are not suitable
as an unexamined generation ordering signal.

2 Samuel 6 is the useful positive control: it is explanatory at 270 words and
11 blocks, below dense-chapter conditions, even though its current response is
also one unit per block. Leviticus 16 is the structural consolidation control:
four blocks cite multiple synthesis units and it has no detected redundant
prose pairs. Genesis is different in scale and duplication density, not simply
in having a one-unit block somewhere.

## 5. Renderer prompt 1.2 audit

The exact persisted Genesis packet contains prompt version `1.2`, effort
`medium`, synthesis hash
`0c1f5f085d07eef107d641c89277ec23627aad1db83423956a860a383740a5df`, and the
following relevant instructions:

* “Explain rather than merely list or restate facts. **Connect facts only where
  a synthesis unit has already grouped them.**”
* “Every contextual prose block must cite valid synthesis IDs and their evidence
  ancestry.”
* “A `why_it_matters` block must cite an available `why_it_matters` synthesis
  unit.”
* “Include only useful supported sections. Do not force every kind to appear.”
* “Prefer explanation over lists. Do not pad genealogies, lists, or simple
  chapters.”

There is no instruction to combine compatible *different* synthesis units, no
instruction that a block should cite multiple units, and no instruction to
omit a redundant unit when a related unit has already supplied the same reader
idea. The “connect only where a synthesis unit has already grouped them” line
can actively discourage cross-unit consolidation. The prompt does not say to
address every unit, but it also does not counter the natural exhaustive
interpretation of a packet containing 49 named units.

The JSON example shows one block with one synthesis ID and one evidence ID,
although the arrays technically permit multiple IDs. That is a schema/example
incentive, not a hard schema requirement. The prompt therefore contributes an
incentive but does not alone prove why Genesis was serialized.

## 6. Packet structure audit

The exact Genesis packet presents:

* 49 units in one flat `units` array;
* 42 `CURRENT_CHAPTER` units and 7 `SURROUNDING_PASSAGE` units;
* 15 cultural, 15 historical, 7 surrounding, 6 `why_it_matters`, 4
  interpretive, and 2 chronology units;
* only 9 non-empty `related_unit_ids` links;
* no reader-level cluster IDs;
* no `CORE`, `SUPPORTING`, `OPTIONAL`, or `DISPUTED` quality class field;
* no presentation priority, unit-family, or “already covered by” field;
* 58 cited evidence records in a separate flat citation summary, with all 58
  used by the compiler.

The packet does expose `kind`, `passage_scope`, `related_unit_ids`,
`relationship_basis`, and `support_count`, but these are provenance/compiler
metadata rather than an actionable reader plan. A renderer can see that a
unit is surrounding context; it cannot see that six units should normally be
one Spirit/ANE background idea, or that a `why_it_matters` unit is a parallel
representation of an earlier unit.

This is sufficient to classify packet structure as a primary causal factor.
The quality-only clustering layer already proves that a deterministic grouping
exists, but it is intentionally not part of the generation packet.

## 7. Schema incentive audit

The schema requires valid provenance for every cited ID and bounds each block
to 2,000 characters. It does not require one block per unit and does allow
arrays of synthesis and evidence IDs. Therefore the schema is permissive in
principle. The exact one-block/one-ID example, combined with mandatory
per-block ancestry and the absence of a multi-unit example, creates a weak
`SCHEMA_INCENTIVE_CAUSE`; it is secondary to the flat packet and prompt wording.

## 8. Synthesis fragmentation audit

The compiler emits 49 units from 58 evidence items. The unit shape is:

* 31 `single_evidence_item` units;
* 14 `shared_parent_object` units;
* 4 `shared_entities` units;
* 9 relationship units represented through `related_unit_ids`;
* 31 units with support count 1, 8 with count 2, 4 with count 3, 4 with count
  4, and 2 with count 5.

The compiler is materially fragmented for reader presentation because
parallel parent records and derived `why_it_matters`/surrounding units remain
separate provenance units. However, the fragmentation is intentional and
traceability-preserving, and the existing deterministic cluster audit reduces
49 units to 25 idea clusters without mutating the compiler output. The
bounded finding is therefore **presentation-level fragmentation**, not a
justification to rewrite `CompiledChapterSynthesis` in this task.

## 9. Smallest fix and versioning

Do not change the current prompt 1.2 in place. The recommended next experiment
is prompt `1.3` with these two additions:

> Do not create one block per synthesis unit. Combine compatible synthesis
> units and evidence into coherent explanatory blocks. A single block may and
> often should cite multiple synthesis IDs.

> Do not attempt to mention every supplied synthesis unit. Prioritize the
> contextual material that most helps explain the chapter. Omit redundant or
> secondary material when including it would reduce clarity.

This preserves every safety and provenance rule, does not alter
`CompiledChapterSynthesis`, does not add evidence, and does not turn the
quality auditor into the generator. Because it changes generation semantics,
the prompt identity must become `1.3` and the packet identity must be rebuilt
for that prompt. No version bump is required for the current tree because no
generation prompt was changed during this diagnostic.

A `ReaderSynthesisPlan` is warranted if the prompt-only experiment does not
produce multi-unit blocks or selective omission. It should be a deterministic,
non-mutating presentation layer with idea groups, member synthesis IDs,
passage scope, contextual category, priority class, and evidence ancestry. The
renderer would cite the underlying IDs; `CompiledChapterSynthesis` would
remain unchanged.

## 10. Integrity and authorization status

* Starting HEAD: `1c361c4b60a3636afdde58e5ce9e99b783604f3a`.
* The starting worktree was dirty before this audit with candidate-state,
  Genesis 1–10 v1.1 output files, and manual/raw-rerun artifacts. Those files
  were preserved.
* This audit added only the deterministic diagnostic module, its focused tests,
  this report, and the read-only CLI.
* No CKL file was changed; no CKL mutation was performed.
* No v1.1 pipeline state or v1.1 generation logic was changed. The v1.1 state
  remains `CORPUS_COMPLETE`.
* Gate v2 remains candidate-only. Genesis remains the intentional
  over-generation quality-fail control.
* Full-Bible generation remains unauthorized.
* No Luna, Terra, Sol, Claude, OpenRouter, Ollama, or other prose renderer was
  invoked.

## 11. Exact next experiment

After explicit authorization to render, run only a new prompt-1.3 canary for
Genesis 1, 2 Samuel 6, and Leviticus 16 using the same evidence and synthesis
hashes. Keep outputs in a new diagnostic/raw location until validation. Compare
the existing metrics, requiring no arbitrary word target:

1. Genesis should move below one-unit-per-block behavior and increase
   `SYNTHESIS_UNITS_PER_BLOCK` and `IDEA_CLUSTERS_PER_BLOCK` through real
   multi-unit explanatory blocks.
2. Genesis should reduce `REDUNDANT_BLOCK_RATIO` and preserve safety,
   provenance, core coverage, and category coverage.
3. 2 Samuel 6 should remain materially explanatory and concise.
4. Leviticus 16 should retain its existing multi-unit consolidation behavior.

If Genesis still serializes units, implement `ReaderSynthesisPlan` and repeat
the same three-chapter comparison. Do not change thresholds, rewrite accepted
prose, modify CKL, or activate Gate v2 as part of that experiment.
