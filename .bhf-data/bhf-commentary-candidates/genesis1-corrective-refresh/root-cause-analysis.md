# Genesis 1 corrective refresh: root-cause analysis

## Scope and locked inputs

This is a candidate-only diagnostic from clean `origin/master` at `b45147cf1ab9a19f4232f133419643cd8489d4bb`. The v1.2 release and reader inputs were treated as immutable. Current production preparation reproduces the published Genesis 1 lineage exactly: evidence hash `68599786c2a557df692d91a1caad2381bcdaba1dda3c0d9ef1b6b1dd572ee110`, synthesis hash `04bd8f1219a5d2965037512cbeb51a42b45990104e9f649838ea3338c7c8a778`, source-packet ID `commentary-production-v1-packet:e6928eef4b211b2617f9b10b96f64316fed9f7ffc12174eefcbdd3f4f4f462fa`, and packet hash `e6928eef4b211b2617f9b10b96f64316fed9f7ffc12174eefcbdd3f4f4f462fa`. Evidence is `AVAILABLE`: 58 items in chronology (6), culture (31), geography (2), history (18), and social (1).

The renderer input was rebuilt by the master production renderer-context code, not from the historical Genesis 1 experiment. It binds prompt 1.8, schema 1.2, `gpt-5.6-terra`, high effort, mode `codex_session`, and renderer-input SHA-256 `82c082dd7710364ad5128aba5f963544490018b42c2b8a14e8fe7bba4644a593`. The exact prompt files and hashes are preserved under `renderer-input/`; source packet, evidence, synthesis, reader projection, ancestry envelope, provenance binding, presentation map, and provenance paths are preserved under `source/`.

## What the renderer can see

The current compiler uses 15 evidence IDs and compiles 12 units: four `interpretive_questions`, seven `surrounding_passages`, and one `why_it_matters`. Five units are tagged `CURRENT_CHAPTER`, seven `SURROUNDING_PASSAGE`. The reader projection contains six distinct ideas; ancestry validation preserves all 12 units and all 15 evidence IDs. The binding has 12 active provenance paths. No reader projection or binding whitelist removes a compiled unit or idea.

The 15 citable IDs are:

`2-corinthians:interpretive_note:21`, `col-image`, `col-new-humanity`, `enuma-elish-cosmic-ordering-comparison`, `enuma-elish-cosmic-ordering-comparison:passage-relevance`, `genesis-ane-comparative-context`, `genesis-literary-movement`, `genesis-ordered-worldview-observation`, `genesis-ordered-worldview-observation:passage-relevance`, `genesis:interpretive_note:0`, `genesis:interpretive_note:1`, `genesis:interpretive_note:2`, `john-logos`, `mesopotamian-creation-and-flood-comparisons:interpretive_note:0`, and `zephaniah-creation-reversal`.

Material available includes Genesis 1's ordered action pattern (God speaks, separates, names, appoints, blesses, evaluates, and rests); an Enuma Elish comparison of waters, ordering, celestial organization, and divine rule with an explicit limit against inferring direct borrowing; the Genesis movement from universal origins in chapters 1–11 to the ancestral narratives in chapters 12–50; broader ANE literary-setting and composition uncertainty; later reception in John 1, 2 Corinthians 4, Colossians, and Zephaniah; and image/new-humanity language. The latter units are reception evidence tied to Genesis 1 anchors, not statements of the immediate sense of Genesis. Several surrounding units repeat the same Enuma Elish, ordered-creation, or ANE-context cluster. Exact unit facts, IDs, scope tags, ideas, and active paths are in `current-input-diagnosis.json` and the locked source snapshots.

The other 43 bundle IDs are excluded from synthesis and citable provenance. Each has applicability status `background`, `current_chapter_eligible: false`, inherited parent anchoring, and reason `legacy_parent_inheritance_is_background_only`. They are generic inherited creation, image, light, spirit/ruach, and timeline background records, including broad records such as `creation-doctrine-framework:*`, `creation-doctrine:*`, `creation-theme:*`, `creation:*`, `image-of-god-theme:*`, `light-and-darkness-theme:*`, `new-creation-theme:*`, `pneumatology:*`, `spirit-theme:*`, `spiritual-gifts:*`, `water-and-spirit-theme:*`, `what-does-ruach-mean:*`, `what-is-the-holy-spirit:*`, `what-is-the-image-of-god:*`, and `what-is-the-significance-of-the-holy-spirit:*`. The exact 43 IDs and each applicability record are preserved in `current-input-diagnosis.json`; none is restored or cited by this transaction.

## One-block collapse

The published `genesis_001.json` has one section, one block, two unique evidence IDs (`col-image`, `col-new-humanity`), and one synthesis unit (`syn_interpretive_questions_104b452d03db`). After removing the storage serializer's three application-owned envelope fields before schema validation—the same treatment used by current promotion checks—the artifact validates against the current input and retains status `validated`. Its presentation audit reports 55 words, 2 of 58 bundle IDs consumed, 1 of 12 units represented, and `SYNTHESIS_GAP`.

The dominant cause is **renderer selection failure**: the historical render chose one of six reader ideas and one of 12 active paths even though the current renderer contract exposed all six ideas, all 12 paths, and the 15 legal evidence IDs. The reader plan/projection did not collapse the input. Applicability filtering excluded 43 inherited background items by the current policy and did not leave the renderer source-limited. The remaining 15 IDs and six distinct clusters contain enough support for a useful, bounded synthesis, so insufficient current input is not the root cause.

A contributing cause is a **historical acceptance / richness-check weakness**. The published result is schema-valid but was accepted with a single short discussion and no demonstrated current presentation-quality parity check. The broad `audit_chapter` diagnostic also divides eligible citations by all 58 bundle records. Even citing every legally renderer-visible ID would reach only 15/58 = 25.86%, below its 35% coverage threshold; the 43 background-only records cannot lawfully be used to make that diagnostic pass. This is a denominator mismatch, not a reason to weaken applicability or cite background records.

## Representative richness comparison

| Chapter | Sections / blocks | Unique evidence IDs | Synthesis units represented | Evidence categories represented | Current-chapter families / units | Surrounding units |
|---|---:|---:|---:|---|---|---:|
| Genesis 1 published | 1 / 1 | 2 | 1 | culture | interpretive_questions / 1 | 0 |
| Genesis 2 | 6 / 9 | 26 | 9 | culture, geography, history | cultural_context, interpretive_questions, why_it_matters / 7 | 2 |
| Genesis 3 | 4 / 8 | 29 | 8 | culture, geography, history | cultural_context, interpretive_questions / 7 | 1 |
| Genesis 6 | 4 / 8 | 28 | 10 | archaeology, culture, geography, history, social | interpretive_questions / 6 | 4 |
| Genesis 10 | 6 / 8 | 27 | 8 | culture, geography, politics, social | cultural_context, historical_context, interpretive_questions / 7 | 1 |

This is a quality diagnostic, not a block-count target. Genesis 1's packet is smaller and more reception-heavy than these examples, but it has six distinct reader ideas and two core clusters. Its deficiency was not that it had fewer potential blocks; the published renderer output ignored materially distinct supplied context.

## Candidate gate and conclusion

One render was made after the context gate passed. The only successful raw model output is attempt 002; attempt 001 is preserved as a transport initialization failure that exited before model rendering. The candidate uses two sections, five blocks, 11 unique eligible evidence IDs, and seven unique synthesis units covering all six projected clusters. Technical validation, evidence ancestry, provenance binding, and envelope checks pass. The current calibrated enrichment gate is `PASS`: all six meaningful clusters, both core clusters, all five evidence/category families, and all material quality checks pass without an evidence dump.

The separate broad `audit_chapter` still reports `SYNTHESIS_GAP` / `validated_but_contextually_thin`, for the denominator reason above. This warning is preserved in `validation.json`; it is not hidden or relabeled. The candidate review uses the applicability-aware calibrated gate and substantive inspection, not schema validation alone. Safeguards for ANE comparison, image language, later reception, ruach, “Let us make,” chronology/science, and cosmological claims are recorded in `substantive-review.json`.

Root-cause classification: **mixed** — primary renderer selection failure, with a historical acceptance/richness-diagnostic weakness; current synthesis contains duplicated surrounding clusters and has limited immediate-chapter context, but it is sufficient for a bounded useful candidate. No CKL mutation, applicability change, synthesis recompilation change, or reader-plan change is justified by this transaction.
