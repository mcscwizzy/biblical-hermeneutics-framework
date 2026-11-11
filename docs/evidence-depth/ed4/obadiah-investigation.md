# Obadiah 1 coverage investigation

## Finding

The anomaly was a CKL anchor-format defect, not missing research, a chapter
enumeration problem, an object identity problem, or a passage-eligibility
failure. The canonical object is `id: obadiah`; the ASV inventory contains one
Obadiah chapter with 21 verses. Its chapter projections and the strict
retrieval path already found eligible CKL records.

One interpretive note about the verse 7 alliance language used the reference
`Obadiah 7`. The census parser correctly interpreted that as chapter 7, which
does not exist in this single-chapter book. The note's prose and rationale
identify verse 7, and the surrounding verse-specific notes use full
chapter-and-verse references. The intended and canonical reference is
`Obadiah 1:7`.

## Before correction

The committed ED-1A/ED-3 chapter census row was:

| Measure | Obadiah 1 |
|---|---:|
| Canonical chapter count | 1 |
| ASV verse count | 21 |
| Raw candidate parents | 3 |
| Eligible CKL items | 62 |
| Passage-anchored claims | 23 |
| Passage-specific interpretive notes | 36 |
| Unresolved anchor signals | 1 |
| Lookup status / coverage category | `partial` / `incomplete_or_unknown` |

The 3 parent records were `obadiah`, `malachi`, and
`judgment-against-the-nations`. The anomaly was isolated to the single
malformed reference; the chapter had substantial existing research.

## Correction and after-checks

The one reference was corrected to `Obadiah 1:7`. No claim, interpretive
content, source ID, source locator, governance status, or review decision was
changed. A regression test checks canonical bounds, and an API test verifies
that the note projects to Obadiah 1 with its original two source IDs.

The full read-only census passed at `/tmp/ed4-census` (runtime 555.2 seconds):
1,189 chapter rows, 687 CKL objects, 19 deterministic retrieval/projection
samples, and 16 live service builds. Candidate-index parity and live API
projection parity both passed; the study database marker was unchanged and
the CKL SQLite integrity check passed. The final Obadiah row is:

| Measure | Obadiah 1 after correction |
|---|---:|
| Canonical chapter count | 1 |
| ASV verse count | 21 |
| Raw candidate parents | 3 |
| Eligible CKL items | 63 |
| Passage-anchored claims | 23 |
| Passage-specific interpretive notes | 37 |
| Unresolved anchor signals | 0 |
| Lookup status / coverage category | `complete` / `passage_specific_evidence` |

The extra eligible item is the note that the malformed chapter reference had
kept out of the Obadiah 1 projection. Chapter categories now total 1,090
passage-specific, 56 contextual-only, 2 entity-only, and 41 with no eligible
CKL material; there are zero incomplete/unknown chapters. Only Obadiah 1
changed category. The validator found zero invalid or unresolved CKL anchors.

The correction preserves the distinction between the note's observation and
its scholarly framing. It resolves a technical reference defect only; it
does not imply scholarly approval of the draft note.
