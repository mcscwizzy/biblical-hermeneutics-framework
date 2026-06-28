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

## Live Status

When JavaScript is enabled, the form starts an in-memory ask job and polls the
FastAPI app for backend status while the agent runs. The status panel shows
real pipeline stages such as preparing the request, detecting the biblical
reference, classifying genre and question type, loading the BHF profile,
checking local knowledge, building the prompt, contacting the model backend,
waiting for the model response, cleaning, validating, finalizing, and
completion.

The non-JavaScript fallback still posts to `/ask` and renders the same answer
partial after the agent finishes. Job status is local process memory only, so
active jobs and old status history reset when the FastAPI app restarts.

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
  "timeout_seconds": 360,
  "show_method_notes": true
}
```

`timeout_seconds` controls the outbound OpenAI-compatible model request timeout.
You can set it in `.bhf/web-config.json`, with `BHF_TIMEOUT_SECONDS`, or in the
form for quick local testing.

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
