# BHF Agent v1.2-v1.3

This phase stabilizes the local CLI agent and adds the foundation for a small,
curated, local-first knowledge layer.

## v1.2 CLI Stabilization

The CLI remains local-first and model-agnostic. It still uses the generic
OpenAI-compatible adapter and does not add a web server, cloud dependency,
hosted API call, external Bible API, or external lexicon API.

Default CLI output shows:

- Answer text
- Profile used
- Detected question type
- Detected reference
- Detected genre
- Validation warnings, when present

Debug mode uses `--show-debug` and prints selected safe metadata only:

- Adapter type
- Base URL with credentials removed
- Model
- Profile
- Question type
- Detected reference
- Detected genre
- Validation score and warnings
- Local knowledge keys used
- Whether output cleanup was applied

Debug mode does not print API keys and does not dump raw provider responses.

## Prompt Leakage Prevention

Small local models can sometimes repeat runtime prompt sections such as:

- `BHF Agent Runtime Instructions`
- `Minimal Runtime Strategy`
- `Standard Runtime Strategy`
- `Scholar Runtime Strategy`
- `Answer Generation`

The prompt now explicitly tells the model not to repeat, quote, summarize, or
expose runtime instructions. It also tells the model to begin directly with the
required answer heading:

- `## 1. Short Answer` for word studies, historical context, and topic studies
- `## 1. Genre` for passage studies

A conservative output cleanup step runs after the model response and before
validation. It only removes obvious leading leaked runtime blocks when the
answer later contains a normal answer heading. It does not rewrite normal
user-facing method content.

## v1.3 Local Curated Knowledge Layer

The first knowledge layer is intentionally small. It exists to give local
models deterministic grounding for common word-study questions where small
models often overgeneralize.

Current local data:

- `ruach`
- `pneuma`
- `nephesh`
- `qol`

The data lives in `bhf_agent/data/lexical_terms.json`. It is a starter curated
helper, not a full lexicon.

The lookup is deterministic:

- No embeddings
- No vector database
- No external data sources
- No copyrighted Bible text
- No external lexicons

For a Hebrew spirit/wind question, the prompt receives `ruach` as the primary
entry and may receive `nephesh` and `qol` as cautionary contrast entries. This
helps the model avoid presenting `nephesh` or `qol` as primary answers for
spirit/wind.

## Validation Changes

Word-study validation now includes simple local-knowledge-aware checks:

- Warns when a Hebrew spirit/wind answer does not mention `ruach`
- Warns when `ruach` or `pneuma` is equated too directly with `Holy Spirit`
- Warns when `nephesh` or `qol` appear to be treated as primary answers for
  spirit/wind
- Rewards the existing method checks for semantic range and context dependence

This is not a full fact-checker. It is a lightweight guardrail.

## Example Configs

Example configs are available in `examples/`:

- `config.local-openai-compatible.json`
- `config.ollama-v1.json`
- `config.lm-studio.json`
- `config.llama-cpp-server.json`

They use placeholder local API keys such as `local`, `ollama`, or `lm-studio`.
Do not put real secrets in example files.

## Example Commands

```bash
python3 -m bhf_agent \
  --config examples/config.ollama-v1.json \
  "What is the Hebrew word for spirit or wind?"
```

```bash
python3 -m bhf_agent \
  --config examples/config.local-openai-compatible.json \
  --show-debug \
  "What does ruach mean?"
```

For Ollama, use the OpenAI-compatible `/v1` base URL:

```json
{
  "base_url": "http://localhost:11434/v1"
}
```

If the base URL is `http://localhost:11434` and the server returns 404, the
adapter reports a hint that OpenAI-compatible endpoints usually need `/v1`.

## Recommended Model Sizes

1B:

- Plumbing tests only
- Expect weak reasoning

3B:

- Usable for simple questions with the `minimal-7b` profile and strict routing

7B/8B:

- Recommended minimum for better BHF reasoning

14B+:

- Better fit for the `standard` profile

Large-context/frontier:

- Best fit for the `scholar` profile

## Limitations

- The knowledge layer is not a full lexicon.
- It does not include copyrighted Bible text.
- It does not call external Bible or lexicon APIs.
- It does not replace careful passage-level interpretation.
- It currently focuses on a tiny starter set for word-study stabilization.
