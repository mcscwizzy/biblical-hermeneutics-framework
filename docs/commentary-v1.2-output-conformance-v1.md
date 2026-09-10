# Commentary v1.2 output conformance v1

Status: **FAILED bounded replication; do not advance to production policy**

Diagnostic namespace:

`.bhf-data/bhf-commentary-candidates/commentary-output-conformance-v1-d278cba2d2151d1b4242`

The frozen source was the provenance-binding pilot namespace
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04`, at source result `SCALE_PILOT_NOT_READY`. The current renderer contract stayed frozen at prompt `1.7`, `reader-level-idea-projection-v1`, `reader-level-idea-ancestry-envelope-v1`, and `reader-provenance-binding-v1`. Renderer identity was `gpt-5.6-sol`, effort `medium`, with runtime self-attestation disabled.

## Historical five failures

All five were JSON objects and schema-shaped renderer payloads. The existing validator, scorer, provenance binding, ancestry envelope, synthesis, CKL, and evidence routing were not changed.

| Chapter | Raw response SHA-256 | Existing rejection | Exact field | JSON/schema parse | Prose elsewhere | Provenance otherwise valid | Diagnosis |
|---|---|---|---|---|---|---|---|
| Numbers 2 | `a53939a0aea45828e4c60ecd3234e9193b94dbbc1c8df2ad3a657ed13fc56ad0` | `VALIDATION_FAILED` | literal `sections: []` | yes / yes | no | yes, vacuously; no paths emitted | generation-side empty required content |
| 2 Kings 4 | `49aab48aff3e6d10799da7b791464b65d3958097627e88f9c3fa3a0cacbf791f` | `VALIDATION_FAILED` | literal `sections: []` | yes / yes | no | yes, vacuously; no paths emitted | generation-side empty required content |
| Psalms 103 | `efcab580bcb4173fead6fced6aa1bddee8c8f4d0677464e0e5e4b5579140b5e2` | `VALIDATION_FAILED` | literal `sections: []` | yes / yes | no | yes, vacuously; no paths emitted | generation-side empty required content |
| Numbers 1 | `bbe33f11059ec8ec5ca93a83c0452e465746aff293d3828a9d6396c26f856f73` | `MALFORMED_VERSE_REFERENCE` | `sections[2].blocks[0].verse_refs[0] = "Numbers 1"` | yes / yes | yes, in the other blocks | yes | generation-side chapter-only reference; normalization cannot infer a verse |
| Psalms 19 | `4047d324968fdddfd2fb15a2993bae45264838300a3eb14ca656f6e48d5a50ce` | `VALIDATION_FAILED` | literal `sections: []` | yes / yes | no | yes, vacuously; no paths emitted | generation-side empty required content |

For Numbers 1, the intended chapter is unambiguous, but the emitted value does not specify a verse or range. `Numbers 1:1-54` is present elsewhere in the response, but assigning that range to the malformed block would be semantic guessing. It is therefore rejected and eligible for structural retry.

## Conformance architecture

The isolated implementation is `commentary-output-conformance-v1` in `bhf_agent/chapter_commentary/output_conformance.py`:

```text
raw LLM bytes
  -> strict JSON parse
  -> deterministic output conformance
  -> canonical payload
  -> existing provenance binding and structural validator
  -> existing ancestry audit and richness scorer
```

Permitted normalization is limited to:

- wrapping one non-empty `verse_refs` string as a one-item array;
- serializing a parseable, unambiguous Scripture reference to the canonical CKL form, such as `Rom 3 : 1` to `Romans 3:1`;
- recording every such event in the conformance audit.

The layer rejects empty `sections`, empty section `blocks`, missing required machine fields, malformed references, and chapter-only references in ordinary sections. It never invents prose, evidence, synthesis, reader ideas, or provenance. Provenance paths are still resolved only by `reader-provenance-binding-v1`.

## Structural retry policy

Only mechanically unusable output can trigger a retry. A chapter receives at most two total attempts. The retry uses the identical frozen system prompt, user prompt, renderer, model effort, evidence, synthesis, projection, ancestry envelope, and provenance binding. Attempts are immutable and retain separate raw hashes, rejection reasons, conformance events, canonical payloads, parsed results, and validation results.

Quality failures never trigger a retry: weighted coverage, eligible utilization, richness shortfall, core/category omission, Gate QUALITY_FAIL, readability, style, prose length, or scorer disagreement are excluded.

## Five-chapter replication

The fresh diagnostic generated attempt 1 once per chapter and used one structural retry for four chapters. There were no deterministic normalization events.

| Measure | Result |
|---|---:|
| First-attempt structural success | `1/5` (`20%`) |
| Deterministic-normalization recovery | `0` |
| Structural retries | `4` |
| Retry successes | `0` |
| Final structural validity | `1/5` (`20%`) |
| Final provenance-path validity | `1/5` among final validated artifacts |
| Final ancestry-safe | `1/5` among final validated artifacts |
| Hard provenance errors | `0` |
| HIGH dumps | `0` |
| Validator weakening | none |
| Invented prose during normalization | none |
| Manual response editing | none |

Numbers 1 was a clean first-attempt result. Its final quality metrics were weighted coverage `1.0`, core coverage `1.0`, eligible utilization `1.0`, category coverage `1.0`, Gate `PASS`, readability `PASS`, and word count `129`.

Numbers 2, 2 Kings 4, Psalms 103, and Psalms 19 emitted empty sections on attempt 1 and emitted byte-identical empty-section responses on attempt 2. Their final quality metrics are correctly absent because no valid commentary artifact existed. This is persistent empty-output generation behavior, not a normalization failure.

The replication therefore does not meet the requested `5/5` success criterion and is classified `FAILED`. No full 75-chapter generation was started.

## Counterfactual and next step

The diagnostic comparison artifact keeps the 70 historically usable responses unchanged and does not rewrite the frozen pilot. Because the fresh replication recovered only one of the five failures, the modeled population remains `71/75` structurally valid (`94.67%`), below the unchanged `98%` threshold. The frozen pilot’s quality thresholds were not tuned.

Do not create prompt 1.8. The smallest next action is a single-chapter renderer-transport diagnostic for Numbers 2 using the exact same contract, capturing the provider/app-server completion receipt alongside the raw response. Its purpose is to distinguish a model-generated empty object from runtime/output-wrapper replay or truncation. Do not begin another full pilot or bulk generation until that mechanical cause is understood.

## Tests and artifacts

Focused conformance tests cover empty sections, required-field rejection, deterministic reference normalization, ambiguous-reference rejection, valid no-op behavior, retry bounds, quality-failure non-retry, strict JSON parsing, provenance-binding compatibility, and checksum reproducibility.

The relevant regression suites passed: **95 tests** in **147.12 seconds**, including conformance, v1.2 validation, provenance binding, reader projection, scale-pilot provenance binding, richness, and richness-cluster suites. The final namespace contains a manifest, source failure identities, frozen contract identities, normalization rules, fresh attempt histories, raw responses, canonical payloads where valid, parsed/validation results, replication and comparison reports, and checksums.
