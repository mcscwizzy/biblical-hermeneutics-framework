# Dense Reader Synthesis v0.1 — ten-chapter experiment

Classification: **PROMISING_DENSE_READER_EXPERIMENT**

This is an isolated reader-side experiment over exactly ten accepted Commentary 1.5 artifacts. Commentary 1.5, Gate v2.1, CKL, synthesis artifacts, and baseline metrics remain unchanged.

## Chapter comparison

| Chapter | Words before → after | Reduction | Blocks → units | CORE retained | Weighted before | Idea retention | Evidence provenance | Dump before → after | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Philippians 1 | 3922 → 2295 | 41.5% | 22 → 22 | 1.0000 | 1.0000 | 1.0000 | True / 1.0000 | NONE → NONE | validated |
| Acts 9 | 2250 → 847 | 62.4% | 21 → 17 | 1.0000 | 1.0000 | 0.9412 | True / 0.9867 | MODERATE → LOW | validated |
| Hebrews 11 | 1558 → 1100 | 29.4% | 24 → 24 | 1.0000 | 0.7255 | 1.0000 | True / 1.0000 | NONE → NONE | validated |
| Genesis 15 | 1755 → 888 | 49.4% | 24 → 23 | 1.0000 | 0.7689 | 0.9571 | True / 0.9815 | LOW → LOW | validated |
| Acts 16 | 3810 → 1844 | 51.6% | 24 → 24 | 1.0000 | 0.7595 | 1.0000 | True / 1.0000 | NONE → NONE | validated |
| Genesis 12 | 2539 → 1434 | 43.5% | 24 → 24 | 1.0000 | 0.5217 | 1.0000 | True / 1.0000 | LOW → LOW | validated |
| Romans 8 | 3128 → 1498 | 52.1% | 24 → 15 | 1.0000 | 0.4731 | 1.0000 | True / 1.0000 | LOW → LOW | validated |
| Hebrews 10 | 1602 → 933 | 41.8% | 24 → 19 | 1.0000 | 0.8571 | 1.0000 | True / 1.0000 | LOW → LOW | validated |
| 1 Corinthians 12 | 2370 → 1320 | 44.3% | 22 → 22 | 1.0000 | 1.0000 | 1.0000 | True / 1.0000 | NONE → NONE | validated |
| Acts 1 | 1962 → 840 | 57.2% | 24 → 20 | 1.0000 | 1.0000 | 0.9517 | True / 0.9828 | MODERATE → LOW | validated |

## Aggregate experimental metrics

- Structurally valid: 10/10
- CORE retention minimum: 1.0000
- Provenance-valid artifacts: 10/10
- Mean / median word reduction: 47.3% / 46.9%
- Mean / median block reduction: 9.8% / 2.1%
- Reader dump distribution: {'NONE': 4, 'LOW': 6}; improved in 2/10

Weighted coverage before is the immutable Commentary 1.5 baseline. Reader idea/evidence retention is relative to the source Commentary's represented clusters and IDs; the reader layer does not claim to repair missing source coverage.

## Outliers and controls

- Romans 8 is consolidated only from its accepted source. Its low baseline weighted coverage remains low; no missing evidence is added.
- Genesis 12 is allowed to remove repeated framing and join related source material, while preserving the meaningful ideas actually represented.
- Acts 9 and Acts 1 are dump-prone tests; their reader dump severity is compared independently from the frozen Gate v2.1 result.
- Philippians 1 is a long-but-good control. Density and length alone do not activate aggressive grouping, so its successful source shape is restrained.

## Activation recommendation

activate only when density/high block shape is paired with dump severity or low weighted/utilization coverage; keep long, well-utilized, non-dump chapters restrained

This experiment is not production architecture approval; it only indicates whether the sidecar boundary and deterministic transform are worth carrying into later design.
