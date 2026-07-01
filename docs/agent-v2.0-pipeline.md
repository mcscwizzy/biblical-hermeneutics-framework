# BHF Agent v2.0 Pipeline Context

## What PipelineContext is

`PipelineContext` is the internal state object for one BHF Agent run. It lives in
`bhf_agent.models` with the other dataclass models and carries the data produced
by each pipeline stage:

- original and normalized question text
- detected reference, genre, and question type
- selected profile name and profile content
- local curated knowledge entries
- system and user prompts
- raw model response and answer text
- cleaned answer text
- validation result
- final answer
- safe debug metadata
- warnings and errors

It is a standard-library dataclass with safe defaults for mutable fields. The
shape is intentionally serialization-friendly for future local app and debugging
boundaries.

## Why it exists

The v1 runner passed many separate values through one straight-line `ask()`
method. That worked while the pipeline was small, but v2 phases will add more
internal state: repair passes, answer modes, model capability hints, expanded
local knowledge, local chat history, mobile integration, and structured UI
rendering.

`PipelineContext` gives those future stages one clear place to read and write
run state without changing the public `AgentResult` contract for every internal
addition.

## Internal flow

`BHFAgent.ask()` still returns `AgentResult`, but internally it now runs simple
private stages:

- `initialize_context`
- `detect_reference`
- `classify_genre`
- `classify_question_type`
- `load_profile`
- `lookup_local_knowledge`
- `build_prompts`
- `call_model`
- `clean_output`
- `validate_response`
- `finalize_result`

This is not a workflow engine or plugin system. Each stage is a small private
method on `BHFAgent` that updates and returns the same context.

## Debug metadata

The context records non-secret metadata such as:

- completed stage names
- prompt strategy
- local knowledge keys
- whether cleanup was applied
- adapter type
- model name
- profile name
- validation score

The debug metadata must not include API keys, secrets, full raw provider
responses, or full prompts in normal CLI debug output.

## What did not change

This phase did not add major new features. It preserves the existing local-first
agent behavior:

- generic OpenAI-compatible adapter design
- profile loading
- profile-aware prompt strategies
- question-type-aware routing
- word-study routing
- local curated lexical lookup
- output cleanup
- validation warnings
- `BHFAgent.ask(question: str) -> AgentResult`
- CLI execution through `python -m bhf_agent`

Default CLI output remains clean and user-facing. `PipelineContext` is not
printed by default. `--show-debug` may show safe pipeline summary metadata, such
as completed stages and prompt strategy, but does not print API keys or raw
provider responses.

## Future phase preparation

`PipelineContext` prepares the agent for:

- optional repair pass
- answer modes
- model capability hints
- expanded local knowledge
- local chat history
- mobile app integration
- structured UI rendering
- better debugging

Those capabilities should be added in later phases without changing the public
CLI behavior unless a phase explicitly requires it.
