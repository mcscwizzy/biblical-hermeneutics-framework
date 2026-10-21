# Biblical Hermeneutics Framework (BHF)

> Read Scripture. Explore context. Ask deeper questions.

BHF is an open-source Bible study workspace grounded in a documented
hermeneutical method. Narrative Explorer is its primary evidence-exploration
experience. It connects a selected passage to reviewed Canonical Knowledge
Library (CKL) evidence, including evidence relationships and passage bridges,
while keeping source identity, uncertainty, and provenance visible.

CKL is the authoritative research source. NE-9C relationship curations and
NE-10 passage bridge records are read-only, provenance-bearing inputs to the
explorer. BHF also provides Bible translations, maps, archaeology, original
language tools, Tyndale Open Study Notes, offline study, and private notes and
highlights. Ask BHF prepares a conversational handoff to the external BHF
assistant; the local reader does not require an AI provider.

Generated BHF Commentary was retired in NE7R3. Its old generated reader URLs
remain stable HTTP 410 responses. Tyndale Open Study Notes is a separate active
service and remains available in the reader.

## Install with Docker

Docker builds the CKL, lexical, and Tyndale databases from checked-in source or
checksum-pinned inputs. The first build downloads lexical sources and takes
longer; later builds can reuse Docker's cache.

```bash
git clone https://github.com/mcscwizzy/biblical-hermeneutics-framework.git
cd biblical-hermeneutics-framework
cp .env.example .env
docker compose up -d --build
```

Open <http://localhost:8080> and check <http://localhost:8080/api/health>.
See [Docker installation and operations](docs/docker.md) for configuration,
persistent data, updates, and uninstallation.

## Run from source

```bash
git clone https://github.com/mcscwizzy/biblical-hermeneutics-framework.git
cd biblical-hermeneutics-framework
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
python -m framework.canonical_library build-db --output .bhf/ckl.sqlite
uvicorn bhf_web.app:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. See [local development](docs/local-development.md)
for database preparation, tests, packaging, and maintainer tools.

## Explore and study

- Read ASV or KJV Scripture, compare translations, and import supported
  device-local translations.
- Open Narrative Explorer from a passage to follow curated relationships and
  passage-scoped evidence. The read-only route is
  `GET /api/narrative-explorer/v1/passages/{book}/{chapter}` with optional
  `verse_start` and `verse_end` query parameters.
- Browse biblical places, journeys, historical layers, manuscripts, maps, and
  archaeology records.
- Use Greek and Hebrew word study when lexical assets are available.
- Read attributed Tyndale Open Study Notes in its separate companion pane.
- Keep notes, highlights, saved studies, and map studies locally; install the
  PWA for supported offline reading and study.
- Use **Ask BHF** to copy passage context and a question into the configured
  external assistant.

BHF teaches users to observe the text, interpret it in literary and historical
context, distinguish evidence from inference, qualify uncertainty, and apply
last. It does not prescribe a denomination or doctrinal conclusion.

## Repository map

| Path | Purpose |
|---|---|
| `bhf_agent/` | Agent CLI, retrieval, prompt construction, and validation. |
| `bhf_web/` | FastAPI app, APIs, reader UI, service worker, and offline support. |
| `framework/canonical_library/` | CKL objects, source records, schema, curations, and runtime. |
| `framework/lexical/` | Lexical sources, build tools, and runtime data interfaces. |
| `framework/commentary/` | Active Tyndale Open Study Notes service and importer. |
| `profiles/` | Copy-and-paste hermeneutics framework profiles. |
| `docs/` | User, development, architecture, and research-method documentation. |
| `tools/` | CKL, translation, archaeology, validation, and evaluation utilities. |
| `tests/` | Python, API, frontend, packaging, and integrity regression coverage. |

Start with the [documentation index](docs/README.md). Read
[CONTRIBUTING.md](CONTRIBUTING.md), the [Neutrality Charter](GOVERNANCE.md#1-neutrality-charter-the-constitution),
and the [style guide](docs/style-guide.md) before changing framework content.

## License

- Code is licensed under [MIT](LICENSE).
- Framework content, documentation, profiles, and examples are licensed under
  [CC BY 4.0](LICENSE-CONTENT).
- Imported translation and lexical sources retain their own notices, licenses,
  and attribution. See [Translations](docs/translations.md) and
  [Lexicon sources](docs/lexicon-sources.md).
