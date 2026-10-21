# Local build and development

This guide runs BHF from a source checkout. Use Docker when you want the
container build to create the CKL, lexical, and Tyndale runtime databases.

## Prerequisites and setup

- Git and Python 3.9 or newer.
- A browser for the web application.
- Node.js only when running the JavaScript frontend tests.

```bash
git clone https://github.com/mcscwizzy/biblical-hermeneutics-framework.git
cd biblical-hermeneutics-framework
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Build local databases

CKL JSON is authoritative. A local SQLite database is generated from the JSON
objects and can be rebuilt at any time:

```bash
mkdir -p .bhf
python -m framework.canonical_library build-db --output .bhf/ckl.sqlite
python -m framework.canonical_library verify-db --database .bhf/ckl.sqlite
```

The reader can fall back to JSON CKL objects if SQLite is absent. The web app
reports missing Tyndale data as unavailable; to build its database, follow the
attribution, archive, and import steps in [Tyndale Open Study Notes](tyndale-study-notes.md).

The checked-in compressed lexical database supports local word study. To
rebuild it from external sources, follow [Compile the lexicon](compile-lexicon.md)
and observe the source revisions, licenses, and attribution in
[Lexicon sources](lexicon-sources.md).

## Run the application

```bash
uvicorn bhf_web.app:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Useful local endpoints include:

- <http://127.0.0.1:8000/api/health>
- <http://127.0.0.1:8000/openapi.json>
- <http://127.0.0.1:8000/api/narrative-explorer/v1/passages/Genesis/1>

Ask BHF uses `BHF_ASSISTANT_URL` to set the external assistant destination.
It hands off selected passage context and a question; the reader itself does
not need model credentials. See [assistant handoff](assistant-handoff.md).

## Development and tests

Validate the framework modules:

```bash
python tools/validate.py framework/
```

Run Python tests or a focused test file:

```bash
python -m pytest
python -m pytest tests/test_web_app.py
```

Run the frontend regression tests:

```bash
node --test tests/frontend/*.test.js
```

The GUI regression stack uses Docker and Selenium:

```bash
docker compose -f docker-compose.yml -f docker-compose.selenium.yml up \
  --build --abort-on-container-exit --exit-code-from gui-tests gui-tests
docker compose -f docker-compose.yml -f docker-compose.selenium.yml down -v
```

CKL integrity and Narrative Explorer checks are part of the active `Validate`
workflow. Do not bypass failures by weakening source, fingerprint, or registry
assertions. NE-9C and NE-10 registry files are read-only runtime inputs.

## Python package

Build a wheel and source distribution with:

```bash
python -m pip install build
python -m build
```

Artifacts go to `dist/`. The package includes the agent, web app, CKL and
lexical modules, framework package data, browser templates/static assets, and
Tyndale database data when present at build time. `.bhf-data`, local study
records, and local database files are not package inputs. The active CI workflow
checks expected and retired resources in both wheel and sdist.

For deployment behavior see [Docker](docker.md),
[Vercel routing](deployment-routing.md), and
[web and PWA use](web-pwa.md).
