# NE-11C1: Jonah / Matthew passage bridge

NE-11B approved one narrow, evidence-backed relationship for runtime exposure:
Jonah 1:17 and Matthew 12:40. The NE-10 registry now contains 44 active
bridges. The 43 pre-existing bridge records retain their prior payloads, and
all seven NE-10 held candidates remain excluded.

## Route contract

- ID: `jonah-1-17-matthew-12-40-sign-of-jonah`
- Category: `later_canonical_reception`
- Direction: `source_to_receiving_text`
- Evidence layer: `later_reception`
- Historical source: Jonah 1:17
- Receiving text: Matthew 12:40
- CKL support: `jonah#claim:jonah-three-days`
- Selected source IDs: `jonah-masoretic`, `jonah-new-testament`

The reader-facing explanation says Matthew 12:40 explicitly compares Jonah’s
narrated three days and nights in the fish with the Son of Man’s time in the
heart of the earth. It notes that standard Jonah 1:17 corresponds to MT/LXX
Jonah 2:1. The route preserves uncertainty about ancient time reckoning,
idiom, the expression “heart of the earth,” and the comparison’s broader
theological interpretation. The route is categorized as later canonical
reception; shared duration wording alone is not presented as a direct
quotation or as evidence that Jonah was originally predicting Jesus.

Navigation works from either endpoint. The endpoint used for navigation
changes while the historical Jonah-to-Matthew direction remains visible.

## Preservation

This addition uses the existing NE-10 schema, CKL resolver, and projection.
It does not change CKL objects, source manifests, NE-9C decisions, or the seven
held candidates. Psalm 22 / Mark 15 remains unimplemented pending the canonical
evidence refinement specified in NE-11B.

The CKL object-byte tree fingerprint remains
`e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`.

## Verification

The bridge registry resolves the exact supporting claim and selected sources.
API tests cover both endpoints, route uniqueness, source/receiver direction,
provenance, and uncertainty serialization. Frontend tests cover the displayed
relationship, uncertainty, and reversible navigation label. The original NE-10
acceptance reports remain historical snapshots of the 43-route baseline.
