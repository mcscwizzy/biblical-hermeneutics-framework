# Commentary v1.2 two-chapter omission audit

Status: `FORENSIC_ONLY`  
Diagnostic result under review: `PROMPT_1_7_SELECTION_BREADTH_NOT_READY`  
Scope: `1 Corinthians 14`, `Revelation 21`  
Prompt 1.8: not created

The complete machine-readable audit, including every eligible cluster's full
evidence and synthesis ancestry, is [audit.json](/home/johnwalker/Documents/github/biblical-hermeneutics-framework/.bhf-data/bhf-commentary-candidates/prompt-1.7-omission-audit-5166b2b6065bee070ee7/audit.json).

## Answer first

The two unchanged metrics do not have the same cause.

For `1 Corinthians 14`, prompt 1.7 selected the same five of seven relevant
clusters as prompt 1.6. The two scorer misses are not a clean pair of absent
reader ideas: one is a broad aggregate whose component ideas are already
expressed through other cited clusters, and the other is a partially implied
Acts/Pentecost comparison. The remaining `.8333` category result is the
scorer's missing `history` family, not a material prose failure. The primary
cause is therefore `POSSIBLE_SCORING_MISMATCH`, with no case for a
chapter-specific renderer change.

For `Revelation 21`, prompt 1.7 did change the selected set, but it exchanged
two prompt-1.6 `.7` clusters for two different prompt-1.7 `.7` clusters:

| Prompt 1.6 only | Prompt 1.7 only | Weight exchanged |
| --- | --- | ---: |
| Jerusalem cultural significance (`idea_cluster_0eab3d8c1fbd`) | New Jerusalem as final hope (`idea_cluster_20992f8315ab`) | `.7` |
| Creation chronology (`idea_cluster_a3997c8def39`) | Ancient temple cultural setting (`idea_cluster_b4f1b03ed9c8`) | `.7` |

The six other selected clusters stayed the same. Thus the numerator remained
`4.8`, the denominator remained `10.4`, and every reported metric remained
unchanged. The output also expresses six of the eight prompt-1.7 scorer misses
through semantically equivalent parallel prose. The two less-equivalent misses
are Jerusalem's distinct cultural density and the creation chronology.

The smallest supported explanation is a dense-input presentation bottleneck:
the renderer receives 119 flat synthesis units, 24 optional clusters, and many
parallel Jerusalem/temple/creation records, but it does not receive the
scorer's eligibility or cluster boundaries. Prompt 1.7 adds instructions about
distinct ideas, but does not surface those distinctions in the input.

## Frozen inputs and method

- Starting SHA: `96c23a1d265548b8742abb6c1272853dc867ef36`
- Branch: `feat/commentary-v1.2-enrichment`
- Prompt-1.7 diagnostic namespace:
  `renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1`
- Prompt-1.7 manifest identity:
  `e4eef49a199c281fe6cf2cbe08f11e96a770ea9ad54da61fb195d3964916ab5c`
- Prompt version: `1.7`
- Renderer: `gpt-5.6-sol`, effort `medium`
- System prompt SHA-256:
  `cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614`
- Prompt-1.6 qualification:
  `renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31`

The evidence hashes and synthesis hashes recomputed from the current
authorities match the frozen prompt-1.7 packets exactly:

| Chapter | Evidence hash | Synthesis hash | Prompt-1.7 user-prompt SHA-256 |
| --- | --- | --- | --- |
| 1 Corinthians 14 | `0f687d600e3fc75cebc24b21f963314a508be0c880a7dfae862e317ad5adc3e9` | `45c08801198bd076d8553b274e99c19f86f8d85056d225186a2612cd37757553` | `58bda27b19b5ed0778f2ba648caac1992ecabf00cd71d9305ac04c849c95e6d9` |
| Revelation 21 | `a470ccd9e79bf996b7b7a31161313c149d8de6e571ef0216f62242c2d91489ba` | `750ad9065279a515f8cd7388fbe7c53eea26020881f9224aa828bf73fba09eaf` | `6d6331aef8c7b445f434b07cf407f2e6e181efe2fcc3ff0398f0142c6f2a5dd0` |

The compiled synthesis JSON and permitted-citation JSON are byte-identical
between the historical prompt-1.6 and frozen prompt-1.7 user prompts for both
chapters. Prompt 1.7 changed the instructions and prompt identity, not the
underlying evidence or synthesis payload. The renderer prompt contains neither
eligibility classifications nor the scorer's cluster boundaries.

All prompt-1.7 responses were structurally accepted, had no validation errors,
and had no hard provenance codes. The audit did not call the scorer to produce
new results; it used the frozen evaluation output and only recomputed hashes and
read-only evidence claims.

## Metric and shape summary

| Chapter | Units | Relevant clusters | Rendered relevant clusters | Prompt 1.6 → 1.7 weighted | Prompt 1.6 → 1.7 eligible utilization | Prompt 1.7 categories | Prompt 1.7 shape |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 Corinthians 14 | 33 | 7 | 5 | `.7143 → .7143` | `.7143 → .7143` | `.8333` | 4 sections / 8 blocks / 536 words |
| Revelation 21 | 119 | 16 | 8 | `.4615 → .4615` | `.5000 → .5000` | `1.0000` | 5 sections / 9 blocks / 622 words |

Both chapters report `core_coverage = 1.0000`, but both have
`core_cluster_count = 0`. The core result is therefore vacuous for this audit;
the prompt-1.7 selection test is being exercised entirely by supporting,
reader-relevant clusters.

## 1 Corinthians 14

### Complete eligible-idea audit

Every row is `RELEVANT`, weight `.5`, and `NON_CORE`. “Rendered” means the
frozen scorer consumed at least one synthesis ID from that cluster. The full
evidence and synthesis ID arrays are preserved in `audit.json`.

| Concept | Weight | Category | Core? | Synth prompt position | Rendered? | Closest prose | Boundary / likely cause |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Linked questions about tongues, prophecy, communal discernment, and disputed women-or-wives silence | .5 | culture, geography, history, interpretive questions | No | 3, 5, 11, 22, 28, 32 / early→late | No, but partial equivalent | Blocks 2–8 express its component ideas under other IDs | `SEMANTICALLY_EQUIVALENT`; `POSSIBLE_SCORING_MISMATCH` |
| Textual placement and contextual scope of the women-or-wives silence commands | .5 | culture, geography, interpretive questions | No | 6, 12, 23, 30 / early→late | Yes — `interpretive_questions: Participation, Discernment, and Silence / block_6` | Textual variation, three silence contexts, and women’s prayer/prophecy are directly explained | Distinct and rendered |
| Chapter 13 as literary setting: love governs gifts, correction, and leadership | .5 | culture, surrounding passages | No | 17, 18 / middle | Yes — `surrounding_passages: The Love Chapter in Its Literary Setting / block_1` | Chapter 13’s location and noncoercive function are directly explained | Distinct and rendered |
| Acts/Pentecost presents recognizable languages, but its relation to Corinthian tongues remains debated | .5 | history, surrounding passages | No | 21 / middle | No, but partial equivalent | Block 2 says Acts 2 must not define Corinthian tongues; it omits the positive language comparison | `PARTIALLY_OVERLAPPING`; `POSSIBLE_SCORING_MISMATCH` with prompt-salience weakness |
| Tongues, prophecy, intelligibility, participation, order, accessibility, and safeguarding form the chapter’s central pattern | .5 | culture, interpretive questions | No | 1, 2, 4, 8, 10, 13, 24–27, 29, 33 / early→late | Yes — blocks 2–5 and 7–8 | The response directly covers uncertain tongues, prophecy, order, participation, medical caution, and safeguarding | Distinct and rendered |
| Order serves edification, intelligibility, learning, encouragement, self-control, peace, and communal weighing | .5 | culture, interpretive questions | No | 7, 9, 31 / early→late | Yes — `interpretive_questions: Participation, Discernment, and Silence / block_5` | Block 5 states the purpose of order and continued evaluation of revelation | Distinct and rendered |
| Chapter 13’s gifts-setting plus manuscript transmission and partition caution | .5 | archaeology, culture, surrounding passages | No | 14–16, 19–20 / middle | Yes — `surrounding_passages: The Love Chapter in Its Literary Setting / block_1` | Block 1 covers chapter 13’s gifts-setting; the cited synthesis also carries manuscript context | Distinct and rendered |

### Trace of the missed clusters

`idea_cluster_018650e9fc74` is clearly represented in evidence (nine anchored
records, including the tongues, prophecy, women-variant, and silence records)
and in six synthesis units at positions 3, 5, 11, 22, 28, and 32. It is
explicitly present in the compiled synthesis and in the prompt’s permitted
citations. It is not a single narrow reader idea: it aggregates several ideas
that the response separately explains in blocks 2–8. The scorer sees no cited
ID from this aggregate cluster, while a reader sees the substance through
`idea_cluster_5b79903d041c`, `idea_cluster_118df255769d`, and
`idea_cluster_621a6a3ced67`. This is a plausible
`SCORER_DISTINCT_BUT_PROSE_EQUIVALENT` case, not a genuine renderer omission.

`idea_cluster_5aa8529568c8` is also clearly available: its evidence is
`acts-pentecost-languages` and its synthesis is
`syn_surrounding_passages_efe154a6d3b0` at synthesis position 21. It is a
single explicit surrounding-passage unit, in the middle of the synthesis
payload, not hidden in nested data. The renderer’s sentence “Acts 2 ... should
not be allowed to define the Corinthian phenomenon in advance” preserves the
comparison’s caution, but not the positive observation that Acts depicts
recognizable diaspora languages. This is partial prose equivalence plus a
low-salience surrounding-context choice, not a missing core explanation.

### Why category coverage is `.8333`

The six available category families are `archaeology`, `culture`, `geography`,
`history`, `interpretive_questions`, and `surrounding_passages`. The five
consumed families are all except `history`. The absent family is supplied by
the two missed clusters above: the broad aggregate includes the history-tagged
`1cor-prophecy` and `1cor-tongues` records, while the Acts comparison is the
clean history/surrounding-passage cluster.

The Acts comparison is useful to a normal reader because it prevents using
Acts 2 as a shortcut for classifying Corinthian tongues. The response already
states that caution, so including the full positive comparison would improve
precision but would not materially change the explanation. The broad aggregate
does not identify a further reader-facing gap beyond prose already present.

### Ancestry and capacity findings

`SYNTHESIS_ANCESTRY_MISMATCH` remains fully resolved. Prompt 1.7 has no
validation errors or rejection codes, and its evidence and synthesis hashes
match the frozen packet. Every output evidence ID is within the ancestry of its
cited synthesis IDs.

The response has 4 sections, 8 blocks, and 536 words. Its largest block is 640
characters, below the 2,000-character schema limit. There is no truncation,
fixed section quota, or evidence of a token ceiling. The output is a complete,
compact prose arc; the issue is which parallel cluster IDs it cites, not an
exhausted schema.

### Chapter diagnosis

Primary cause: `POSSIBLE_SCORING_MISMATCH`.

Secondary contributor: `PROMPT_SALIENCE_WEAKNESS` for the single surrounding
Acts comparison.

Prompt 1.7 did not add a relevant scorer cluster: the selected set remained
five of seven. The category shortfall is not a useful reason to alter this
chapter’s renderer behavior, and no further remediation is needed for this
chapter alone.

## Revelation 21

### Complete eligible-idea audit

There are 16 `RELEVANT` clusters: 12 at weight `.7` and 4 at weight `.5`.
All are `NON_CORE` under the frozen core classifier. Eight are scorer-rendered
and eight are not. The “boundary” column records whether the cluster boundary
looks distinct from a reader-facing prose perspective; it does not change the
frozen clustering.

| Concept | Weight | Category | Core? | Synth prompt position | Rendered? | Closest prose | Boundary / likely cause |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Jerusalem’s royal, cultic, pilgrimage, imperial-pressure, repentance, judgment, and restored-worship significance | .7 | culture | No | 32, 37, 118 / early→late | No, partial | Historical Context block 2 and Cultural Context block 5 cover neighboring history/temple ideas | `PARTIALLY_OVERLAPPING`; `PROMPT_SALIENCE_WEAKNESS` |
| New Jerusalem as the final hope reshaping Zion after judgment and exile | .7 | history | No | 78 / middle | Yes — Historical Context block 2 | Block 2 states this directly | Distinct and rendered |
| Temple sequence from tabernacle through Solomon, destruction, restoration, Jesus, and New Jerusalem | .7 | chronology | No | 5, 6, 108 / early→late | Yes — Chronology block 6 | Block 6 gives the sequence and its New Jerusalem completion | Distinct and rendered |
| Revelation’s recomposition of Ezekielian throne, measuring, battle, city, river, and tree imagery | .5 | geography, surrounding passages | No | 99 / late | Yes — Surrounding Passages block 9 | Block 9 gives the Ezekielian literary pattern | Distinct and rendered |
| Ancient temples as royal-cultic centers contrasted with Israel’s covenant holiness and atonement | .7 | culture | No | 17, 41, 47 / early→middle | No, semantic equivalent | Cultural Context block 5 states the same ancient-temple/Israel contrast | `SEMANTICALLY_EQUIVALENT`; `LIKELY_SEMANTIC_REDUNDANCY` |
| Jerusalem’s movement from Jebusite city to Davidic capital, temple center, exile/return focus, and messianic expectation | .7 | history | No | 81, 87 / late | Yes — Historical Context block 2 | Block 2 traces this trajectory | Distinct and rendered |
| New creation, divine dwelling, nations, and kings form a cosmic and communal hope | .5 | history, interpretive questions | No | 96, 101 / late | Yes — Why It Matters block 7 | Block 7 holds these images together | Distinct and rendered |
| New Jerusalem combines city, bride, sanctuary, Eden, and renewed-Zion imagery | .5 | culture, surrounding passages | No | 98, 100 / late | Yes — Surrounding Passages block 9 | Block 9 directly states the overlapping imagery and scriptural reuse | Distinct and rendered |
| Sanctuary referents remain distinct; later readings cannot justify antisemitism, replacement, seizure, or institutional immunity | .5 | culture, interpretive questions | No | 97, 102 / late | Yes — Why It Matters block 8 | Block 8 directly states the distinction and ethical boundary | Distinct and rendered |
| Creation sequence from good creation and human vocation through fall, worship, Christ, and promised new creation | .7 | chronology | No | 4, 9, 115 / early→late | No, partial — Cultural Context block 3 and Why It Matters block 7 | Those blocks cover creation and renewal broadly, not the chronological arc | `PARTIALLY_OVERLAPPING`; `SYNTHESIS_PRESENTATION_WEAKNESS` |
| Ancient temple dwelling/royal-cultic setting, Israel’s holiness, sacrifice, priesthood, pilgrimage, and authority disputes | .7 | culture | No | 16, 105 / early→late | Yes — Cultural Context block 5 | Block 5 directly explains this cluster | Distinct and rendered |
| Temple imagery from tabernacle through Solomon, exile/return, and New Testament sacred-space rereading | .7 | history | No | 74 / middle | No, semantic equivalent | Chronology block 6 gives the same historical development under another cluster | `SEMANTICALLY_EQUIVALENT`; `LIKELY_SEMANTIC_REDUNDANCY` |
| Ancient Near Eastern temple presence/royal order contrasted with Israel’s holiness, covenant, atonement, mediation, pilgrimage, and Second Temple life | .7 | culture | No | 14, 109 / early→late | No, semantic equivalent | Cultural Context block 5 covers this cultural family through a parallel cluster | `SEMANTICALLY_EQUIVALENT`; `LIKELY_SEMANTIC_REDUNDANCY` |
| New Jerusalem transforms familiar ancient city/temple imagery around God’s direct presence | .7 | culture | No | 30 / early | No, semantic equivalent across blocks 6 and 9 | Block 6 explains direct presence replacing a separate temple; block 9 explains the wider city/sanctuary imagery | `PARTIALLY_OVERLAPPING`; `POSSIBLE_SCORING_MISMATCH` |
| Temple development from tabernacle through Solomon, exilic memory, and Second Temple rebuilding | .7 | history | No | 70, 71, 94 / middle→late | No, semantic equivalent — Chronology block 6 | Block 6 gives the same sequence and adds its New Jerusalem completion | `SEMANTICALLY_EQUIVALENT`; `LIKELY_SEMANTIC_REDUNDANCY` |
| Temple symbolism across tabernacle, monarchy, Second Temple Judaism, Jesus, and Christ/community New Testament imagery | .7 | history | No | 69, 116 / middle→late | No, semantic equivalent across blocks 6 and 8 | Blocks 6 and 8 together carry the historical and Christ/community sanctuary material | `SEMANTICALLY_EQUIVALENT`; `LIKELY_SEMANTIC_REDUNDANCY` |

### Trace of every missed eligible idea

The following traces use the exact evidence and synthesis IDs preserved in the
machine artifact.

1. **`idea_cluster_0eab3d8c1fbd` — Jerusalem cultural significance.** Evidence
   IDs are `jerusalem:ancient_near_east_context:0`,
   `jerusalem:hebraic_worldview:0`, `jerusalem:second_temple_context:0`, and
   `what-is-the-significance-of-jerusalem:ancient_near_east_context:0`.
   Synthesis IDs are `syn_cultural_context_6fe92900e971`,
   `syn_cultural_context_7d12d817b879`, and
   `syn_why_it_matters_ecb971b680bb`. Evidence claims and synthesis facts are
   explicit. They occur at synthesis positions 32, 37, and 118, with the
   significance copy last. The renderer prompt contains them, but the input
   also contains Jerusalem history and several temple alternatives. The prose
   covers adjacent historical and temple facts, not Jerusalem’s distinct
   cultural density. Classification: `PROMPT_SALIENCE_WEAKNESS`.

2. **`idea_cluster_440d7c941173` — ancient temple cultural contrast.** Evidence
   IDs are `temple:ancient_near_east_context:0`,
   `what-is-the-significance-of-the-temple:ancient_near_east_context:0`, and
   `what-is-the-temple:ancient_near_east_context:0`; synthesis IDs are
   `syn_cultural_context_1255f86bbec6`,
   `syn_cultural_context_956d4d9fb47d`, and
   `syn_cultural_context_c035d1f2c3dc`. The facts are explicit at positions
   17, 41, and 47. Cultural Context block 5 says the same thing using the
   rendered `idea_cluster_b4f1b03ed9c8` ancestry. Classification:
   `LIKELY_SEMANTIC_REDUNDANCY`; `SCORER_DISTINCT_BUT_PROSE_EQUIVALENT` is
   plausible.

3. **`idea_cluster_a3997c8def39` — creation chronology.** Evidence IDs are
   `creation-doctrine-framework:timeline:0` through `:5`; synthesis IDs are
   `syn_chronology_2edf54bee5a7`, `syn_chronology_ea92011ac148`, and
   `syn_why_it_matters_c59af65cbb27`. The evidence and facts are explicit, but
   the idea is split between positions 4, 9, and 115. Cultural Context block 3
   gives creation background and Why It Matters block 7 gives cosmic renewal,
   but the prose never states the complete creation-to-new-creation sequence.
   Classification: `SYNTHESIS_PRESENTATION_WEAKNESS`.

4. **`idea_cluster_b9f92a2e8940` — temple historical development.** Evidence
   ID is `temple-theme:historical_context:0`; synthesis ID is
   `syn_historical_context_a01b7b4b83e2` at position 74. The single unit is
   explicit and in the middle of the prompt. Chronology block 6 expresses the
   same sequence through `idea_cluster_243e0cbb763d`. Classification:
   `LIKELY_SEMANTIC_REDUNDANCY`; scorer-distinct but prose-equivalent is
   plausible.

5. **`idea_cluster_c4b6236fce0e` — temple cultural meaning.** Evidence IDs
   are `temple-theme:ancient_near_east_context:0`,
   `temple-theme:hebraic_worldview:0`, and
   `temple-theme:second_temple_context:0`; synthesis IDs are
   `syn_cultural_context_0be32dd62dc5` and
   `syn_why_it_matters_7ed31ca5269e`. They occur at positions 14 and 109.
   Cultural Context block 5 expresses the same ancient-temple, Israelite
   holiness, and Second Temple content using `idea_cluster_b4f1b03ed9c8`.
   Classification: `LIKELY_SEMANTIC_REDUNDANCY`.

6. **`idea_cluster_e29624b106d8` — transformation of familiar city/temple
   imagery.** Evidence ID is `new-jerusalem:ancient_near_east_context:0`;
   synthesis ID is `syn_cultural_context_6d6a364126a4` at position 30. The
   concept is explicit and early-middle, but its reader-facing meaning is
   distributed across Chronology block 6’s direct-presence claim and
   Surrounding Passages block 9’s city/sanctuary imagery. Classification:
   `POSSIBLE_SCORING_MISMATCH`; it is not proof of a scorer defect.

7. **`idea_cluster_e56f67d45e11` — temple historical sequence.** Evidence IDs
   are `temple:historical_context:0`,
   `what-is-the-significance-of-the-temple:historical_context:0`, and
   `what-is-the-temple:historical_context:0`; synthesis IDs are
   `syn_historical_context_6d3af537e6c4`,
   `syn_historical_context_87b6fb42d65c`, and
   `syn_historical_context_fc40b5ad8845` at positions 70, 71, and 94. Block 6
   gives the same sequence under `idea_cluster_243e0cbb763d`. Classification:
   `LIKELY_SEMANTIC_REDUNDANCY`.

8. **`idea_cluster_ebe19d7ddf91` — temple symbolism across Jewish and New
   Testament settings.** Evidence IDs are `temple-symbol:historical_context:0`
   and `temple-symbol:historical_setting:0`; synthesis IDs are
   `syn_historical_context_64e9e004fadb` and
   `syn_why_it_matters_d6c5f36b7588` at positions 69 and 116. Blocks 6 and 8
   together express the tabernacle-to-Jesus sequence and the Christ/community
   sanctuary distinctions using other ancestry. Classification:
   `LIKELY_SEMANTIC_REDUNDANCY`.

### Redundancy pattern

The misses are not systematically late: missed synthesis positions include
14, 17, 30, 32, 69–74, and 116–118. The evidence-citation list is sorted by
ID, so its ordinal position is provenance ordering rather than a reliable
attention ordering; synthesis-unit position is the meaningful prompt-salience
measure.

Seven of the eight misses concern Jerusalem/temple framing. Six are exact or
near-parallel records whose reader-facing content appears in rendered blocks:

- `440d7c941173` → block 5 / rendered temple culture;
- `b9f92a2e8940`, `e56f67d45e11`, `ebe19d7ddf91` → block 6, with block 8 adding
  the Christ/community distinction;
- `c4b6236fce0e` → block 5;
- `e29624b106d8` → blocks 6 and 9.

The current scoring boundary is therefore not a clean reader-facing boundary
for those six cases. The scorer is still correctly reporting that the output
did not cite those clusters' IDs; the audit only flags a plausible semantic
equivalence. The two remaining cases, Jerusalem cultural significance and the
creation chronology, are genuinely distinct enough that their partial absence
matters.

### Prompt salience and response capacity

Revelation 21’s 119 synthesis units include 16 relevant clusters and 24
contextual-optional clusters. Relevant concepts are represented by one to
three synthesis units, often with a duplicate `why_it_matters` copy. The
renderer sees the facts and provenance, but not the labels `RELEVANT`,
`CONTEXTUAL_OPTIONAL`, cluster weights, or duplicate relationships. Prompt 1.7
asks it to identify distinct ideas silently, but gives it no explicit
reader-level selection view to distinguish a true new idea from a parallel
record.

The response contains 5 sections, 9 blocks, and 622 words. The largest block is
665 characters, below the 2,000-character limit. It is full prose, not
truncated, and no dump signal fired. Compared with prompt 1.6, it is actually
shorter and less section-diverse (`703 → 622` words and `8 → 5` sections), but
there is no hard output quota or token-limit evidence. The observed behavior is
a soft narrative stopping point: after a coherent apocalyptic, exile, temple,
presence, and scriptural-reuse arc, the renderer stops rather than extending
the response for every relevant cluster. That behavior is enabled by the flat,
duplicate-heavy input and the no-checklist/no-fixed-length contract; it is not a
schema failure.

### Why Revelation 20 improved

Revelation 20 has only 21 synthesis units and six relevant clusters. Its
prompt-1.7 response is 329 words in six blocks and improved from `.6667` to
`.8056` weighted coverage and from `.6667` to `.8333` eligible utilization.
Its six relevant clusters are comparatively direct: resurrection hope,
judgment, Gog/Ezekiel reuse, and broader scriptural reuse. There are fewer
semantic competitors, no 119-unit flat backlog, and no large group of parallel
temple/Jerusalem records. Prompt 1.7 therefore had a tractable selection
problem and added one relevant cluster plus a category.

Revelation 21 has 16 relevant clusters, 24 optional clusters, 119 units, and
multiple parallel families. Prompt 1.7 changed which `.7` ideas were selected,
but not how many weighted ideas were selected. This is why the same instruction
helped Revelation 20 while producing no metric movement in Revelation 21.

### Chapter diagnosis

Primary cause: `SYNTHESIS_PRESENTATION_WEAKNESS`.

Secondary contributors:

- `LIKELY_SEMANTIC_REDUNDANCY` across six of the eight scorer misses;
- `POSSIBLE_SCORING_MISMATCH` where alternate evidence ancestry supports
  prose-equivalent ideas;
- soft narrative stopping behavior without evidence of a hard capacity limit.

The shortfall is meaningful for two concepts—the distinct cultural meaning of
Jerusalem and the creation chronology—but the majority of the apparent misses
are not missing natural prose. Category coverage is `1.0000`, so category
presence cannot detect this selection loss.

## Final classification

### 1 Corinthians 14

Primary cause: `POSSIBLE_SCORING_MISMATCH`.

Secondary contributors: `PROMPT_SALIENCE_WEAKNESS` for the Acts/Pentecost
comparison. No additional scorer cluster was selected, and the metric shortfall
does not represent a material reader-facing omission.

### Revelation 21

Primary cause: `SYNTHESIS_PRESENTATION_WEAKNESS`.

Secondary contributors: parallel semantic redundancy, plausible scorer/prose
boundary disagreement, and soft narrative stopping in a dense input. Two
eligible ideas remain only partially expressed; six scorer misses are plausibly
already expressed through alternate rendered clusters.

## One next bounded action

**B. Prompt/input-presentation remediation.**

Run one isolated diagnostic that presents a dense chapter’s distinct eligible
reader-level ideas and their synthesis ancestry as an explicit deterministic
selection view, scoped to a Revelation 21-style dense input. Leave CKL, evidence
routing, synthesis content, scoring, and all prompt-1.7 artifacts unchanged.

This is smaller and better supported than a prompt-only change because the
renderer cannot reliably preserve distinctions that are not surfaced in its
input. It is also premature to make a scoring-semantic change: the
scorer-equivalence flags are plausible, but the Jerusalem and creation misses
show that the input presentation has a real omission problem.

