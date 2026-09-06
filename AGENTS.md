# BHF Commentary v1.1 pipeline operator instructions

When operating the Commentary v1.1 pipeline:

- Read `.bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json` first.
- Use `python -m framework.commentary.orchestrator status`, `next`, `validate`, `run`, or `resume`; do not infer the next task from conversation history.
- Run one safe stage at a time. Never weaken evidence gates or advance state before output validation.
- Respect the required model and effort in state. Luna High owns selection, evidence preflight, hardening, and audit reasoning. Terra Medium owns prose synthesis.
- Stop for genuine blockers, protected fingerprint changes, identity/hash disagreement, CKL ambiguity, or unsupported model substitution.
- Use the existing resumable checkpoints for long-running preflight work. An interrupted run is not a PASS.
- Do not modify CKL records as part of batch generation or certification.
- Do not generate a batch before its evidence is locked, and do not add evidence during prose synthesis.
- Do not rewrite previously certified canary, Batch 001, Batch 002, or Batch 003 prose.
- When a batch completes, let the orchestrator advance to the next batch. When the derived eligible corpus is complete, stop at `CORPUS_COMPLETE` after final corpus certification.

