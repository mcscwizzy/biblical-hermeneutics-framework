# Commentary v1.2 renderer qualification v2

Status: `AWAITING_EXTERNAL_RESPONSE_BUNDLE`

This is a clean qualification handoff for renderer prompt `1.6`. No fresh
renderer response was available in the repository at handoff time, so this
document does not claim a qualification pass or evaluate placeholder output.

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

The new qualification-harness contract suite passed `4` tests. The complete
focused commentary/scoring/renderer suite, including that harness, passed `78`
tests with one expected duplicate-ZIP warning. No response import has occurred
at this boundary.

The separate existing canary module reported `3 passed, 1 failed`. Its failure
is outside this qualification: the pre-existing dirty canary packets carry
renderer prompt `1.5`, while `tests/test_commentary_v12_canary.py` still asserts
prompt `1.2`. The canary files and test were not changed.

## Priority diagnostics after import

The final evaluation must explicitly inspect Revelation 21 as the richness
stress test, Job 1 as the mixed-evidence case, 1 Corinthians 14 for
`SYNTHESIS_ANCESTRY_MISMATCH`, and Exodus 14/Deuteronomy 10 as scoring-noise
controls. The evaluator records historical-vs-new metrics, deltas, category
coverage, eligible idea utilization, dump severity, Gate v2.1 outcome, and a
short diagnostic classification for all 21 chapters.

## Recommended next step

Run the exact external GPT-5.6 Sol generation against the prepared request
bundle. Import only the verified complete response bundle, then run evaluation.
Do not remediate renderer behavior, alter scoring, regenerate CKL, or begin
scale expansion until the resulting 21-chapter qualification report gives a
clear `RENDERER_QUALIFICATION_PASS` or `RENDERER_QUALIFICATION_NOT_QUALIFIED`.
