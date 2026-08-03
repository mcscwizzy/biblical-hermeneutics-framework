# BHF Examples

This directory contains runnable provider configurations, data-tool fixtures,
and a worked hermeneutics example. Copy an example before adding private keys or
machine-specific model names; committed examples must remain secret-free.

## Agent configurations

| File | Use |
|---|---|
| `config.ollama-v1.json` | Ollama through its OpenAI-compatible `/v1` API. |
| `config.lm-studio.json` | LM Studio's common local `/v1` endpoint. |
| `config.llama-cpp-server.json` | A llama.cpp OpenAI-compatible server. |
| `config.local-openai-compatible.json` | Generic local OpenAI-compatible template. |

Run one from the repository root after starting its model server:

```bash
python -m bhf_agent \
  --config examples/config.ollama-v1.json \
  "What is the literary context of Romans 8:1?"
```

Replace `model` with an identifier installed in the selected runtime. The
legacy profile and answer-mode fields remain in some examples for compatibility
but do not change the application's unified answer format.

## Lexicon fixtures

- `lexicon-source-manifest.example.json` documents the normalized local-source
  manifest shape used by lexical onboarding tools.
- `lexicon-coverage.example.json` and
  `lexicon-coverage.expanded.example.json` provide smoke-test coverage inputs.

The fixtures do not download sources and are not substitutes for license and
revision review. See [Lexicon sources](../docs/lexicon-sources.md) and
[Compile the lexicon](../docs/compile-lexicon.md).

## Worked interpretation example

[`romans-honor-shame-walkthrough.md`](romans-honor-shame-walkthrough.md)
demonstrates how the core method, epistle genre, and Roman social setting can be
applied without settling a doctrinal question. To reproduce it, compose the
named modules and use the result as a model system prompt. See the
[prompt-only guides](../docs/README.md#use-bhf).
