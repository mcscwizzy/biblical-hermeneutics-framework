# Commentary v1.1 pipeline orchestrator

The repository is the source of truth for Commentary v1.1 batch progress. The
orchestrator is available with:

```bash
python -m framework.commentary.orchestrator status
python -m framework.commentary.orchestrator report
python -m framework.commentary.orchestrator validate
python -m framework.commentary.orchestrator next
python -m framework.commentary.orchestrator run --model luna --effort high
python -m framework.commentary.orchestrator resume
python -m framework.commentary.orchestrator remediate --model terra --effort medium
python -m framework.commentary.orchestrator reconcile-recovery-blocker
```

State is stored at
`.bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json`.
It has a schema version and a SHA-256 content hash. Writes use a temporary
sibling followed by an atomic replace. A malformed or hash-mismatched state
file is blocked; it is never silently rebuilt.

## Stage progression

The only legal progression is:

`BATCH_PENDING` → `CANDIDATE_SELECTION` → `EVIDENCE_PREFLIGHT` →
`EVIDENCE_CERTIFICATION` → `EVIDENCE_LOCKED` → `READY_FOR_GENERATION` →
`PROSE_GENERATION` → `POST_GENERATION_AUDIT` → `PROSE_CERTIFICATION` →
`BATCH_COMPLETE`.

Each invocation performs or records at most one stage transition. A stage is
recorded as `RUNNING`, `OUTPUT_WRITTEN`, `OUTPUT_VALIDATED`, and only then
`COMPLETE`. The transition is not advanced merely because a child command
exited successfully.

The existing `tools/commentary_v11_scaled_preflight.py` remains the evidence
implementation. Its hidden `.batch-NNN.work` directory and atomic promotion
are reused by the orchestrator for candidate selection and evidence
preflight. Incomplete work is never written under final batch artifact names.

## Model handoffs

Luna High is required for selection, preflight, evidence certification, and
evidence-lock reasoning. Terra Medium is required for prose synthesis. The
orchestrator does not substitute a model. At a Terra stage it emits structured
`MODEL_HANDOFF_REQUIRED` output. Accept the handoff with:

```bash
python -m framework.commentary.orchestrator handoff --model terra --effort medium
```

That command records the handoff only; it does not invoke Terra. After an
external Terra run has written all expected chapter outputs, `resume` validates
coverage and evidence provenance before allowing post-generation certification.

## Blockers and recovery

Integrity failures, protected fingerprint changes, missing locked evidence,
identity disagreement, and unsupported stage transitions are first-class
`BLOCKED` conditions. A blocker records the batch, stage, error class, reason,
affected material, diagnostics, and retry policy. Clear a reviewed blocker
explicitly:

```bash
python -m framework.commentary.orchestrator clear-blocker --resolution "reviewed and repaired"
```

Clearing a blocker never retries a stage implicitly. Run `validate` first, then
`next`, `run`, or `resume` as appropriate.

Historical quarantine recovery is stored at
`.bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/quarantine-recovery-ledger.json`.
The ledger is rebuilt from the reviewed adjudication artifacts with:

```bash
python -m tools.commentary_v11_quarantine_recovery ledger \
  --scale-root .bhf-data/bhf-commentary-candidates/commentary-v1.1-scale \
  --output .bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/quarantine-recovery-ledger.json
```

Its source hashes and chapter identities are validated before selection. A
`RECOVERABLE` chapter re-enters ordinary candidate selection only while it is
unconsumed; locked chapters remain excluded, and unresolved dispositions stay
blocked. Recovery never bypasses current evidence preflight, routing, hashes,
provenance, or Terra suppression controls. The Batch 008 empty-pool blocker
has a derived reconciliation command; it clears only when the blocker’s
affected set exactly matches the ledger’s pending recoverable set:

```bash
python -m framework.commentary.orchestrator reconcile-recovery-blocker
```

### Bounded prose remediation

The only automatic prose retry currently allowlisted is `READER_UNFRIENDLY`.
It is eligible only when the evidence lock, provenance, hashes, routing, and
semantic checks are clean. The retry is limited to one attempt per chapter and
uses the same locked evidence with Terra Medium:

```bash
python -m framework.commentary.orchestrator remediate --model terra --effort medium
python -m framework.commentary.orchestrator resume
```

Integrity findings, unsupported claims, routing errors, hash disagreements,
and semantic leakage remain human-review blockers. The first failed report is
preserved as `post-generation-initial-report.json`; original chapter JSON is
preserved under `terra/remediation-attempts/attempt-001/original/` and the
machine-readable attempt record is `remediation-report.json`. A failed retry
cannot loop or reset its attempt counter.

## Batch and corpus advancement

When prose certification reaches `GO`, the next invocation records
`BATCH_COMPLETE`. The following advancement either creates the next numbered
batch work directory or writes `final-corpus-certification.json` and marks the
state `CORPUS_COMPLETE`. The eligible total is derived from the latest
population manifest; it is not a hardcoded corpus size. Protected prose
fingerprints are collected from certified historical roots and are carried
forward automatically.

The orchestrator never changes CKL records, never rewrites prior certified
prose, and never puts quarantined or `DATA_GAP` chapters in Terra input.
