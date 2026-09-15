# Commentary v1.2 prompt 1.7 selection-breadth diagnostic

Status: `PROMPT_1_7_SELECTION_BREADTH_NOT_READY`

This was a bounded seven-chapter renderer diagnostic only. It did not start the
60–100 chapter scale qualification, change CKL/evidence routing/synthesis, or
modify any scoring contract.

## Identity and baseline

- Branch: `feat/commentary-v1.2-enrichment`
- Starting SHA: `1216896256855f4b7c6d9c9a01b5f8a1dd16099d`
- Prompt-1.6 qualification: `renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31`
- Prompt-1.6 qualification result: `RENDERER_QUALIFICATION_NOT_QUALIFIED`
- Prompt-1.6 baseline: `21/21` structural validity, weighted coverage `.8478`, core coverage `.9474`, eligible idea utilization `.8498`, category coverage `.9325`, `HIGH dumps=0`, `19` Gate passes, `2` quality failures, `14` target passes, `5` target shortfalls

Prompt 1.7 is an additive candidate layered on the byte-stable prompt 1.6
contract. It adds a silent distinct-idea coverage pass: identify distinct CORE
and reader-relevant ideas before drafting, synthesize records supporting the
same concept, preserve every genuinely distinct CORE concept, and adapt depth
to evidence density. It explicitly retains v1.6 ancestry, provenance,
dispute-state, no-dump, no-inventory, and no-fixed-length safeguards.

Prompt 1.7 system prompt SHA-256:

`cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614`

The frozen v1.6 system prompt SHA-256 remains:

`befaadae050b039ee61d475fa7c8ddd2dfc4e3fc22bf85f93bb5efd571e2f52b`

Diagnostic namespace:

`.bhf-data/bhf-commentary-candidates/renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1/`

## Frozen diagnostic scope

Exactly these seven chapters were rendered once:

1. Isaiah 13
2. Romans 3
3. 1 Corinthians 14
4. Revelation 20
5. Revelation 21
6. Exodus 14 (control)
7. Deuteronomy 10 (control)

Renderer contract: `gpt-5.6-sol`, effort `medium`, prompt `1.7`.

The handoff preserved each prompt-1.6 source packet identity, evidence hash,
synthesis hash, raw response, parsed response, structural validation, frozen
reader-relevance scoring, and Gate v2.1 evaluation. The immutable response
import contains exactly seven raw JSON files.

Frozen contracts remained:

- `essential-passage-context-v2`
- `reader-relevance-eligibility-v1`
- `commentary-richness-clusters-v2`
- `commentary-richness-policy-v3-reader-relevance`
- `commentary-richness-gate-v2.1`

## Prompt 1.6 versus prompt 1.7

| Chapter | 1.6 structural | 1.7 structural | Weighted 1.6 → 1.7 | Core 1.6 → 1.7 | Eligible ideas 1.6 → 1.7 | Categories 1.6 → 1.7 | Dump 1.6 → 1.7 | Gate 1.7 | Interpretation |
|---|---|---|---:|---:|---:|---:|---|---|---|
| Isaiah 13 | ACCEPTED | ACCEPTED | .5000 → 1.0000 | 1.0000 → 1.0000 | .5000 → 1.0000 | .7500 → 1.0000 | NONE → NONE | PASS | RESOLVED |
| Romans 3 | ACCEPTED | ACCEPTED | .4000 → .8000 | 0.0000 → 1.0000 | .5000 → .7500 | .5000 → 1.0000 | NONE → NONE | PASS | RESOLVED |
| 1 Corinthians 14 | ACCEPTED | ACCEPTED | .7143 → .7143 | 1.0000 → 1.0000 | .7143 → .7143 | .8333 → .8333 | NONE → NONE | PASS | UNCHANGED |
| Revelation 20 | ACCEPTED | ACCEPTED | .6667 → .8056 | 1.0000 → 1.0000 | .6667 → .8333 | .8000 → 1.0000 | NONE → NONE | PASS | RESOLVED |
| Revelation 21 | ACCEPTED | ACCEPTED | .4615 → .4615 | 1.0000 → 1.0000 | .5000 → .5000 | 1.0000 → 1.0000 | NONE → NONE | QUALITY_FAIL | UNCHANGED |
| Exodus 14 | ACCEPTED | ACCEPTED | 1.0000 → 1.0000 | 1.0000 → 1.0000 | 1.0000 → 1.0000 | 1.0000 → 1.0000 | NONE → NONE | PASS | CONTROL_STABLE |
| Deuteronomy 10 | ACCEPTED | ACCEPTED | 1.0000 → 1.0000 | 1.0000 → 1.0000 | 1.0000 → 1.0000 | 1.0000 → 1.0000 | NONE → NONE | PASS | CONTROL_STABLE |

Aggregate diagnostic result:

- Structural validity: `7/7`
- Structural rejections: `0`
- Hard provenance codes: none
- 1 Corinthians 14 ancestry regression: none; no `SYNTHESIS_ANCESTRY_MISMATCH`
- Core coverage: `1.0000` for all seven; Romans 3 recovered from `0.0000` to `1.0000`
- `HIGH` dumps: `0`
- Controls: clean and unchanged
- Prior failure cases materially improved: `false` under the strict all-five comparison because 1 Corinthians 14 and Revelation 21 were unchanged
- Prior failure cases at target: `false` (`3/5` resolved, `2/5` unchanged)
- Quality failures: `1` (Revelation 21)

## Qualitative review

The seven fresh responses generally read like knowledgeable reader-facing
explanations. They did not expose evidence inventory, repeat “another piece of
evidence” phrasing, or trigger HIGH dump diagnostics. Isaiah 13, Romans 3, and
Revelation 20 showed useful breadth without becoming mechanically longer.
Exodus 14 and Deuteronomy 10 remained bounded controls; Deuteronomy 10 stayed
concise.

Romans 3 is the clearest success: the response naturally preserves Jewish
advantage, universal sin, justification, contested terminology, and one-God
inclusion, with full CORE and category coverage. Revelation 21 is readable and
not a database dump, but its nine coherent blocks still consume only `4.8` of
`10.4` eligible weighted idea units, leaving the richness result unchanged.
1 Corinthians 14 is also readable and preserves the recovered ancestry behavior,
but its eligible utilization and category coverage remain unchanged, including
the same missing history category under the frozen scorer.

The detailed bounded review is stored at:

`evaluation/qualitative-review.json`

## Tests

Focused protection suite:

`51 passed, 1 warning`

The suite covered prompt 1.6 immutability, prompt 1.7 resolution and hashes,
ancestry/provenance safeguards, the seven-case manifest and deterministic
selection, renderer-remediation regressions, renderer qualification v2,
richness scoring, eligibility, and Gate v2.1. The warning is the pre-existing
duplicate ZIP-member warning in the response-manifest rejection test.

Direct commentary validation and external-import suite:

`76 passed`

## Final decision and next step

`PROMPT_1_7_SELECTION_BREADTH_NOT_READY`

Prompt 1.7 successfully recovered Romans 3 CORE coverage and improved Isaiah
13 and Revelation 20 without dump or control regressions. It did not establish
reliable selection breadth across the full failure set: 1 Corinthians 14 and
Revelation 21 remained unchanged, and Revelation 21 remained a quality failure.

Do not implement prompt 1.8 in this task. The smallest next remediation should
focus on dense-chapter selection persistence—especially why a renderer can
acknowledge many distinct concepts in prose while still consuming the same
eligible clusters—without changing the frozen scorer, evidence, or synthesis.
