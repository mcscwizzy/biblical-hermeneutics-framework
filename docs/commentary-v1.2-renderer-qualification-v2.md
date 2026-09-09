# Commentary v1.2 renderer qualification v2

Status: `RENDERER_QUALIFICATION_NOT_QUALIFIED`

This document preserves the clean qualification handoff for renderer prompt
`1.6` and records the completed frozen 21-chapter experiment. The imported
responses are fresh GPT-5.6 Sol outputs at medium effort. No response was
retried or edited after evaluation, and no prompt, CKL, evidence, clustering,
eligibility, scoring, threshold, or Gate behavior was changed.

## Completed qualification

- Qualification execution starting SHA: `b82073766430e4a8bf6f2e28c34e0c4c67186f9e`
- Renderer: `gpt-5.6-sol`
- Reasoning effort: `medium`
- Renderer prompt: `1.6`
- Prompt-1.6 system prompt SHA-256: `befaadae050b039ee61d475fa7c8ddd2dfc4e3fc22bf85f93bb5efd571e2f52b`
- Response bundle: `renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-responses.zip`
- Response bundle SHA-256: `ee0127c1523f6b524c015d93c05ca627f4f7d2d6f2bc4ab94c92397581e2362d`
- Response manifest SHA-256: `c397715f8a6d30e63af5e82159caa10fc97da908f44e4c4a500d83bacad7fee8`
- Import result: `IMPORTED`, 21 responses, immutable raw bytes
- Final result: `RENDERER_QUALIFICATION_NOT_QUALIFIED`

The first import attempt correctly rejected an explicit `responses/` directory
member as an extra ZIP member. The archive was repackaged without changing any
response or manifest content, reverified at 22 exact members, and then imported
successfully.

## Aggregate result

- Total renderer chapters: `21`
- Structurally valid: `21`
- Structurally rejected: `0`
- Structural rejection reasons: none
- Evidence-bearing valid chapters: `19`
- Reader-relevance weighted coverage: `.8478`
- Core coverage: `.9474`
- Eligible idea utilization: `.8498`
- Eligible unit utilization: `.6579`
- Raw synthesis utilization: `.5860`
- Category coverage: `.9325`
- HIGH dump count: `0`
- Gate v2.1 PASS count: `19`
- Gate quality-fail count: `2`
- Qualification-target passes: `14`
- Qualification-target shortfalls: `5`
- Chapters below the per-chapter category target: `5`
- Outcome transitions from historical prompt 1.5: `18 PASS->PASS`,
  `2 PASS->QUALITY_FAIL`, and `1 REJECTED->PASS`

The aggregate reader-relevance and eligible-utilization means clear their
thresholds, and all responses are structurally valid with no dump behavior.
Qualification nevertheless fails because the frozen contract also applies
core and relevant coverage expectations at chapter level. The five target
shortfalls are Isaiah 13, Romans 3, 1 Corinthians 14, Revelation 20, and
Revelation 21. Romans 3 omitted a core idea; the other failures are primarily
eligible-idea/category richness omissions.

## Per-chapter result

`Hist.` is the historical prompt-1.5 corrected-v3 weighted coverage. `Delta`
is the new prompt-1.6 weighted-coverage change from that value. All chapters
were structurally accepted, so every structural-failure entry is `none`.

| Reference | Structural / failure | Weighted | Core | Eligible ideas | Category | Dump | Gate v2.1 | Qualification | Hist. / delta | Diagnostic |
|---|---|---:|---:|---:|---:|---|---|---|---|---|
| Exodus 14 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS; concise scoring-noise control remained complete |
| Leviticus 8 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Numbers 36 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Deuteronomy 10 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS; concise scoring-noise control remained complete |
| Ruth 2 | accepted / none | .8649 | 1.0000 | .8000 | 1.0000 | NONE | PASS | PASS | .8649 / +.0000 | STABLE_PASS |
| 2 Samuel 15 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Ezra 8 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Nehemiah 7 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Job 1 | accepted / none | .7500 | 1.0000 | .7500 | 1.0000 | NONE | PASS | PASS | .7500 / +.0000 | STABLE_PASS; disputed/contextual material stayed calibrated at the threshold |
| Isaiah 13 | accepted / none | .5000 | 1.0000 | .5000 | .7500 | NONE | PASS | BELOW_TARGET | 1.0000 / -.5000 | CATEGORY_REGRESSION; eligible context and one category were omitted |
| Amos 2 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Matthew 4 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | .7879 / +.2121 | IMPROVED_RENDERER |
| Matthew 19 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Matthew 20 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Romans 3 | accepted / none | .4000 | .0000 | .5000 | .5000 | NONE | QUALITY_FAIL | BELOW_TARGET | .8000 / -.4000 | CORE_REGRESSION; core and category material were omitted |
| 1 Corinthians 14 | accepted / none | .7143 | 1.0000 | .7143 | .8333 | NONE | PASS | BELOW_TARGET | historical response rejected / n.a. | RICHNESS_SHORTFALL; ancestry recovered but reader-facing/category breadth remained low |
| Hebrews 8 | accepted / none | .7500 | 1.0000 | .7143 | .8333 | NONE | PASS | PASS | .8636 / -.1136 | CATEGORY_REGRESSION at the accepted boundary |
| Revelation 4 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Revelation 19 | accepted / none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS | 1.0000 / +.0000 | STABLE_PASS |
| Revelation 20 | accepted / none | .6667 | 1.0000 | .6667 | .8000 | NONE | PASS | BELOW_TARGET | .8056 / -.1389 | CATEGORY_REGRESSION; eligible breadth remained below target |
| Revelation 21 | accepted / none | .4615 | 1.0000 | .5000 | 1.0000 | NONE | QUALITY_FAIL | BELOW_TARGET | .6635 / -.2020 | RICHNESS_SHORTFALL; no dump, but the main stress response omitted too many eligible ideas |

## Priority diagnostics

- **1 Corinthians 14:** The fresh response is structurally accepted with no
  `SYNTHESIS_ANCESTRY_MISMATCH`, confirming prompt 1.6's ancestry recovery in
  the full qualification. Its `.7143` weighted coverage is below `.75`, and
  category coverage is `.8333`, so it remains below the qualification target
  for richness rather than provenance.
- **Revelation 21:** Structural validity, core coverage, and full category
  representation were preserved with no dump. Weighted coverage `.4615` and
  eligible idea utilization `.5000` are below both the prior prompt-1.6
  diagnostic (`.5288`) and the historical prompt-1.5 v3 counterfactual
  (`.6635`). This is a reader-facing richness omission, not encyclopedic dump
  behavior.
- **Job 1:** Passed exactly at `.7500` weighted coverage, with `1.0000` core and
  category coverage, `.7500` eligible idea utilization, and no dump. The mixed
  contextual/disputed material remained calibrated.
- **Exodus 14:** Passed at `1.0000` across weighted, core, eligible-idea, and
  category coverage with no dump. The corrected denominator did not induce
  generic entity expansion.
- **Deuteronomy 10:** Also passed at `1.0000` across all four coverage measures
  with no dump, preserving concise reader relevance.

## Starting point

- Branch: `feat/commentary-v1.2-enrichment`
- Starting SHA: `13cc63fb42be92b235233afe569212d966c31f0b`
- Final SHA: recorded in the completion handoff after the bounded qualification
  machinery and frozen request namespace are committed.
- Historical qualification: `renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a`
- Historical renderer remediation: `renderer-remediation-v1-gpt-5.6-sol-2d03bb002c24cdbcca72`
- Accepted scoring-remediation outcome: `SCORING_REMEDIATION_PASS`

The worktree contained unrelated pre-existing v1.2 enrichment, renderer
remediation, and scoring-remediation changes. They were preserved. The new
qualification files are isolated from those namespaces.

## Immutable qualification namespace

The prepared namespace is:

`.bhf-data/bhf-commentary-candidates/renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31/`

It contains the qualification manifest, candidate packets, prompt text
handoff, external-generation instructions, request bundle, metadata, and
prepared checksum index. Response, parsed-output, structural, richness, gate,
and aggregate artifacts are written only after a verified complete response
bundle is imported.

The namespace ID is deterministic from the frozen source qualification
identity, packet identities, prompt-1.6 hash, renderer identity, and frozen
contract versions. All writes use immutable artifact semantics.

## Frozen corpus

The corpus is byte-for-byte rechecked against the historical qualification
manifest (`qualification_manifest_identity`
`927a895949882148699e11fad489a06510824fd6ad70843cb76b33cb748947fa`):

1. Exodus 14
2. Leviticus 8
3. Numbers 36
4. Deuteronomy 10
5. Ruth 2
6. 2 Samuel 15
7. Ezra 8
8. Nehemiah 7
9. Job 1
10. Isaiah 13
11. Amos 2
12. Matthew 4
13. Matthew 19
14. Matthew 20
15. Romans 3
16. 1 Corinthians 14
17. Hebrews 8
18. Revelation 4
19. Revelation 19
20. Revelation 20
21. Revelation 21

The four historical DATA_GAP exclusions remain excluded. Every candidate
packet records its source packet ID/hash/file SHA, evidence hash, and synthesis
hash.

## Renderer and frozen contract

- Renderer: `gpt-5.6-sol`
- Effort: `medium`
- Renderer prompt: `1.6`
- Prompt resolver: `bhf_agent.chapter_commentary.prompts.system_prompt_for_version`
- Prompt-1.6 system prompt SHA-256: `befaadae050b039ee61d475fa7c8ddd2dfc4e3fc22bf85f93bb5efd571e2f52b`
- Core classifier: `essential-passage-context-v2`
- Reader-relevance eligibility: `reader-relevance-eligibility-v1`
- Richness clustering: `commentary-richness-clusters-v2`
- Richness policy: `commentary-richness-policy-v3-reader-relevance`
- Gate: `commentary-richness-gate-v2.1`

The harness invokes v3 scoring with the canonical chapter text and preserves
the scorer's full non-optional inventory for dump detection. It reports raw
unit utilization separately from eligible reader-facing idea utilization. No
threshold, classifier, cluster, or gate implementation was changed for this
qualification.

Qualification aggregation follows the accepted semantics: weighted
reader-relevance coverage and eligible idea utilization are arithmetic means
over structurally valid `AVAILABLE` chapters. Structural validity, core
coverage, dump severity, and category floors are also checked per chapter.
The reader-facing weighted coverage target is `>= 0.75`; it is not replaced by
Gate v2.1's enrichment threshold.

## Historical baseline

The original full-corpus prompt-1.5 qualification was `NOT_QUALIFIED`:

- Structural validity: `20 / 21`
- Structural rejection: one `SYNTHESIS_ANCESTRY_MISMATCH` in 1 Corinthians 14
- Gate quality failures: `4`
- Corrected v3 counterfactual weighted coverage: `.9186`
- Corrected v3 counterfactual core coverage: `1.0000`
- Corrected v3 counterfactual eligible idea utilization: `.9154`
- Corrected v3 counterfactual category coverage: `1.0000`
- Corrected v3 counterfactual HIGH dumps: `0`

The prior five-case prompt-1.6 remediation is not used as the new corpus. Its
corrected diagnostic values remain comparison context only: Exodus 14 `1.0000`,
Deuteronomy 10 `1.0000`, Job 1 `.7500`, 1 Corinthians 14 `.7143` with ancestry
recovered, and Revelation 21 `.5288`. The full-corpus prompt-1.5 counterfactual
for Revelation 21 is separately recorded as `.6635`; these values come from
different response sets and must not be conflated.

## Generation and import procedure

Prepare or reverify the namespace and request bundle:

```sh
.venv/bin/python tools/commentary_renderer_qualification_v2.py prepare
```

Give the resulting input ZIP to GPT-5.6 Sol at medium effort. Use every packet's
exact system and user prompt, return one raw JSON object per chapter, and build
the response ZIP with the exact manifest identity and filenames. The required
response manifest can be printed with:

```sh
.venv/bin/python tools/commentary_renderer_qualification_v2.py response-template \
  --qualification-root .bhf-data/bhf-commentary-candidates/renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31
```

After the external response bundle is verified to be the complete GPT-5.6 Sol
return for this qualification, import it with:

```sh
.venv/bin/python tools/commentary_renderer_qualification_v2.py import \
  --qualification-root .bhf-data/bhf-commentary-candidates/renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31 \
  --bundle <PATH_TO_VERIFIED_SOL_RESPONSE_BUNDLE.zip>
```

Then evaluate the immutable imported bytes:

```sh
.venv/bin/python tools/commentary_renderer_qualification_v2.py evaluate \
  --qualification-root .bhf-data/bhf-commentary-candidates/renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31
```

The import command refuses a missing/extra response, altered packet identity,
wrong renderer or effort, wrong prompt version, duplicate ZIP member, or
corrupt JSON. The evaluator writes per-chapter parsed outputs and diagnostics
plus the aggregate comparison report under the immutable namespace.

## Tests

After immutable import and evaluation, the qualification-harness contract suite
passed `4 / 4` tests. A broader focused commentary/scoring/renderer suite passed
`82 / 82` tests:

- `tests/test_commentary_renderer_qualification_v2.py`
- `tests/test_commentary_renderer_remediation.py`
- `tests/test_commentary_v12_richness.py`
- `tests/test_commentary_v12_richness_clusters.py`
- `tests/test_commentary_v12_validation.py`
- `tests/test_commentary_v12_external_import.py`

The separate existing canary module reported `3 passed, 1 failed`. Its failure
is outside this qualification: the pre-existing dirty canary packets carry
renderer prompt `1.5`, while `tests/test_commentary_v12_canary.py` still asserts
prompt `1.2`. The canary files and test were not changed.

## Recommended next step

Do not freeze prompt 1.6 as the Commentary v1.2 renderer contract and do not
begin the 60–100 chapter scale qualification. The smallest remaining defect is
renderer selection breadth: structurally valid prose omits eligible
reader-relevant ideas and, in Romans 3, a core idea. The next bounded remediation
should be a prompt-only five-chapter diagnostic over Isaiah 13, Romans 3,
1 Corinthians 14, Revelation 20, and Revelation 21 using the same frozen
evidence and scoring contract. It should target representative eligible/category
breadth without increasing dump behavior. That remediation is not implemented
as part of this qualification.
