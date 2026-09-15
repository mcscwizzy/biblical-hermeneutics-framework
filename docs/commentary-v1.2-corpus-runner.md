# Commentary v1.2 corpus runner

The bounded runner discovers canonical Scripture in BHF order, treats the
packaged v1.2 release and its own immutable result receipts as terminal state,
and selects at most 100 chapters by default (100 maximum). This remains a
bounded corpus unit. The default workflow
freezes each selected chapter for direct rendering in the current Codex
session, then finalizes the preserved responses without a provider call.

The persisted v1.2 candidate state contains the explicit
`full_bible_generation_authorized` guard. Dry runs are allowed regardless of
the guard; generation fails closed while it is false.

```bash
.venv/bin/python tools/commentary_v12_corpus.py dry-run --batch-size 100
.venv/bin/python tools/commentary_v12_corpus.py prepare --batch-size 100
# Either render each frozen chapter packet in the current Codex session, or use
# the host-local transport below.
.venv/bin/python tools/commentary_v12_corpus.py finalize
```

`prepare` creates an immutable, content-addressed session manifest and one
renderer-input directory per renderable selected chapter. It performs no model
calls and records `awaiting_render` until the current Codex session writes
exactly one `raw-response.bin` for each renderable chapter. Before projection,
ancestry, provenance, or prompt construction, it applies the existing
evidence-applicability rules to the compiled synthesis. A chapter with zero
current-chapter-eligible evidence and zero synthesis units becomes a terminal
`NOT_RENDERABLE_SOURCE_LIMITED` receipt containing its source packet, evidence,
and synthesis identities; it receives no renderer input or raw response. An
empty synthesis with eligible evidence fails closed as a compiler regression.
`finalize` requires responses only for renderable chapters, preserves malformed
bytes, verifies the frozen source and prompt identities, then runs
normalization, structural, ancestry, provenance, richness, and quality checks
without invoking a model. Session metadata is truthfully recorded as
`renderer_mode: codex_session`, requested model `gpt-5.6-terra`, and requested
effort `high`.

The legacy nested Codex CLI transport remains available only through the
explicit `generate` command for environments that permit it; it is not the
default session workflow.

## Host-local Codex rendering

`render-local` is the scalable transport for an already-prepared session. Run
it from a normal host terminal, where the user's locally authenticated Codex
CLI is available—not from inside a Codex-agent sandbox. It performs no
discovery and never creates or re-prepares a batch.

```bash
.venv/bin/python tools/commentary_v12_corpus.py render-local \
  --run session-batch-f4179fd9eef5a7bd \
  --finalize
```

The command resolves `/home/johnwalker/.local/bin/codex` first, then `codex`
on `PATH`. It uses isolated `codex exec` exchanges with model
`gpt-5.6-terra` and `model_reasoning_effort="high"`; it does not require an
`OPENAI_API_KEY` or any OpenAI-compatible, OpenRouter, Ollama, or LM Studio
provider configuration.

Each `awaiting_render` chapter is independently rendered from its immutable
input only, atomically written as `raw-response.bin`, given an immutable
host-local renderer receipt, and checkpointed immediately. Source-limited
chapters are ignored. On resume, a response is skipped only when its receipt,
run, chapter identity, renderer contract, and SHA-256 all agree. Any conflict
fails closed. A transport failure leaves previous response files intact and
records its stdout/stderr diagnostic separately; rerunning resumes the missing
chapter. `--finalize` invokes the existing deterministic finalizer only after
every expected raw response exists, then reports the next dry run.

The batch report includes a deterministic classification such as
`V1_2_CORPUS_BATCH_01_VALIDATED` or
`V1_2_CORPUS_BATCH_01_VALIDATED_WITH_WARNINGS`; the latter records quality-audit
warnings while retaining per-chapter validation results. The session metadata
records the required Terra model and high effort without claiming that a
provider was invoked by `prepare` or `finalize`.

Each generation invocation creates an immutable manifest and per-chapter
result receipt under
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/corpus-runner/`.
The next invocation rescans those receipts and skips terminal results. Duplicate
or conflicting identities, invalid package checksums, non-terminal persisted
results, and pipeline status mismatches stop the run without guessing.

Preparation checkpoints after every chapter, so session rendering remains
resumable. Re-running a partial session
rebuilds the deterministic contract and reuses existing immutable prompt files
only when every byte matches; an immutable collision stops the run. Canary
authorization tests provide a temporary candidate-state path so testing both
authorization outcomes cannot mutate the operational candidate state.
Failure in a later chapter never justifies overwriting earlier immutable work.
