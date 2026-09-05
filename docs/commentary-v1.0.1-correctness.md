# Commentary v1.0.1 correctness review

This is a proposed patch-release review. It does not publish or tag a release.

## Availability classifier

The former classifier treated every projected EvidenceBundle item as equal:
zero items was `DATA_GAP`, one item was `THIN`, and two or more items was
`AVAILABLE`. That made a whole-book literary statement count like a
chapter-specific historical record.

The replacement is deterministic and uses the authored evidence metadata:

| Factor | Contribution |
| --- | --- |
| verse or chapter anchor | 1.00 |
| multi-chapter range | 0.65 |
| whole-book/background range | 0.25 |
| high / medium / low confidence | 1.00 / 0.85 / 0.60 |
| undisputed / disputed | 1.00 / 0.75 |
| direct / background or comparative relationship | 1.00 / 0.85 |
| recognized contextual category / unrecognized category | 1.00 / 0.50 |

An item contributes only when its own anchor overlaps the requested passage.
`AVAILABLE` requires a score of at least 1.5 and at least two non-broad
(`chapter`, `verse`, or qualifying multi-chapter) items. Any positive but
insufficient score is `THIN`; no projected items remains `DATA_GAP`. Thus
whole-book evidence remains useful background without making a chapter
available by itself. The threshold is configurable for tests and operations,
but the default and all factor weights are fixed in code.

## 1 Samuel 28

The stored v1.0 artifact had `DATA_GAP` and zero cited evidence. The repaired
trace is:

```text
CKL object 1-samuel
  object anchor: 1 Samuel 28:1-25
  claim anchor: 1 Samuel 1-31
  interpretive-note anchor: 1 Samuel 28:3-25
        |
        +-- JSON and SQLite Scripture indexes: 1-samuel
        +-- chapter lookup: 1-samuel
        +-- valid anchored result: 1-samuel
        +-- projection: interpretive note + explicitly anchored claim
        +-- EvidenceBundle: 2 items
        +-- classifier: THIN
```

The object anchor alone is not projected because the object has structured
claims. This preserves the parent/child safeguard. The two final items are:

| Evidence ID | Category | Anchor | Confidence | Dispute |
| --- | --- | --- | --- | --- |
| `1-samuel:interpretive_note:3` | culture | 1 Samuel 28:3-25 | low | denominational disagreement |
| `first-samuel-literary-movement` | politics | 1 Samuel 1-31 | high | not disputed |

The second item is broad literary context, not chapter-specific historical
proof. The first is explicitly disputed. Their deterministic score is 0.70,
so the new result is `THIN`, not `AVAILABLE`.

The five-chapter control run returned the following final SQLite/JSON-aligned
trace. The raw candidate count includes broad and unrelated records that are
rejected by the normal Scripture scope filter:

| Passage | Raw index candidates | Valid anchored records | Rejected | Bundle items | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 Samuel 27 | 43 | 1 | 42 | 1 | THIN |
| 1 Samuel 28 | 43 | 1 | 42 | 2 | THIN |
| 1 Samuel 29 | 43 | 1 | 42 | 1 | THIN |
| 1 Samuel 30 | 43 | 1 | 42 | 1 | THIN |
| 1 Samuel 31 | 43 | 2 | 41 | 3 | AVAILABLE |

For chapter 28, JSON and SQLite both resolve the same final source object
(`1-samuel`); both indexes include the object, claim, and interpretive-note
anchor layers. The original missing item was the explicitly anchored
interpretive note, which the earlier projection/index repair now exposes. The
remaining 42 raw records disappear at normal Scripture scope matching or
projection, not through a chapter-28 special case.

The current CKL records relevant to chapter 28 are the `1-samuel` book object,
its `first-samuel-literary-movement` claim, and its Endor interpretive note.
Their source IDs are `1-samuel-1-31`, `tsumura-first-samuel`, and
`klein-first-samuel`; no new source or factual assertion was added in this
patch.

## Full-Bible classification audit

The scan covers all 1,189 chapters. Old status means the prior count-based
classifier; new status means the weighted classifier above.

| Old -> new | Count |
| --- | ---: |
| AVAILABLE -> AVAILABLE | 827 |
| AVAILABLE -> THIN | 74 |
| AVAILABLE -> DATA_GAP | 0 |
| THIN -> AVAILABLE | 0 |
| THIN -> THIN | 136 |
| THIN -> DATA_GAP | 0 |
| DATA_GAP -> AVAILABLE | 0 |
| DATA_GAP -> THIN | 0 |
| DATA_GAP -> DATA_GAP | 152 |

Totals changed from 901 AVAILABLE / 136 THIN / 152 DATA_GAP to 827 / 210 /
152. The report's raw valid-anchor coverage is unchanged at 1,057 of 1,189
chapters (88.90%); the new classifier changes semantic status, not retrieval
coverage. After projection, 1,037 chapters (87.22%) have at least one usable
EvidenceBundle item. The 20-chapter difference is exactly the object-only
manual-review set below.
The 74 downward transitions are concentrated in chapters whose evidence is
broad, multi-chapter, low-confidence, or disputed. No chapter was arbitrarily
collapsed to `DATA_GAP`.

The earlier general retrieval repair also recovered explicitly anchored notes
for 12 chapters that had previously been missed by the EvidenceBundle:
`1 Chronicles 2, 4, 5, 8, 20, 24, 25, 26, 27`; `1 Kings 20`; and `Numbers 12,
15`. Those fixes are retained on this branch and were included in the
scan.

Per-book summaries for books with data gaps are:

| Book | Available | Thin | Data gap | Projected status coverage |
| --- | ---: | ---: | ---: | ---: |
| Numbers | 20 | 11 | 5 | 86.11% |
| 1 Kings | 13 | 3 | 6 | 72.73% |
| 2 Kings | 17 | 1 | 7 | 72.00% |
| 1 Chronicles | 11 | 15 | 3 | 89.66% |
| 2 Chronicles | 12 | 10 | 14 | 61.11% |
| Psalms | 38 | 32 | 80 | 46.67% |
| Proverbs | 10 | 9 | 12 | 61.29% |
| Ecclesiastes | 10 | 1 | 1 | 91.67% |
| Ezekiel | 14 | 15 | 19 | 60.42% |
| Zechariah | 12 | 1 | 1 | 92.86% |
| Luke | 18 | 2 | 4 | 83.33% |

The other 55 books have no DATA_GAP chapters in this scan. JSON and SQLite
returned identical chapter candidate sets, and the scan found zero remaining
likely retrieval defects.

## Twenty object-only cases

Each case has an overlapping object-level Scripture reference, but no
overlapping claim, evidence-item, or interpretive-note anchor. Consequently
the production projection correctly emits no EvidenceBundle item. No parent
inheritance was restored and no data was invented.

| Classification | Chapters | Finding |
| --- | --- | --- |
| A. Projectable with code fix | none | No general projection defect found. |
| B. Legitimate structural data issue | 2 Kings 21; Ezekiel 4, 5, 12, 20, 41, 42, 44, 45, 46; Luke 9; Numbers 25; Zechariah 10 | The object has a passage anchor, but the structured claims/notes have no matching authored anchor. Existing provenance is not enough to manufacture a source-addressable item. |
| C. Bad/overbroad anchor for evidence coverage | Ezekiel 35; Psalms 31, 34, 36, 54, 68, 112 | These are cross-book reference objects. Their object-level cross-reference must not be treated as contextual evidence for the target passage without an independently anchored claim or note. |
| D. Needs human review | none | The available structure was sufficient to classify all 20 safely. |

No minimal CKL structural repairs were justified. The unresolved cases remain
data issues or overbroad relationship anchors, not hidden retrieval bugs.

## General fixes retained on this branch

The preceding retrieval repair made the smallest general changes needed for
the original failure: chapter-only range parsing was corrected; interpretive
note anchors were added to the JSON, SQLite, and generic Scripture indexes;
explicitly anchored interpretive notes were projected into EvidenceBundles;
diagnostics became backend-aware; and the DATA_GAP generation fallback became
concise and transparent. This review found no additional projection or index
defect, so no new CKL structural repair or chapter-specific code was added.

## True data-gap roadmap

The 20 object-only cases above are excluded from the true-gap count. There are
132 remaining true DATA_GAP chapters. This is a prioritization for future
source expansion only; this task adds no CKL records.

### PRIORITY 1 — high-value context expansion

These are narrative, historical, geographic, military, architectural, or
prophetic chapters where source-addressable context is likely to materially
help readers:

- Numbers 3, 5, 7, 8 — sanctuary organization, census/ritual logistics, and wilderness setting.
- 1 Kings 2, 5, 7, 10, 13, 15 — succession, temple construction, royal exchange, prophetic conflict, and regional power.
- 2 Kings 1, 6, 7, 11, 12, 13 — royal crises, siege geography, temple administration, and dynastic transitions.
- 1 Chronicles 14, 18, 19 — Davidic warfare, diplomacy, and military geography.
- 2 Chronicles 2, 4, 8, 9, 14, 16, 17, 18, 19, 21, 22, 23, 25, 27 — temple economy, international exchange, warfare, and Judean state history.
- Ezekiel 6, 7, 15, 19, 21, 22, 29, 30, 31 — prophetic geography, imperial politics, siege imagery, and Egypt/Levant history.
- Luke 5, 8, 13 — social setting, travel/location changes, healing practice, and first-century public life.

### PRIORITY 2 — useful expansion

These poetry and wisdom chapters offer meaningful linguistic, social, cultic,
royal, or genre context, but generally require more specialized source
matching than the narrative and historical cases:

- Psalms 5, 6, 7, 11, 12, 14, 15, 17, 20, 21, 25, 26, 28, 30, 33, 35, 37, 38, 39, 43, 45, 46, 47, 48, 49, 52, 53, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 75, 76, 77, 80, 81, 83, 86, 87, 91, 92, 94, 96, 97, 98, 99, 100, 101, 102, 105, 108, 109, 111, 135, 138, 139, 140, 141, 142, 143, 144, 145 — prioritize by explicit superscriptions, place names, institutions, warfare, and ancient poetic vocabulary when source provenance supports them.
- Proverbs 2, 5, 6, 12, 13, 15, 16, 18, 19, 20, 21, 28 — household, legal, economic, and linguistic context with verse-level source support.

### PRIORITY 3 — lower urgency

- Ecclesiastes 10 — wisdom/royal-administration and literary context are useful, but the chapter has lower immediate expansion urgency than the historical and prophetic gaps.

The ranking uses passage complexity and realistic source opportunities, not
theological preference.

## Patch scope and integrity

The complete v1.0.1 candidate snapshot contains 1,189 chapter artifacts. Its
correctness patch set contains 249 chapters:

- 95 commentary regenerations, because the old blocks had no citations after
  valid evidence became projectable. This includes 1 Samuel 28 and the 12
  interpretive-note recoveries.
- 63 status-only changes where existing citations and verse references remain
  valid.
- 91 legacy metadata corrections where availability was not recorded.

The other 700 chapters with a larger fresh candidate bundle have grounded
stored citations and unchanged derived status; their additional candidates are
reported as audit-only evidence deltas and do not trigger prose rewrites. Of
the 74 AVAILABLE-to-THIN transitions, 37 require the evidence-backed
regeneration above and 37 are status-only. This keeps the patch correctness-
focused rather than performing a stylistic rewrite of the corpus.

The regenerated chapters use the local Luna development harness and current
EvidenceBundles. No external provider call or new CKL source was used.

The candidate is stored separately at:

`.bhf-data/bhf-commentary-candidates/commentary-v1.0.1/1_samuel_028.json`

It uses the corrected two-item EvidenceBundle, has availability `THIN`, cites
both valid evidence IDs, preserves the disputed interpretation, and passes
chapter identity, verse scope, evidence ID, evidence hash, confidence, and
availability validation. The complete reconciliation and per-chapter delta
are stored in `reconciliation-v1.0.1.json`; the fresh release health report is
`commentary-health-report-v1.0.1.json`.

The frozen v1.0 chapter artifacts were not modified. The proposed manifest is
`.bhf-data/bhf-commentary-candidates/commentary-v1.0.1/manifest.json`.
