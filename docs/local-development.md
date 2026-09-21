# Local Build and Development

This guide runs BHF directly from a source checkout. Use Docker instead if you
want the lexical database built automatically.

## Prerequisites

- Git.
- Python 3.9 or newer. CI and the container currently use modern Python 3.
- A browser.
- A browser. The web runtime is provider-independent; reading, local Bible
  search, maps, CKL browsing, notes, highlights, and saved work need no model
  connection.

Node.js is not part of the normal build. Browser assets and the pinned Leaflet
runtime are committed and served directly by FastAPI.

## Create the environment

```bash
git clone https://github.com/mcscwizzy/biblical-hermeneutics-framework.git
cd biblical-hermeneutics-framework
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Use `python -m pip` after activation so packages are installed into the selected
environment.

## Build the CKL database

The runtime can fall back to the JSON CKL objects, but a generated SQLite
database matches the normal application deployment:

```bash
mkdir -p .bhf
python -m framework.canonical_library build-db --output .bhf/ckl.sqlite
python -m framework.canonical_library verify-db --database .bhf/ckl.sqlite --skip-fingerprint
```

The default local configuration uses `.bhf/ckl.sqlite` and falls back to JSON if
the database is absent or stale. Docker uses a stricter image-owned database.

## Build the lexical database

The generated lexical database is intentionally not committed. Without it, BHF
still runs, but deterministic word-study definitions and original-language
verse-token selection report that lexical data is unavailable.

Follow [Compile the lexicon](compile-lexicon.md) to build:

```text
framework/lexical/database/lexicon.sqlite
```

That process downloads external source repositories, records their revisions
and licenses, builds dictionary entries, imports verse tokens, validates the
database, and runs a smoke test. The Docker image performs the same high-level
process automatically from pinned revisions.

## Ask BHF handoff

The reader's **Ask BHF** action opens a handoff composer. It uses the current
book/chapter, copies the prepared question, and opens the configured external
assistant. Set `BHF_ASSISTANT_URL` to change the destination; it defaults to
the current BHF assistant hosted in ChatGPT. See
[Ask BHF assistant handoff](assistant-handoff.md).

Maintainer-side CLI and commentary-generation workflows may still use the
provider adapters and model configuration documented in their dedicated
pipeline instructions. Those settings are not loaded by the web runtime.

## Run the web application

```bash
uvicorn bhf_web.app:app --reload --host 127.0.0.1 --port 8000
```

Open:

- Website: <http://127.0.0.1:8000>
- Health check: <http://127.0.0.1:8000/api/health>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>
- PWA manifest: <http://127.0.0.1:8000/manifest.webmanifest>

Binding to `127.0.0.1` keeps the development server local to the machine. Do
not bind the unprotected development app to a public interface.

## Run the maintainer CLI

The maintainer CLI requires a provider configuration file or equivalent
command-line overrides:

```bash
python -m bhf_agent \
  --config examples/config.ollama-v1.json \
  "What is the literary context of Romans 8:1?"
```

`config.ollama-v1.json` deliberately uses Ollama's OpenAI-compatible `/v1`
endpoint with the `openai_compatible` adapter. The native `ollama` adapter uses
the non-`/v1` base URL described above.

## Validate and test

Run the framework validator:

```bash
python tools/validate.py framework/
```

Run the Python test suite:

```bash
python -m pytest
```

Run a focused test while iterating:

```bash
python -m pytest tests/test_web_app.py
```

The GUI regression stack uses Docker and Selenium:

```bash
docker compose -f docker-compose.yml -f docker-compose.selenium.yml up \
  --build --abort-on-container-exit --exit-code-from gui-tests gui-tests
```

Clean up that stack afterward:

```bash
docker compose -f docker-compose.yml -f docker-compose.selenium.yml down -v
```

## Build the Python package

Install the build frontend and create a source distribution and wheel:

```bash
python -m pip install build
python -m build
```

Artifacts are written to `dist/`. The package contains the agent, CKL runtime,
lexical runtime code, framework data declared by `MANIFEST.in`, and bundled
agent JSON data. The FastAPI website is intended to run from the repository or
container and is not currently included in the Python package discovery list.

## Stop and clean up

Stop Uvicorn with `Ctrl-C`, then deactivate the virtual environment:

```bash
deactivate
```

The source checkout's `.bhf/` directory contains generated databases and local
study data. Delete only the exact files you intend to rebuild. Removing the
virtual environment is safe after deactivation; recreate it with the install
steps above.
