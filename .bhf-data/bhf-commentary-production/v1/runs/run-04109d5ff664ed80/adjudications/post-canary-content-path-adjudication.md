# Production canary post-adjudication

Run: `run-04109d5ff664ed80`  
Mode / renderer: `external_handoff` / `codex-gpt-5`  
Scope: existing immutable attempt-001 raw responses only. No renderer, API, or provider call was made.

## Root cause split

- **Application defect (4):** ProductionRunner stamped metadata, availability, and status, but unlike the prior import tool did not add the application-owned DATA_GAP fallback before canonical validation.
- **Renderer compliance (2):** Ruth 2 exceeded a cited medium-confidence evidence/synthesis ceiling; Hebrews 8 cited unknown `hebrew-covenant` rather than the available `heb-covenant`, outside the cited synthesis ancestry.
- **Gate quality (7):** structurally accepted work failed Gate v2.1 for inadequate weighted coverage; Romans 3 additionally omitted its CORE cluster.

## DATA_GAP re-adjudication

All four packets had `evidence_availability=DATA_GAP`, zero evidence items, zero synthesis units, and their raw payloads had exactly `sections: []`, no fallback flag, and no prose. They are all `APPLICATION_FALLBACK_STAMP_MISSING`, not renderer violations.

| Reference | Raw SHA-256 | Post-adjudication |
| --- | --- | --- |
| 2 Kings 11 | `8edc8221af75ad744b0311d152c70824234935a139e880e3008174306148a698` | COMPLETE |
| Psalms 30 | `a7b8f62146205fdda083c82a76b3cd1080a963f0ab2161b8b637cbcbd6f0d73c` | COMPLETE |
| Psalms 105 | `59592d2bd5293ee636da55b1167287713e905872be67d0fddc1d03f1bb852338` | COMPLETE |
| Ezekiel 12 | `9f130af81cf0dfd93a68a1c303b779047696e32ceff7c6dbb5fcc9cb9f8deb2a` | COMPLETE |

The shared normalizer stamps the fixed notice only where all four authoritative conditions hold: expected DATA_GAP, zero usable evidence, zero synthesis units, and raw `sections == []`. It does not repair renderer prose or nonempty authorities. The raw bytes, raw paths, hashes, and attempt number remain unchanged. Each item has a derived-validation receipt, a post-adjudication receipt, and a link to its original immutable quarantine receipt.

## Provenance findings

Ruth 2 has one offending block: `overview_1` cited `syn_cultural_context_03fbde819094` (high) and `syn_historical_context_aee44f0aa033` (medium), with evidence `ruth-gleaning-protection` (high) and `boaz:historical_context:0` (medium). The renderer marked it high; its maximum permitted confidence is medium. The packet is unambiguous.

Hebrews 8 has one offending block: `overview_1` cited `syn_interpretive_questions_d28582175e6a` and `syn_cultural_context_76146a4f85c9`. Their permitted union is `heb-covenant`, `hebrews:interpretive_note:1`, and the four `what-is-the-tabernacle:*` records. The renderer cited `hebrew-covenant`, which is neither a bundle record nor an ancestor. This is an ID hallucination/near-name confusion, not sibling-ancestry ambiguity.

## Gate omission diagnosis

All seven are AVAILABLE, have dump severity NONE except Revelation 21 (LOW), and failed weighted coverage. `represented → omitted` lists material family-level coverage.

| Chapter | units / clusters / CORE | blocks / words | weighted / CORE / utilization | Material omissions |
| --- | ---: | ---: | ---: | --- |
| Exodus 14 | 34 / 19 / 1 | 8 / 437 | .4254 / 1.00 / .2941 | Route-identification caution, geography/timeline detail, Exodus-as-redemption and wilderness-formation significance; geography, culture, and history units remained materially distinct despite all categories appearing. |
| Deuteronomy 10 | 40 / 8 / 1 | 3 / 162 | .4068 / 1.00 / .0750 | Concrete Amalek/Arabah/Gibeah setting and late-second-millennium desert-formation background. |
| Job 1 | 17 / 8 / 0 | 4 / 245 | .4583 / 1.00 / .2353 | `hasatan` as a council role rather than automatic later-proper-name identification; limits on prosperity/replacement readings; Job's righteous prologue and disputed James/endurance relation. |
| Matthew 4 | 30 / 11 / 0 | 4 / 246 | .2533 / 1.00 / .1333 | Early Roman Galilee, Herod Antipas's jurisdiction, Capernaum/fishing-economic setting, and follower/tax-collector social setting. |
| Romans 3 | 25 / 10 / 1 | 4 / 275 | .3582 / **0.00** / .2400 | The sole CORE surrounding-passage cluster; `pistis Christou`, `hilasterion`, sacrifice/crucifixion context, and Paul/James distinction. |
| Revelation 20 | 21 / 11 / 0 | 4 / 257 | .1690 / 1.00 / .1905 | Ezekielian recomposition, Israel's-scripture reuse, resurrection-development, Genesis/death, throne-judgment, and garden imagery. |
| Revelation 21 | 119 / 40 / 0 | 5 / 308 | .0882 / 1.00 / .0420 | Sanctuary referent distinctions and anti-supersession safeguard; creation/new-creation, Zion/Jerusalem/exile-restoration, temple-presence and city/geography material. |

## Metrics

| Metric | Original canary | Post-adjudication canary |
| --- | ---: | ---: |
| immutable raw responses | 25 | 25 |
| structurally accepted | 19 | 23 |
| content/structural quarantine | 6 | 2 |
| application defects corrected | 0 | 4 |
| Gate PASS / warning / QUALITY_FAIL | 12 / 0 / 7 | 16 / 0 / 7 |
| COMPLETE | 12 | 16 |
| quality quarantine | 7 | 7 |
| Dense Reader generated | 2 | 6 |

For the 19 AVAILABLE, synthesis-bearing chapters, cluster-weighted coverage is `.4024`, CORE retention `.9000` (9/10), and synthesis utilization `.2268` (83/366). DATA_GAP fallbacks are deliberately excluded from these coverage denominators.

The completed 60-chapter pilot recorded 59 valid, 50 PASS, 7 warning, 2 QUALITY_FAIL, CORE `.9915`, weighted coverage `.8249`, utilization `.8258`, and no HIGH dump. The four DATA_GAP cases are a pipeline difference. The remaining two validator failures and seven low-coverage Gate failures are renderer-controlled outcomes; canary mix does not excuse explicit confidence, ancestry, CORE, or breadth violations.

## Policy and recommendation

`GATE_QUALITY_FAIL` means **STRUCTURALLY_ACCEPTED** plus **PRODUCTION_QUARANTINED_QUALITY**; it is not a content/schema rejection. Ledger reporting now keeps that state separate from `PRODUCTION_QUARANTINED_CONTENT`.

The handoff machinery, identity binding, immutability, resume/reconciliation, and idempotency remained sound. Prompt 1.5 and every protected evidence, schema, validator, Gate, and reader contract were unchanged.

`codex-gpt-5` is not qualified for bounded production: it has two hard provenance violations and 7/19 AVAILABLE chapters failed the richness Gate, markedly below the pilot. FULL-BIBLE GENERATION WAS NOT RUN.
