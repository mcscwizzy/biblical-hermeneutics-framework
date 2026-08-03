# Docker

The default Docker setup runs the BHF web/API server configured for OpenRouter.
It includes the Python BHF agent package, web UI, framework modules, profiles,
agent data files, and persistent BHF application data. It does not start a
local model runtime.

Ollama remains available as an opt-in stack in `docker-compose.ollama.yml`.
The app can also point at an external OpenAI-compatible endpoint such as LM
Studio, llama.cpp, or another server on your machine or LAN by changing the
environment variables in `.env`.

## Build And Run

Copy the example environment file if you want to customize defaults:

```bash
cp .env.example .env
```

Start the full stack:

```bash
docker compose up -d --build
```

Open:

```text
http://localhost:8080
```

The container starts:

```bash
uvicorn bhf_web.app:app --host 0.0.0.0 --port 8080
```

## Local HTTP

The Docker stack publishes the BHF web/API server directly from the `bhf-web`
container:

```text
http://localhost:8080
```

The default host port is controlled by `BHF_HTTP_PORT` and defaults to `8080`.
The app container always listens on port `8080` inside Compose.

To verify the local endpoint:

```bash
curl http://localhost:8080/api/health
```

## OpenRouter

The default stack uses the OpenRouter-compatible endpoint:

```text
https://openrouter.ai/api/v1
```

On first launch, connect OpenRouter in the browser UI. The connection key is
kept by the browser and sent to BHF only for the current request. For a
server-side key instead, set `BHF_API_KEY` in `.env`.

## Ollama (Optional)

Start the separate Ollama stack when you want the bundled local runtime:

```bash
docker compose -f docker-compose.ollama.yml up -d --build
```

This starts the BHF web server, Ollama, and the one-time model initializer.
The default model is:

```text
qwen2.5:0.5b
```

The model is stored in the named Docker volume `ollama` and reused on
subsequent starts. Change it in `.env` with `OLLAMA_MODEL`, or pull another
model manually:

```bash
docker exec -it <ollama-container-name> ollama pull llama3.2:1b
```

To use an Ollama server running on the host rather than the bundled container,
use the default stack with these `.env` values:

```dotenv
LLM_PROVIDER=ollama
BHF_BASE_URL=http://host.docker.internal:11434
BHF_MODEL=qwen2.5:0.5b
```

The bundled app container talks to Ollama over the Compose network at:

```text
http://ollama:11434
```

The host can reach the same Ollama service at:

```bash
curl http://localhost:11434/api/tags
```

## Lexical Database

The Docker image build automatically clones pinned lexical source revisions,
builds the Greek/Hebrew dictionary database, imports OSHB Hebrew Bible verse
tokens, imports MorphGNT Greek New Testament verse tokens, validates the
result, and stores the generated SQLite file at:

```text
/app/.bhf-seed/lexicon.sqlite
```

On container start, the entrypoint copies that seeded database into the mounted
runtime path:

```text
.bhf/lexicon.sqlite -> /app/.bhf-data/lexicon.sqlite
```

By default, Compose sets `BHF_LEXICAL_SEED_POLICY=refresh`, so the image seed
replaces `.bhf/lexicon.sqlite` each time the web container starts. Set
`BHF_LEXICAL_SEED_POLICY=missing` to preserve an existing mounted lexical
database, or `BHF_LEXICAL_SEED_POLICY=none` to disable seeding entirely.

Pinned source revisions can be overridden as build args:

```bash
BHF_HEBREW_LEXICON_REVISION=<commit> \
BHF_STRONGS_REVISION=<commit> \
BHF_OSHB_REVISION=<commit> \
BHF_MORPHGNT_REVISION=<commit> \
docker compose build bhf-web
```

The default pinned revisions are listed in `.env.example` and passed through
`docker-compose.yml` as build arguments.

## LM Studio On The Host

In LM Studio, start the local server with OpenAI-compatible mode enabled. The
common base URL is:

```text
http://host.docker.internal:1234/v1
```

Set it in `.env`:

```dotenv
LLM_PROVIDER=openai_compatible
BHF_BASE_URL=http://host.docker.internal:1234/v1
BHF_MODEL=local-model
```

The default stack can also use LM Studio without changing Compose files. Set
`LLM_PROVIDER=openai_compatible`, then point `BHF_BASE_URL` at the LM Studio
server as shown above.

## Persistent Data

Compose mounts:

```text
./.bhf:/app/.bhf-data
```

Session memory is stored in:

```text
.bhf/sessions/
```

Exports, when added by future features, should use:

```text
.bhf/exports/
```

Optional web defaults can live in:

```text
.bhf/web-config.json
```

The lexical runtime database is stored in:

```text
.bhf/lexicon.sqlite
```

The generated CKL runtime database remains inside the image at:

```text
/app/.bhf/ckl.sqlite
```

Do not mount the host `.bhf/` directory over `/app/.bhf`; that hides the
generated CKL database and can make `/api/canonical/search` fail at runtime.

Do not put secrets in committed files. `.bhf/` and `.env` are ignored by git.

## Reset Sessions

Stop the container and remove local session files:

```bash
docker compose down
rm -rf .bhf/sessions
mkdir -p .bhf/sessions
```

## LAN Access

The compose file publishes local HTTP on the host port configured by
`BHF_HTTP_PORT` and defaults to `8080`.

From another trusted device on your LAN, open:

```text
http://YOUR_HOST_LAN_IP:8080
```

This plain HTTP LAN address is suitable for local BHF features, but it is not a
secure OpenRouter OAuth callback target. For OpenRouter, use a trusted HTTPS
Synology reverse-proxy address or run the browser on the BHF host with
`localhost`.

This setup is intended for trusted local or LAN use only. It has no
authentication, account system, rate limiting, or public internet hardening.
Do not expose it directly to the public internet.
