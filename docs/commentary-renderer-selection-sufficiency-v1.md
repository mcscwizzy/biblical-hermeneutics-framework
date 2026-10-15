# Commentary renderer selection sufficiency v1

`commentary-renderer-selection-sufficiency-v1` is a deterministic quality
assessment of validated renderer prose against its locked evidence bundle and
compiled synthesis. It runs after technical and provenance validation and
before a new artifact can be accepted or promoted.

## Decision contract

The assessment uses `RICHNESS_POLICY_VERSION_V3`, the existing V2 CORE
classifier, cluster audit V2, and the unchanged evidence applicability
policy. It does not change Gate v2.1 or its historical default scoring policy.
Only evidence marked eligible for the current chapter enters the evidence
denominator. A synthesis unit is legally renderable only when it has evidence
ancestry wholly inside that eligible set. Repeated or parallel units are
clustered before setting coverage requirements. CORE clusters must all be
represented and weighted eligible idea coverage must be at least 0.75.

A cluster is represented only when one commentary block cites a synthesis
unit in that cluster and eligible evidence from it, and the block expresses a
fact authored by the cited synthesis. The audit reports evidence categories,
synthesis kinds, idea clusters, CORE coverage, and weighted coverage as
separate measures. Citation volume alone cannot satisfy the gate.

The lexical expression check is intentionally deterministic and inspectable;
it cannot reliably recognize every valid paraphrase or establish semantic
excellence. A human should review borderline paraphrases and any selection
failure before prose is changed. Selection sufficiency does not assess
technical validity, provenance, coherence, repetition, proportionality, or
evidence dumping. Production uses Gate v2.1 as its separate presentation
assessment. The v1.2 corpus finalizer now records and requires that decision
independently. The historical 75-chapter promotion contract keeps its separate
readability, normal-reader-usefulness, and evidence-dump checks.

## Failure and unavailable states

`RENDERER_SELECTION_COLLAPSE` means the locked context contains relevant ideas
that the validated response materially omits or cites without expressing.
The receipt records the locked source identity, renderer prompt/schema,
eligibility exclusions, denominators, consumed synthesis IDs, represented and
omitted cluster IDs, weighted coverage, and exact failure reasons.

`RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE` is used when the locked bundle,
compiled synthesis, renderer versions, or source identities are absent or do
not agree. The assessor does not reconstruct missing historical input from a
current database. A new promotion of such a legacy artifact requires an
explicit human review record conforming to
`commentary-renderer-selection-legacy-exception-v1`. It must name the
reviewer, timezone-qualified review time, rationale, decision
`ACCEPT_WITH_SELECTION_ASSESSMENT_UNAVAILABLE`, and exact reference, evidence
hash, synthesis hash, raw response hash, and canonical commentary hash. The
exception is recorded in the release index and cannot waive a recorded
selection failure, failed technical/provenance checks, or a failed or missing
presentation-quality decision. The v1.2 corpus release path requires an
independent Gate v2.1 PASS or PASS_WITH_WARNING for new publication.

Existing immutable release directories retain their existing checksum and
reader compatibility. Fresh release preparation marks legacy artifacts with
missing assessment context as quality review and does not publish them until
the required source-bound human review records and independent presentation
evidence are available.
