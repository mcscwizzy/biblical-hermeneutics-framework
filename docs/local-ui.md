# BHF Agent Local UI

The local UI is a small FastAPI app that submits questions to the existing
`BHFAgent(config).ask(question)` pipeline. It is intended for localhost use
with an OpenAI-compatible local model runtime.

It has no accounts, sync, database, or authentication. Do not bind it to a
public interface unless you add your own access controls first.

## Install

```bash
pip install -r tools/requirements.txt
```

## Run

```bash
uvicorn bhf_web.app:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Local Defaults

The UI reads optional defaults from `.bhf/web-config.json`. This path is
ignored by git, so local model names, endpoints, session paths, and secrets are
not committed.

If the file is missing or invalid, the UI uses built-in local defaults:

```json
{
  "config_version": 1,
  "adapter": "openai_compatible",
  "base_url": "http://localhost:11434/v1",
  "model": "llama3.1:8b",
  "profile": "minimal-7b",
  "answer_mode": "study",
  "temperature": 0.3,
  "max_tokens": 2048,
  "timeout_seconds": 600,
  "show_method_notes": true
}
```

Example Ollama base URL:

```text
http://localhost:11434/v1
```

Example LM Studio base URL:

```text
http://localhost:1234/v1
```

If your local runtime requires an API key, place it only in
`.bhf/web-config.json`. The UI does not render API keys back into the page.

## Memory

If memory is enabled in the form, the agent uses the existing local session
memory support. By default, session files are written under `.bhf/sessions/`,
which is also ignored by git.
