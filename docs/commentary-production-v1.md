# Commentary production v1

This document describes the production orchestration layer around the frozen
Commentary 1.5 contracts. It is a workflow contract, not a new commentary
schema. The production version is `commentary-production-v1`.

## Existing architecture and boundary

The repository already owns the content contracts:

1. `bhf_agent.bible` enumerates canonical ASV chapters and validates chapter
   identities.
2. `bhf_agent.chapter_commentary.evidence_bundling` retrieves the CKL,
   archaeology, map, and Scripture inputs and builds an `EvidenceBundle`.
3. `synthesis.compiler` creates the deterministic synthesis 1.1 packet and
   `synthesis.validation` validates it.
4. `prompts.build_user_prompt` and `CommentaryGenerator` implement the frozen
   Commentary Prompt 1.5 rendering contract.
5. `validation.validate_chapter_commentary` performs strict structural,
   reference, and provenance validation. Production does not salvage rejected
   sections or rewrite malformed JSON.
6. `richness`, `richness_clusters.assess_gate_v2`, and the existing scale
   evaluation tools provide the Gate v2.1 diagnostics and assessment.
7. `dense_reader` remains the deterministic, extractive Dense Reader v0.1
   presentation transform. Production stores it downstream of accepted
   Commentary and never lets reader failure invalidate Commentary.

The production layer composes those authorities. It owns run identity,
immutable manifests, attempts, artifact paths, lifecycle state, recovery,
quarantine, ledger reconstruction, sampling, and authorization. It does not
change prompt, schema, evidence, synthesis, Gate, CKL, validator, or reader
semantics.

## Flow and artifact layout

The guarded CLI is:

```text
python tools/commentary_production.py status
python tools/commentary_production.py census
python tools/commentary_production.py plan --batch-size 25 --count 25
python tools/commentary_production.py run --manifest PATH --authorized-run
python tools/commentary_production.py resume --run RUN_ID --authorized-run
python tools/commentary_production.py ledger
python tools/commentary_production.py drift
python tools/commentary_production.py audit-sample --count 25 --seed 20260908
```

Production is isolated at:

```text
.bhf-data/bhf-commentary-production/v1/
  planned/                         # plans, explicitly NOT_AUTHORIZED
  ledger.json                      # rebuildable index, never sole authority
  runs/<run-id>/
    authorization.json
    batches/<batch-id>/
      manifest.json                # immutable batch membership and inputs
      state.json                   # atomic mutable lifecycle receipt
      packets/<chapter>.json
      raw/attempt-001/<chapter>.json
      accepted/attempt-001/<chapter>.json
      rejected/attempt-001/<chapter>.json
      gate/attempt-001/<chapter>.json
      reader/attempt-001/<chapter>.json
      quarantine/attempt-001/<chapter>.json
```

Raw output is written before import, validation, Gate, or reader work. A raw
path can be reused only when its bytes have the same SHA-256; a different
payload is an immutable artifact collision. A future retry uses a new attempt
directory and identity. Production v1 defaults to one attempt and does not
enable content retries.

## Immutable identities

Every chapter row records evidence hash, synthesis hash, prompt 1.5, schema
1.2, synthesis schema/compiler 1.1, Gate v2.1, the validator source identity,
packet hash/ID, expected artifact paths, run ID, and batch ID. Run generation
configuration records provider adapter, model, effort where exposed,
temperature, output limit, runner version, and reader enablement. Secrets are
never copied into manifests.

The manifest identity hashes the canonical manifest content excluding its own
identity field. The batch manifest repeats the run manifest identity. At run
time, the current EvidenceBundle and compiler output are reloaded and compared
to the locked row. Any difference becomes `STALE_INPUT` with a drift receipt;
the old artifacts remain untouched and no silent regeneration occurs.

## State machine

The explicit chapter lifecycle is:

```text
PENDING -> READY -> GENERATING -> RAW_CAPTURED -> VALIDATING
  -> ACCEPTED -> GATE_PASS/GATE_WARNING -> COMPLETE
  -> DENSE_READER_PENDING -> DENSE_READER_COMPLETE -> COMPLETE

VALIDATING -> REJECTED -> QUARANTINED
ACCEPTED -> GATE_QUALITY_FAIL (accepted Commentary remains auditable)
PENDING/READY -> STALE_INPUT or BLOCKED
```

`COMPLETE`, `GATE_QUALITY_FAIL`, `QUARANTINED`, `STALE_INPUT`, and `BLOCKED`
are terminal for the default one-attempt policy. Invalid transitions raise an
error. Recovery reconciles written raw, accepted, Gate, and quarantine files
before continuing, so a process dying after an artifact write does not cause a
duplicate attempt.

## Failure policy

Malformed JSON, invalid references, invalid provenance, and validator rejection
are `CONTENT_FAILURE`; the raw response and validator messages are retained,
then a machine-readable quarantine receipt is written. There is no automatic
content repair.

Timeouts, 429/5xx responses, network errors, and authentication failures are
`PROVIDER_FAILURE`. Their failure envelope is stored under the attempt raw
path and their quarantine receipt carries `generation_failure: true`. They
are not counted as quality failures. Three provider failures in one batch
stop the batch as a systemic failure; a single provider failure is chapter
local and leaves the batch resumable. Evidence-store, synthesis, contract,
manifest, and unexpected harness failures stop the batch immediately.

## Dense Reader activation

Production reuses the exact v0.1 decision function. Density or length alone is
insufficient. Activation requires a dump/fragmentation signal (`dump_severity`,
low weighted coverage, or low utilization) plus at least one additional stress
signal (high block count or high word count, or another qualifying metric).
The decision is stored as `NOT_ELIGIBLE` or `ELIGIBLE`; generation is optional
and off by default. If enabled for an authorized run, a successful transform
is `GENERATED`; any transform or provenance failure is `FAILED` while the
accepted Commentary remains `COMPLETE` and valid.

Against the ten-chapter experiment, this conservative rule would activate:

* Acts 9, Genesis 15, Genesis 12, Romans 8, Hebrews 10, and Acts 1.

It would not activate Philippians 1, Hebrews 11, Acts 16, or 1 Corinthians 12.
Philippians 1 is intentionally restrained: it is long and has many blocks,
but has no dump signal, full weighted coverage, and full utilization. Acts 9
and Acts 1 demonstrate why a dense chapter with a dump signal is a different
case. These are recorded experiment observations; the experiment artifacts
are not imported into production.

## Census, ledger, and audit sampling

The census enumerates all 1,189 canonical chapters in Bible order. Historical
scale-pilot and other experiment artifacts are visible as historical flags,
but none count as production-complete. The current production status is
derived only from production batch state and artifacts. The ledger can be
rebuilt at any time from those states and records both current selection and
all observed run occurrences.

Audit sampling uses a recorded seed and SHA-256 rank. It always prioritizes
structural quarantines, Gate quality failures, warnings, THIN/DATA_GAP
chapters, and reader eligibility/failures, then fills the requested count from
the remaining chapters. It is deterministic and does not perform an audit.

## Authorization and canary procedure

`plan` is dry-run only and writes `planned/...` with
`PLANNED_NOT_AUTHORIZED`. It creates no raw model response and never calls a
renderer. `run` requires an explicit `--manifest` and `--authorized-run`; it
does not accept an unrestricted `--all`. Runs over 50 chapters are rejected
unless the manifest carries a separate full-corpus authorization, so a normal
flag typo cannot launch the corpus. Reader execution also requires the
explicit `--enable-reader` flag.

For a canary, review the planned manifest, authorize that exact manifest in a
separately approved operation, then run it with the required explicit flag.
Use `resume` for interruption. A completed batch is skipped; a new attempt is
not created implicitly. Full-corpus generation requires a separately created,
deliberately authorized manifest and should proceed batch by batch after the
canary is accepted.

This implementation task creates a planned canary only. It does not run
generation, Dense Reader on new chapters, or full-Bible processing.
