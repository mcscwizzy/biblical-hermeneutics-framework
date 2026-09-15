# Commentary v1.2 provenance-binding scale pilot

## Decision

`SCALE_PILOT_NOT_READY`

No: BHF should not yet begin controlled generation of the remaining Commentary v1.2 prose. Deterministic provenance binding removed the systemic ancestry blocker, but the frozen renderer population missed the readiness floor because 5/75 chapters were structurally invalid. Four of those five were syntactically valid empty commentaries (`sections: []`); the fifth used the chapter-level verse reference `Numbers 1`, which the frozen validator correctly rejected as `MALFORMED_VERSE_REFERENCE`.

The smallest population-supported remediation is a bounded renderer output-completeness/schema-conformance control that prevents an empty `sections` array and enforces verse-level `verse_refs` before a response is accepted as a generation result. This recommendation does not change prompt 1.7, projection, ancestry, provenance binding, synthesis, evidence routing, CKL, scoring, or thresholds. Do not create prompt 1.8 and do not tune Galatians 3.

## Identity and frozen contract

- Starting SHA: `6955ac414cea9a50062d2ec9e39741460a97bc31`
- Source pilot: `.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-922472547555015a3ced`
- Source manifest identity: `eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394`
- Source frozen-corpus SHA-256: `5fb7f7c2f813a3013b1a3dc9c08431e35e71b15a254c84aa1daea1928cab76c9`
- Ordered-reference SHA-256: `876d0fbca0c3986a0c40c9e87b1028b826d2d510dd74c8c2875462482f4538ea`
- Exact source corpus reused: yes, 75 unique chapters in unchanged order and batches (`13, 13, 13, 12, 12, 12`)
- New namespace: `.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04`
- New manifest identity: `ecb771decc370dffe177d38cefbe0463a0c83444a8ea7642ca060384bcc72e5f`
- Seen/unseen: 5/70; 93.33% unseen
- Renderer: `gpt-5.6-sol`, effort `medium`; one generation per chapter, zero quality retries, no runtime self-attestation

| Component | Version | Source SHA-256 |
|---|---|---|
| Prompt | `1.7` | `332b39b60152517d12145511afd9fba9572d8cf985dda7238587f6cb56cf1ff4` |
| Reader projection | `reader-level-idea-projection-v1` | `bb6b7d6ac97501d41ad88d6c3cb398d61a5bb307f7b4a2fb460dd05256a377f9` |
| Ancestry presentation | `reader-level-idea-ancestry-envelope-v1` | `5ad4c40743b179cdf6a811e879c52ba97b81d45e740ca2289fe65439fc7ef61f` |
| Provenance binding | `reader-provenance-binding-v1` | `dc14722dda787e2b096783708b5d9f846aa5328c756eeceb6a0ab0607baaef53` |
| Validator | unchanged | `b4bbb3ce24a2d84c3c026138626e2b8c7337d8fe029db31da5a6c28bed2880f2` |
| Scorer | unchanged | `beb0a73fd403c5013cb8eedf7e871c855686c2960f5dfd2afc2b0642cb6b7074` |

Frozen scoring remained `essential-passage-context-v2`, `reader-relevance-eligibility-v1`, `commentary-richness-clusters-v2`, `commentary-richness-policy-v3-reader-relevance`, and `commentary-richness-gate-v2.1`.

## Batch results and prior Batch 001 comparison

| Batch | Chapters | Classification distribution | Catastrophic stop |
|---|---:|---|---|
| 001 | 13 | 13 `CLEAN_PASS` | no |
| 002 | 13 | 11 `CLEAN_PASS`; 2 `RICHNESS_SHORTFALL` | no |
| 003 | 13 | 12 `CLEAN_PASS`; 1 `STRUCTURAL_FAILURE` | no |
| 004 | 12 | 11 `CLEAN_PASS`; 1 `STRUCTURAL_FAILURE` | no |
| 005 | 12 | 9 `CLEAN_PASS`; 1 `RICHNESS_SHORTFALL`; 1 `SCORER_RENDERER_EDGE_CASE`; 1 `STRUCTURAL_FAILURE` | no |
| 006 | 12 | 9 `CLEAN_PASS`; 1 `RICHNESS_SHORTFALL`; 2 `STRUCTURAL_FAILURE` | no |

The truncated source Batch 001 had 8 clean passes, 1 core omission (Galatians 3), and 4 provenance failures (Romans 3, Joshua 10, Leviticus 1, Genesis 5). The fresh provenance-bound Batch 001 achieved 13/13 clean passes, 13/13 structural and path validity, zero ancestry mismatches, zero hard provenance errors, full core/category coverage, 13 Gate passes, and zero HIGH dumps. This is direct population evidence that `reader-provenance-binding-v1` removed the prior systemic ancestry-envelope failure mechanism.

## Aggregate metrics

| Metric | Result |
|---|---:|
| Chapters generated | 75 |
| Structural validity | 93.33% |
| Provenance-path validity | 100.00% |
| Ancestry safe | 100.00% |
| Hard-provenance safe | 100.00% |
| Gate PASS | 89.33% |
| Core coverage rate | 93.33% |
| Category coverage rate | 93.33% |
| HIGH dump rate | 0.00% |
| Clean-pass rate | 86.67% |
| Edge-case rate | 1.33% |
| Genuine renderer failure rate | 12.00% |
| Weighted mean / median | 0.9066 / 1.0000 |
| Eligible utilization mean / median | 0.9080 / 1.0000 |
| Average prose words | 246.7 |

Weighted percentiles were P10 `0.6679`, P25 `1.0000`, P50 `1.0000`, P75 `1.0000`, and P90 `1.0000`. Structural failures are conservatively represented as zero in these population aggregates.

Lowest weighted chapters: 2 Kings 4, Numbers 1, Numbers 2, Psalms 103, and Psalms 19 (structural, no score); Acts 17 `0.5766`; Revelation 21 `0.5962`; John 2 `0.6410`; Jeremiah 29 `0.7083`; Romans 14 `0.7966`.

Lowest eligible-utilization chapters: 2 Kings 4, Numbers 1, Numbers 2, Psalms 103, and Psalms 19 (structural, no score); Acts 17 `0.5882`; Revelation 21 `0.6250`; John 2 `0.6667`; Jeremiah 29 `0.7500`; Romans 14 `0.8000`.

## Seen versus unseen

| Population | N | Structural | Provenance path | Gate PASS | Weighted mean / median | Eligible mean / median | Core | Failure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Seen | 5 | 100.00% | 100.00% | 100.00% | 0.8804 / 1.0000 | 0.8917 / 1.0000 | 100.00% | 0.00% |
| Unseen | 70 | 92.86% | 100.00% | 88.57% | 0.9084 / 1.0000 | 0.9091 / 1.0000 | 92.86% | 12.86% |

Weighted and eligible scores generalized well among structurally valid unseen chapters, and provenance generalized perfectly. The readiness comparison nevertheless fails because all five structural failures occurred in the unseen population.

## Density analysis

| Density | N | Weighted mean / median | Eligible mean / median | Avg words | Structural | Provenance / ancestry failures | Richness failures | HIGH dumps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sparse | 17 | 0.8824 / 1.0000 | 0.8824 / 1.0000 | 119.4 | 2 | 0 / 0 | 0 | 0 |
| Medium | 32 | 0.9375 / 1.0000 | 0.9375 / 1.0000 | 210.0 | 2 | 0 / 0 | 0 | 0 |
| Dense | 26 | 0.8843 / 1.0000 | 0.8883 / 1.0000 | 375.3 | 1 | 0 / 0 | 4 | 0 |

Binding and ancestry remained stable as density increased. Richness misses clustered in dense chapters, while empty output occurred across sparse, medium, and dense inputs and is therefore not solely a density failure.

## Failure clusters

- Output completeness/schema conformance: 5 structural failures. Numbers 2, 2 Kings 4, Psalms 103, and Psalms 19 returned empty `sections`; Numbers 1 used one malformed chapter-level verse reference. Four empty outputs across four different batches are the dominant recurring systemic issue.
- Contextual breadth/richness: Acts 17, John 2, Jeremiah 29, and Psalms 2. The first three are dense chapters; Psalms 2 had full weighted/core/eligible/category coverage but a `PASS_WITH_WARNING` LOW-dump result under the frozen gate.
- Scorer/prose semantic mismatch: Revelation 21. It was structurally, provenance, ancestry, core, category, dump, Gate, concept-representation, and readability safe; all 8/8 projected concepts were represented, supporting the bounded `SCORER_RENDERER_EDGE_CASE` classification.
- Provenance/path binding: none.
- Core omission: none among structurally valid prose.
- Category shortfall: none among structurally valid prose.
- Readability regression: the four empty responses are unusable; no systemic prose readability regression appeared among non-empty responses.

## Human readability review

The deterministic 13-chapter sample was: 2 Kings 4, Numbers 1, Numbers 2, Psalms 103, 1 Corinthians 14, 1 Peter 1, 1 Timothy 2, John 2, Acts 17, Jeremiah 29, Psalms 19, Psalms 2, and John 5. It includes unseen sparse/medium/dense chapters, high and low scorers, and genuine failures.

The four empty outputs were correctly judged unusable. Numbers 1 was natural, coherent, restrained, and useful, but its invalid `Numbers 1` verse reference remains a hard structural rejection. The eight other non-empty selections were natural and coherent, avoided evidence-dump and checklist feel, exposed no internal provenance terminology, and did not show awkward provenance-driven wording. Acts 17 was the longest reviewed response (1,039 words) but remained organized and useful; John 5 and Psalms 2 demonstrated that sparse output could remain readable. No hard provenance result was overridden on prose grounds.

## Galatians 3 and Revelation 20

- Galatians 3 recovered as `CLEAN_PASS`: structural/path valid, zero ancestry mismatches and hard provenance errors, weighted `0.8684`, core `1.0000`, eligible `0.8333`, category `1.0000`, Gate PASS, no dump, readability PASS. It was generated fresh and not tuned.
- Revelation 20 was generated in its original Batch 006 position and was `CLEAN_PASS`: structural/path valid, zero ancestry mismatches and hard provenance errors, weighted `0.8056`, core `1.0000`, eligible `0.8333`, category `1.0000`, Gate PASS, no dump, readability PASS.

## Per-chapter results

`Str` is structural validity, `Path` path validity, `Anc` ancestry mismatches, `Prov` hard provenance errors, `Ideas` represented/projected, and `Class` final classification. `—` denotes unavailable scoring after structural rejection.

| Reference | Seen | Genre | Density | Syn | Elig | Proj | Paths | Str | Path | Anc | Prov | Wtd | Core | Util | Cat | Dump | Gate | Words | Ideas | Read | List | Class |
|---|---|---|---|---:|---:|---:|---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|---|---|
| Romans 3 | seen | Pauline Epistles | dense | 25 | 4 | 4 | 17 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 368 | 4/4 | PASS | PASS | CLEAN_PASS |
| John 5 | unseen | Gospels | sparse | 2 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 112 | 1/1 | PASS | PASS | CLEAN_PASS |
| Isaiah 3 | unseen | Major Prophets | sparse | 1 | 1 | 1 | 1 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 58 | 1/1 | PASS | PASS | CLEAN_PASS |
| Hosea 4 | unseen | Minor Prophets | medium | 6 | 2 | 1 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 285 | 1/1 | PASS | PASS | CLEAN_PASS |
| Daniel 4 | unseen | Major Prophets | sparse | 2 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 120 | 1/1 | PASS | PASS | CLEAN_PASS |
| Joshua 10 | unseen | Historical Narrative | medium | 7 | 2 | 2 | 5 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 180 | 2/2 | PASS | PASS | CLEAN_PASS |
| Leviticus 1 | unseen | Torah | medium | 20 | 3 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 135 | 2/2 | PASS | PASS | CLEAN_PASS |
| Hebrews 1 | unseen | General Epistles | dense | 36 | 4 | 3 | 9 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 291 | 3/3 | PASS | PASS | CLEAN_PASS |
| Galatians 3 | unseen | Pauline Epistles | dense | 66 | 12 | 10 | 40 | Y | Y | 0 | 0 | 0.8684 | 1 | 0.8333 | 1 | NONE | PASS | 725 | 8/10 | PASS | PASS | CLEAN_PASS |
| Acts 9 | unseen | Acts | dense | 67 | 7 | 7 | 15 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 433 | 7/7 | PASS | PASS | CLEAN_PASS |
| Genesis 5 | unseen | Torah | medium | 10 | 1 | 1 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 99 | 1/1 | PASS | PASS | CLEAN_PASS |
| Mark 8 | unseen | Gospels | sparse | 4 | 2 | 1 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 191 | 1/1 | PASS | PASS | CLEAN_PASS |
| Isaiah 2 | unseen | Major Prophets | medium | 10 | 5 | 4 | 8 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 266 | 4/4 | PASS | PASS | CLEAN_PASS |
| Malachi 4 | unseen | Minor Prophets | medium | 6 | 2 | 1 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 171 | 1/1 | PASS | PASS | CLEAN_PASS |
| John 2 | unseen | Gospels | dense | 57 | 12 | 5 | 25 | Y | Y | 0 | 0 | 0.6410 | 1 | 0.6667 | 1 | LOW | PASS_WITH_WARNING | 502 | 5/5 | PASS | PASS | RICHNESS_SHORTFALL |
| Luke 21 | unseen | Gospels | medium | 6 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 202 | 1/1 | PASS | PASS | CLEAN_PASS |
| Isaiah 52 | unseen | Major Prophets | medium | 10 | 3 | 3 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 223 | 3/3 | PASS | PASS | CLEAN_PASS |
| Numbers 33 | unseen | Torah | medium | 15 | 5 | 4 | 8 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 222 | 4/4 | PASS | PASS | CLEAN_PASS |
| Amos 7 | unseen | Minor Prophets | medium | 6 | 1 | 1 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 331 | 1/1 | PASS | PASS | CLEAN_PASS |
| 2 Kings 15 | unseen | Historical Narrative | medium | 10 | 2 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 156 | 2/2 | PASS | PASS | CLEAN_PASS |
| Colossians 2 | unseen | Pauline Epistles | medium | 8 | 1 | 1 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 258 | 1/1 | PASS | PASS | CLEAN_PASS |
| Zechariah 8 | unseen | Minor Prophets | sparse | 5 | 2 | 2 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 145 | 2/2 | PASS | PASS | CLEAN_PASS |
| Acts 17 | unseen | Acts | dense | 69 | 17 | 12 | 65 | Y | Y | 0 | 0 | 0.5766 | 1 | 0.5882 | 1 | NONE | PASS | 1039 | 9/12 | PASS | PASS | RICHNESS_SHORTFALL |
| Joshua 1 | unseen | Historical Narrative | medium | 19 | 5 | 5 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 186 | 5/5 | PASS | PASS | CLEAN_PASS |
| 2 Thessalonians 1 | unseen | Pauline Epistles | medium | 15 | 3 | 2 | 7 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 220 | 2/2 | PASS | PASS | CLEAN_PASS |
| 3 John 1 | unseen | General Epistles | medium | 11 | 2 | 2 | 11 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 107 | 2/2 | PASS | PASS | CLEAN_PASS |
| Esther 3 | unseen | Historical Narrative | medium | 6 | 2 | 2 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 338 | 2/2 | PASS | PASS | CLEAN_PASS |
| Jeremiah 49 | unseen | Major Prophets | dense | 32 | 2 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 153 | 2/2 | PASS | PASS | CLEAN_PASS |
| Romans 14 | unseen | Pauline Epistles | dense | 53 | 10 | 9 | 37 | Y | Y | 0 | 0 | 0.7966 | 1 | 0.8 | 1 | NONE | PASS | 444 | 8/9 | PASS | PASS | CLEAN_PASS |
| Hosea 1 | unseen | Minor Prophets | dense | 21 | 5 | 4 | 14 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 450 | 4/4 | PASS | PASS | CLEAN_PASS |
| Numbers 2 | unseen | Torah | sparse | 2 | 0 | 0 | 0 | N | Y | 0 | 0 | — | — | — | — | — | — | 0 | 0/0 | FAIL | PASS | STRUCTURAL_FAILURE |
| Romans 16 | unseen | Pauline Epistles | dense | 92 | 9 | 7 | 51 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 664 | 7/7 | PASS | PASS | CLEAN_PASS |
| Psalms 122 | unseen | Poetry/Wisdom | medium | 13 | 3 | 2 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 203 | 2/2 | PASS | PASS | CLEAN_PASS |
| John 12 | unseen | Gospels | medium | 10 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 95 | 1/1 | PASS | PASS | CLEAN_PASS |
| Daniel 7 | unseen | Major Prophets | dense | 40 | 4 | 3 | 10 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 407 | 3/3 | PASS | PASS | CLEAN_PASS |
| Mark 4 | unseen | Gospels | sparse | 4 | 3 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 167 | 2/2 | PASS | PASS | CLEAN_PASS |
| Judges 3 | unseen | Historical Narrative | medium | 6 | 1 | 1 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 75 | 1/1 | PASS | PASS | CLEAN_PASS |
| Matthew 27 | unseen | Gospels | dense | 27 | 3 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 220 | 2/2 | PASS | PASS | CLEAN_PASS |
| Matthew 1 | unseen | Gospels | dense | 21 | 7 | 5 | 9 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 274 | 5/5 | PASS | PASS | CLEAN_PASS |
| 1 Timothy 2 | unseen | Pauline Epistles | medium | 8 | 2 | 1 | 8 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 412 | 1/1 | PASS | PASS | CLEAN_PASS |
| Song of Songs 2 | unseen | Poetry/Wisdom | medium | 6 | 2 | 2 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 250 | 2/2 | PASS | PASS | CLEAN_PASS |
| 2 Kings 4 | unseen | Historical Narrative | medium | 18 | 0 | 0 | 0 | N | Y | 0 | 0 | — | — | — | — | — | — | 0 | 0/0 | FAIL | PASS | STRUCTURAL_FAILURE |
| Esther 1 | unseen | Historical Narrative | medium | 8 | 4 | 3 | 8 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 418 | 3/3 | PASS | PASS | CLEAN_PASS |
| Acts 8 | unseen | Acts | medium | 10 | 4 | 4 | 8 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 269 | 4/4 | PASS | PASS | CLEAN_PASS |
| 1 Peter 1 | unseen | General Epistles | dense | 32 | 6 | 3 | 14 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 372 | 3/3 | PASS | PASS | CLEAN_PASS |
| Judges 8 | unseen | Historical Narrative | medium | 6 | 1 | 1 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 84 | 1/1 | PASS | PASS | CLEAN_PASS |
| Psalms 8 | unseen | Poetry/Wisdom | medium | 16 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 66 | 1/1 | PASS | PASS | CLEAN_PASS |
| James 1 | unseen | General Epistles | medium | 19 | 5 | 3 | 17 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 521 | 3/3 | PASS | PASS | CLEAN_PASS |
| Judges 21 | unseen | Historical Narrative | medium | 9 | 5 | 4 | 9 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 233 | 4/4 | PASS | PASS | CLEAN_PASS |
| Hebrews 7 | unseen | General Epistles | medium | 17 | 6 | 4 | 11 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 325 | 4/4 | PASS | PASS | CLEAN_PASS |
| James 5 | unseen | General Epistles | dense | 22 | 4 | 3 | 16 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 473 | 3/3 | PASS | PASS | CLEAN_PASS |
| Psalms 103 | unseen | Poetry/Wisdom | medium | 6 | 0 | 0 | 0 | N | Y | 0 | 0 | — | — | — | — | — | — | 0 | 0/0 | FAIL | PASS | STRUCTURAL_FAILURE |
| Revelation 21 | seen | Apocalyptic literature | dense | 119 | 16 | 8 | 33 | Y | Y | 0 | 0 | 0.5962 | 1 | 0.625 | 1 | NONE | PASS | 365 | 8/8 | PASS | PASS | SCORER_RENDERER_EDGE_CASE |
| 2 Kings 18 | unseen | Historical Narrative | dense | 31 | 5 | 4 | 15 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 348 | 4/4 | PASS | PASS | CLEAN_PASS |
| Hosea 11 | unseen | Minor Prophets | sparse | 5 | 2 | 1 | 5 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 212 | 1/1 | PASS | PASS | CLEAN_PASS |
| Psalms 137 | unseen | Poetry/Wisdom | medium | 16 | 3 | 2 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 205 | 2/2 | PASS | PASS | CLEAN_PASS |
| Jeremiah 29 | unseen | Major Prophets | dense | 31 | 4 | 3 | 7 | Y | Y | 0 | 0 | 0.7083 | 1 | 0.75 | 1 | LOW | PASS_WITH_WARNING | 221 | 3/3 | PASS | PASS | RICHNESS_SHORTFALL |
| Jonah 4 | unseen | Minor Prophets | dense | 24 | 4 | 2 | 24 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 333 | 2/2 | PASS | PASS | CLEAN_PASS |
| Isaiah 63 | unseen | Major Prophets | dense | 28 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 86 | 1/1 | PASS | PASS | CLEAN_PASS |
| Revelation 9 | unseen | Apocalyptic literature | sparse | 3 | 2 | 2 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 107 | 2/2 | PASS | PASS | CLEAN_PASS |
| Revelation 8 | unseen | Apocalyptic literature | sparse | 2 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 48 | 1/1 | PASS | PASS | CLEAN_PASS |
| 1 Corinthians 14 | seen | Pauline Epistles | dense | 33 | 7 | 7 | 33 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 563 | 7/7 | PASS | PASS | CLEAN_PASS |
| Revelation 7 | unseen | Apocalyptic literature | sparse | 3 | 2 | 2 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 113 | 2/2 | PASS | PASS | CLEAN_PASS |
| Revelation 20 | seen | Apocalyptic literature | dense | 21 | 6 | 4 | 10 | Y | Y | 0 | 0 | 0.8056 | 1 | 0.8333 | 1 | NONE | PASS | 343 | 4/4 | PASS | PASS | CLEAN_PASS |
| Haggai 2 | unseen | Minor Prophets | dense | 30 | 2 | 1 | 9 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 496 | 1/1 | PASS | PASS | CLEAN_PASS |
| Psalms 22 | unseen | Poetry/Wisdom | medium | 17 | 4 | 3 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 185 | 3/3 | PASS | PASS | CLEAN_PASS |
| Numbers 1 | unseen | Torah | sparse | 5 | 3 | 1 | 4 | N | Y | 0 | 0 | — | — | — | — | — | — | 149 | 1/1 | FAIL | PASS | STRUCTURAL_FAILURE |
| Psalms 19 | unseen | Poetry/Wisdom | dense | 30 | 0 | 0 | 0 | N | Y | 0 | 0 | — | — | — | — | — | — | 0 | 0/0 | FAIL | PASS | STRUCTURAL_FAILURE |
| Revelation 15 | unseen | Apocalyptic literature | sparse | 2 | 1 | 1 | 2 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 50 | 1/1 | PASS | PASS | CLEAN_PASS |
| Numbers 31 | unseen | Torah | sparse | 1 | 1 | 1 | 1 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 37 | 1/1 | PASS | PASS | CLEAN_PASS |
| Psalms 2 | unseen | Poetry/Wisdom | dense | 26 | 1 | 1 | 1 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | LOW | PASS_WITH_WARNING | 65 | 1/1 | PASS | PASS | RICHNESS_SHORTFALL |
| Acts 27 | unseen | Acts | sparse | 5 | 2 | 2 | 5 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 183 | 2/2 | PASS | PASS | CLEAN_PASS |
| Numbers 26 | unseen | Torah | sparse | 3 | 3 | 2 | 3 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 163 | 2/2 | PASS | PASS | CLEAN_PASS |
| Exodus 14 | seen | Torah | dense | 34 | 2 | 2 | 6 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 122 | 2/2 | PASS | PASS | CLEAN_PASS |
| Hebrews 5 | unseen | General Epistles | sparse | 4 | 3 | 3 | 4 | Y | Y | 0 | 0 | 1.0000 | 1 | 1 | 1 | NONE | PASS | 174 | 3/3 | PASS | PASS | CLEAN_PASS |

## Tests

Focused command:

```bash
.venv/bin/pytest -q tests/test_bhf_commentary_projection.py tests/test_commentary_v12_reader_idea_ancestry_envelope.py tests/test_commentary_v12_reader_provenance_binding.py tests/test_commentary_v12_scale_pilot.py tests/test_commentary_v12_scale_pilot_provenance_binding.py tests/test_commentary_v12_richness.py tests/test_commentary_v12_richness_clusters.py tests/test_commentary_renderer_selection_breadth_diagnostic.py tests/test_commentary_renderer_remediation.py
```

Result: `83 passed in 213.77s`; warnings: none. Coverage includes prompt 1.7 and scoring immutability, projection and ancestry determinism, provenance-binding determinism, valid path resolution, unknown-path rejection, replacement of manual synthesis/evidence IDs, cross-synthesis leakage prevention, exact source-corpus/batch reuse, manifest/checksum reproducibility, quarantine classification, and aggregate metric correctness.

## Readiness rationale

The original systemic blocker is fixed: all 75 chapters are path-valid, ancestry-safe, and hard-provenance-safe, including the four old Batch 001 failures. No batch crossed its catastrophic threshold, no HIGH dump occurred, and non-empty prose did not show a systemic readability problem. However, structural validity, core/category population rates, and Gate PASS remain below the requested readiness bands because four separate batches emitted empty commentaries. That 5.33% recurring empty-output rate is too large to treat as an automatically quarantinable tail for production kickoff.

After the bounded output-completeness/schema-conformance remediation, rerun a population-level qualification without changing the frozen semantic or scoring contracts. Do not regenerate these pilot chapters to improve this pilot's scores and do not proceed to the remaining corpus in this task.
