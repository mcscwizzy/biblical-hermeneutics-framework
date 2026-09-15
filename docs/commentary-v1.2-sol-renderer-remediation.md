# Commentary v1.2 Sol renderer remediation

This records the bounded five-chapter follow-up to qualification
`renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a`. The failed
qualification remains immutable. This remediation does not authorize production
or bulk generation.

## Diagnosis

- **Exodus 14:** Prompt 1.5 consumed 11 of 34 synthesis units and 8 of 19
  meaningful clusters. It covered the core cluster and every available category.
  All 11 skipped weighted clusters were classified as `SUPPORTING` on the basis
  `entity_background_not_direct_passage_context`. Most were generic or irrelevant
  location background (Euphrates, Great Sea, Jordan, Mount Seir, and Salt Sea) or
  redundant representations of the Red Sea, Egyptian setting, and Exodus-to-Sinai
  sequence that the prose already explained. The low weighted score therefore
  primarily exposed packet/scoring relevance noise, not a reader-facing omission.
- **Deuteronomy 10:** Prompt 1.5 consumed 4 of 40 units and 3 of 8 meaningful
  clusters while retaining complete core and category coverage. Every skipped
  cluster was `SUPPORTING` entity background. They contain conglomerated or
  generic material about locations and peoples such as Gibeah, Gilead, Gomorrah,
  Hamath, Jezreel, Kadesh-barnea, Amalek, Arabah, Asia, and Bashan. Those records
  do not materially explain Deuteronomy 10. The renderer correctly preferred
  Aaron/Eleazar/Levi and Deuteronomy's literary movement.
- **Job 1:** Prompt 1.5 consumed 7 of 17 units and 4 of 8 meaningful clusters.
  Two omissions had plausible reader value: Job's association with suffering,
  reverence, and wisdom, and the surrounding reception of Job in James as an
  example of endurance. The remaining skipped clusters were generic theology of
  suffering/cross material. This case showed a genuine prompt completion gap,
  though only for a small subset of the skipped material.
- **Revelation 21:** Prompt 1.5 already used 20 synthesis units across 13 blocks
  and covered creation/new creation, exile/restoration, Jerusalem, temple
  history, apocalyptic imagery, Scripture reuse, resurrection, and direct divine
  presence. Many skipped weighted clusters are semantic parallels under separate
  parent records (creation, resurrection, exile, Jerusalem, temple, and repeated
  theme families). A few could naturally provide complementary support, but
  indiscriminately consuming enough separately scored clusters to reach 0.75
  would duplicate existing explanations.
- **1 Corinthians 14:** The exact failure was `block_8` in `why_it_matters`.
  It cited synthesis `syn_why_it_matters_e5e5571f98fb` while also citing evidence
  `corinthian-outsider-intelligibility:passage-relevance`. The cited synthesis's
  ancestry contained `acts-pentecost-languages-joel`, its passage-relevance
  evidence, `corinthian-interpretation-required`, its passage-relevance evidence,
  and `corinthian-outsider-intelligibility`, but not
  `corinthian-outsider-intelligibility:passage-relevance`. That evidence belongs
  to `syn_interpretive_questions_48738fe0e7f8` and
  `syn_why_it_matters_80afec65926b`. The renderer combined two support families
  but attached only one family's synthesis ID. The validator correctly rejected
  the block; this was a citation-pairing lapse made easier by insufficiently
  salient per-block ancestry instructions, not a validator or schema defect.

There were no operative hard section or block-count limits suppressing coverage:
the four quality failures ranged from 4 to 13 blocks, and the only block-size
limit remained 2,000 characters. Prompt 1.5's repeated selectivity language also
allowed the renderer to stop after core/category coverage. Critically, renderer
inputs expose synthesis units but do not expose the evaluation-only weighted
cluster classification, so the renderer cannot literally prioritize "high-weight
clusters" from the current packet.

## Candidate contract 1.6

The active production contract remains prompt 1.5 and schema 1.2. Candidate
prompt 1.6 adds only two silent final checks:

1. A relevance-based representative-breadth check: include another materially
   distinct supported idea when it changes or deepens understanding, merge it
   naturally, and stop at redundant, generic, weakly related, or bulk-only units.
   IDs may never be attached solely to improve coverage.
2. A per-block set check requiring every evidence ID to occur in the union of
   the cited synthesis units' evidence ancestry. Same-chapter membership is
   explicitly insufficient.

This behavioral change requires a prompt-version bump because it changes the
renderer stopping rule and its final provenance audit. It does not change the
commentary schema, synthesis, validator, Gate v2.1, or any threshold.

## Bounded result

GPT-5.6 Sol at medium effort rendered the five frozen prompt 1.6 packets. All
five outputs structurally validated, the 1 Corinthians ancestry failure was
removed, no hard provenance error appeared, all core coverage remained 1.0, and
no output had HIGH dump severity. The four former quality cases did not improve:
Exodus and Deuteronomy were unchanged in coverage, Job retained the same weighted
coverage while citing fewer duplicate units, and Revelation decreased in both
weighted coverage and raw utilization. Four Gate v2.1 quality failures therefore
remain.

Result: `FIVE_CHAPTER_REMEDIATION_FAILED`.

The next action is not a new 21-chapter qualification. First make one further
bounded decision about the mismatch between evaluation-only weighted clusters
and the renderer-visible synthesis: either correct the relevance/classification
of noisy supporting clusters upstream, or expose a frozen, non-metric selection
signal to the renderer. Any such change needs its own new candidate contract and
the same five-case test before another 21-chapter qualification.
