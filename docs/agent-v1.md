# BHF AI Agent Core v1

The BHF AI Agent Core is a reusable Python library for asking biblical
interpretation questions through the Biblical Hermeneutics Framework method. It
is designed for local-first use and can be called by a future CLI, desktop app,
mobile app, notebook, or other local tool.

The agent teaches method. It does not force theological conclusions.

## What it is

- A library-first agent runner in `bhf_agent/`.
- A deterministic reference detector for first-pass Bible references.
- A broad book-to-genre classifier.
- A profile loader for the existing committed profiles in `profiles/`.
- A prompt builder that combines BHF method, reference context, genre context,
  and the user question.
- A lightweight response validator that checks whether the method was followed.
- A generic `ChatAdapter` interface with one v1 implementation:
  `OpenAICompatibleAdapter`.
- A thin CLI wrapper via `python -m bhf_agent`.

## What it is not

- Not a mobile app.
- Not a web server.
- Not infrastructure.
- Not a cloud service.
- Not tied to OpenAI, Anthropic, Google, Ollama, LM Studio, llama.cpp, or any
  single model provider.
- Not a theology engine or denomination-specific answer generator.
- Not a Bible text lookup engine.

No copyrighted Bible text is bundled or looked up in v1.

## Runtime model

The agent core depends only on the `ChatAdapter` interface:

```python
class ChatAdapter:
    def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError
```

The core runner does not know whether the model runtime is HTTP-based,
in-process, mobile-native, or something else. The v1 HTTP adapter exists because
many local runtimes expose an OpenAI-compatible `/v1/chat/completions` endpoint,
but the interface is intentionally broader than HTTP.

Future adapters can support:

- in-process llama.cpp bindings
- MLC LLM mobile runtimes
- native iOS or Android model bridges
- other local runtimes

## Configuration

Example `agent-config.json`:

```json
{
  "config_version": 1,
  "adapter": "openai_compatible",
  "base_url": "http://localhost:1234/v1",
  "api_key": "local",
  "model": "local-model",
  "profile": "minimal-7b",
  "temperature": 0.3,
  "max_tokens": 2048,
  "timeout_seconds": 120,
  "show_method_notes": true,
  "debug": false
}
```

Notes:

- `api_key` is optional for local runtimes.
- If `api_key` is omitted, the adapter omits the `Authorization` header.
- API keys are not printed by the config serializer.
- CLI flags can override config values.
- v1 uses only the Python standard library for the agent runtime.

## Running the CLI

From the repository root:

```bash
python -m bhf_agent --config agent-config.json "What does Proverbs 3 mean?"
```

Or without a config file:

```bash
python -m bhf_agent \
  --base-url http://localhost:1234/v1 \
  --model local-model \
  --profile minimal-7b \
  --temperature 0.3 \
  --max-tokens 2048 \
  "Explain John 3:16"
```

CLI output includes:

- answer text
- profile used
- detected reference or topic
- detected genre
- validation warnings
- debug metadata only when `--show-debug` is supplied

The CLI is intentionally thin; reusable logic stays in `BHFAgent`.

## Configuring local OpenAI-compatible runtimes

The v1 adapter posts to:

```text
{base_url}/chat/completions
```

For `base_url`:

```text
http://localhost:1234/v1
```

The final endpoint is:

```text
http://localhost:1234/v1/chat/completions
```

Request shape:

```json
{
  "model": "local-model",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.3,
  "max_tokens": 2048
}
```

### LM Studio

1. Start LM Studio's local server.
2. Load a local chat model.
3. Use the server's OpenAI-compatible base URL, commonly:

```json
{
  "base_url": "http://localhost:1234/v1",
  "api_key": "local",
  "model": "your-loaded-model-name"
}
```

The exact model name must match what LM Studio expects for the loaded model.

### llama.cpp server

1. Start `llama-server` with a local model.
2. Enable or use its OpenAI-compatible endpoint.
3. Configure BHF with that local base URL, commonly:

```json
{
  "base_url": "http://localhost:8080/v1",
  "model": "local-model"
}
```

If your server does not require authorization, omit `api_key`.

### LocalAI or similar runtimes

Use the runtime's local OpenAI-compatible base URL:

```json
{
  "base_url": "http://localhost:8080/v1",
  "model": "configured-local-model"
}
```

The adapter is generic; it does not depend on LocalAI-specific behavior.

### Ollama compatibility endpoint

If using an OpenAI-compatible Ollama endpoint, point `base_url` at the local
`/v1` base and set `model` to the local model name exposed by Ollama:

```json
{
  "base_url": "http://localhost:11434/v1",
  "model": "llama3.1"
}
```

## Python usage

```python
from bhf_agent import AgentConfig, BHFAgent

config = AgentConfig(
    adapter="openai_compatible",
    base_url="http://localhost:1234/v1",
    model="local-model",
    profile="minimal-7b",
)

agent = BHFAgent(config)
result = agent.ask("What does Proverbs 3 mean?")

print(result.answer_text)
print(result.validation_result.warnings)
```

For tests or custom runtimes, pass a custom adapter:

```python
agent = BHFAgent(config, adapter=my_adapter)
```

## Intentionally deferred from v1

- No streaming responses.
- No cancellation support.
- No mobile runtime adapters.
- No in-process model bindings.
- No local chat history.
- No retrieval over local BHF modules.
- No Bible text lookup.
- No token-budget-aware profile/module selection.
- No web server or hosted API wrapper.

## Preparing for v2

Future work should address:

- streaming responses
- cancellation support
- local mobile model runtime adapters
- in-process model adapters
- token budgeting and context-window-aware profile/module selection
- bundled resource loading for mobile packaging
- local chat history storage
- privacy audit to verify no cloud calls
- richer response validation
- optional retrieval over local BHF docs/modules
- mobile UI wrapper
- model capability detection
- battery/memory/performance considerations for phones
