# Coverage before and after

## Before (origin/master, ED-2A merged)

The reproducible baseline is in [baseline.md](baseline.md). The chapter census reports 993 passage-specific chapters, 68 contextual-only, 3 entity-only, 124 with no eligible material, and 1 incomplete/unknown. These are reader-eligibility categories, not completeness ratings.

## After each validated wave

### Wave A, batch A1 — eight Psalms

The same ED-1A audit passed on the batch tree at fingerprint `8d313f7383484004567c768529c4e6ee13510edd4e4ae7d750a78b218abba2ad`: 1,189/1,189 chapters, no unmapped identities.

| Census category | Before | After A1 | Change |
| --- | ---: | ---: | ---: |
| Passage-specific evidence | 993 | 1,001 | +8 |
| Contextual-only coverage | 68 | 68 | 0 |
| Entity-only coverage | 3 | 3 | 0 |
| No eligible passage-specific material | 124 | 116 | −8 |
| Incomplete/unknown | 1 | 1 | 0 |

| Book | Passage-specific before | After A1 | No-eligible before | After A1 |
| --- | ---: | ---: | ---: | ---: |
| Psalms | 61 | 69 | 66 | 58 |

The eight chapter transitions are Psalm 55, 60, 66, 75, 80, 81, 97, and 100, each from no eligible passage-specific CKL item to passage-specific evidence. This records reader eligibility only. The new material consists of eight source-backed literary/textual items; it does not establish adequate coverage of those chapters or the Psalter. Sixty-six Psalm chapters still had no eligible material after this batch. See [the Wave A packets](wave-a-psalms/psalms-research-packets.md) and [the chapter backlog](research-backlog.csv).

Later batches will append their overall and by-book deltas here. No chapter will receive filler to reduce the number of zeros.

### Wave A, batch A2 — Psalms 5, 20, and 25

The corrected ED-1A census passed for all 1,189 chapters with zero unmapped identities. It found 1,004 passage-specific chapters, 68 contextual-only, 3 entity-only, 113 with no eligible material, and 1 incomplete/unknown.

| Census category | Baseline | After A2 | Change |
| --- | ---: | ---: | ---: |
| Passage-specific evidence | 993 | 1,004 | +11 |
| Contextual-only coverage | 68 | 68 | 0 |
| Entity-only coverage | 3 | 3 | 0 |
| No eligible passage-specific material | 124 | 113 | −11 |
| Incomplete/unknown | 1 | 1 | 0 |

| Book | Passage-specific baseline | After A2 | No-eligible baseline | After A2 |
| --- | ---: | ---: | ---: | ---: |
| Psalms | 61 | 72 | 66 | 55 |

The eleven changed chapters are Psalms 5, 20, 25, 55, 60, 66, 75, 80, 81, 97, and 100. A2 added three source-backed literary/textual records; it did not make all 55 remaining zero-eligible Psalms adequately researched. All coverage labels describe eligibility only. The final A2 census and source/projection details are in [the A2 packet](wave-a-psalms/psalms-research-packets-a2.md) and [the chapter backlog](research-backlog.csv).

### Wave A, batch A3 — ten additional Psalms

The corrected ED-1A audit passed all 1,189 chapter rows with zero unmapped identities. After A3, the census reports 1,014 passage-specific chapters, 68 contextual-only, 3 entity-only, 103 with no eligible material, and 1 incomplete/unknown.

| Census category | Before A3 | After A3 | Change |
| --- | ---: | ---: | ---: |
| Passage-specific evidence | 1,004 | 1,014 | +10 |
| Contextual-only coverage | 68 | 68 | 0 |
| Entity-only coverage | 3 | 3 | 0 |
| No eligible passage-specific material | 113 | 103 | −10 |
| Incomplete/unknown | 1 | 1 | 0 |

| Book | Passage-specific before A3 | After A3 | No-eligible before A3 | After A3 |
| --- | ---: | ---: | ---: | ---: |
| Psalms | 72 | 82 | 55 | 45 |
| Every other biblical book | unchanged | unchanged | unchanged | unchanged |

The ten newly eligible chapters are Psalms 7, 11, 14, 17, 21, 26, 33, 43, 49, and 83. Counts are eligibility signals, not measures of scholarly depth. The [A3 packets](wave-a-psalms/psalms-research-packets-a3.md) preserve each research question, source locator, access limit, and uncertainty. The complete audit output was written outside Git to `/tmp/ed2-master-wave-a3/`.


### Wave A, batch A4 — eight additional Psalms

The full ED-1A census passed for all 1,189 chapters with no unmapped record identities. After A4, 1,022 chapters have passage-specific evidence, 68 have contextual-only coverage, 3 have entity-only coverage, 95 have no eligible passage-specific item, and 1 is incomplete/unknown.

| Census category | Before A4 | After A4 | Change |
| --- | ---: | ---: | ---: |
| Passage-specific evidence | 1,014 | 1,022 | +8 |
| Contextual-only coverage | 68 | 68 | 0 |
| Entity-only coverage | 3 | 3 | 0 |
| No eligible passage-specific material | 103 | 95 | −8 |
| Incomplete/unknown | 1 | 1 | 0 |

| Book | Passage-specific before A4 | After A4 | No-eligible before A4 | After A4 |
| --- | ---: | ---: | ---: | ---: |
| Psalms | 82 | 90 | 45 | 37 |
| Every other biblical book | unchanged | unchanged | unchanged | unchanged |

Psalms 46, 56, 77, 91, 92, 105, 111, and 139 each moved from no eligible item to passage-specific evidence. A4 adds eight typed literary evidence records and eight source identities; all remain draft/in-review. These eligibility changes do not measure research depth. See the [A4 research packets](wave-a-psalms/psalms-research-packets-a4.md). The full audit artifacts were written outside Git to `/tmp/ed2-master-wave-a4/`.
