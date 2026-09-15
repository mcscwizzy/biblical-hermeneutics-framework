# Commentary v1.2 architecture baseline

Starting branch: `master`

Starting HEAD: `02421e706187d73c5d87b5fbd21b488ce59cf77f`

The Commentary v1.1 orchestrator was read before this inspection. It reports
`CORPUS_COMPLETE`, 935 of 935 eligible chapters finalized, 1,189 runtime
chapters publishable, no blocker, and no resumable work.

## Current v1.1 flow

1. `bhf_agent.chapter_commentary.evidence_bundling` resolves the canonical
   chapter and retrieves passage-scoped CKL objects, archaeology summaries,
   and map summaries.
2. `bhf_agent.presentation.evidence` normalizes those inputs into an
   `EvidenceBundle`. Admission requires overlapping authored passage anchors;
   broad retrieval tags do not establish passage eligibility.
3. `bhf_agent.presentation.evidence_hash` calculates a deterministic evidence
   identity while excluding volatile retrieval scores.
4. `bhf_agent.chapter_commentary.availability` deterministically classifies the
   bundle as `AVAILABLE`, `THIN`, or `DATA_GAP` from specificity, confidence,
   dispute state, relationship, and category.
5. `bhf_agent.chapter_commentary.prompts` serializes the canonical text and raw
   evidence items directly into the v1.1 reader-commentary prompt.
6. `bhf_agent.chapter_commentary.generator` makes one prose model call, discards
   model-supplied provenance, stamps application-owned metadata, and invokes
   validation.
7. `bhf_agent.chapter_commentary.validation` validates chapter identity,
   section and block structure, evidence IDs, verse scope, confidence ceilings,
   disputed-as-fact claims, and unsupported explicit dates. Deterministic
   `INVENTED_SIGNIFICANCE` and `UNSUPPORTED_ENTITY` checks are explicitly
   deferred because the current contract has no safe structured inputs for
   them.
8. `bhf_agent.chapter_commentary.storage` atomically stores chapter JSON.
   `CommentaryBuilder` reconstructs progress from chapter files and treats
   prompt, schema, identity, or evidence-hash mismatch as stale.
9. `framework.commentary` independently protects and publishes v1.1. The
   orchestrator records SHA-256 fingerprints for certified prose; reconciliation
   overlays exactly one certified v1.1 or validated v1.0.1 source onto every
   canonical chapter; publication rejects changed fingerprints, invalid or
   duplicate identities, non-validated artifacts, missing evidence hashes, and
   incomplete canonical coverage. Publication is atomic.
10. Runtime resolves the immutable `.bhf-data/bhf-commentary-v1.1` corpus.
    Vercel excludes `.bhf-data/bhf-commentary-candidates/**`, so candidate work
    does not become a runtime dependency.

In compact form, v1.1 is:

```text
CKL / archaeology / geography
  -> EvidenceBundle + evidence_hash
  -> raw-evidence prompt + canonical text
  -> model-written reader commentary
  -> deterministic validation
  -> candidate storage
  -> certified runtime overlay
```

## v1.2 boundary

v1.2 will retain retrieval and the `EvidenceBundle` as the evidence boundary,
then insert a deterministic `CompiledChapterSynthesis` before prose generation:

```text
CKL / archaeology / geography
  -> EvidenceBundle + evidence_hash
  -> CompiledChapterSynthesis + synthesis_hash
  -> reader-facing prose generation
  -> validation against synthesis and evidence ancestry
  -> separate v1.2 candidate workspace
```

The synthesis is an organization and relationship layer, not a second evidence
store and not model-written prose. It may group compatible items and expose
supported relationships, but it cannot add facts, entities, dates, confidence,
or certainty that are absent from its evidence ancestry.

## Protected baseline

The following remain read-only during this implementation:

- `.bhf-data/bhf-commentary-v1.1/**`
- `.bhf-data/bhf-commentary-candidates/commentary-v1.0.1/**`
- `.bhf-data/bhf-commentary-candidates/commentary-v1.1*/**`
- v1.1 pipeline state, certification, audit, and fingerprint artifacts
- CKL records under `framework/canonical_library/objects/**`
- release tags and the `master` branch

All generated v1.2 synthesis, commentary, audit, canary, and backlog artifacts
belong under
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/` until an
explicit future promotion.
