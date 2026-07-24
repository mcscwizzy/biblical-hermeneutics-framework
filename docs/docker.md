# Docker

The default Docker setup runs the BHF web/API server and a lightweight local
Ollama runtime for development and testing. It includes the Python BHF agent
package, web UI, framework modules, profiles, agent data files, and a persistent
Ollama volume for model reuse.

The app can still point at an external OpenAI-compatible endpoint such as LM
Studio, llama.cpp, or another server on your machine or LAN by changing the
environment variables in `.env`.

## Build And Run

Copy the example environment file if you want to customize defaults:

```bash
cp .env.example .env
```

Start the full stack:

```bash
./scripts/generate-local-cert.sh
docker compose up -d --build
```

Open:

```text
http://localhost:8080
https://localhost:8443
```

The container starts:

```bash
uvicorn bhf_web.app:app --host 0.0.0.0 --port 8080
```

## Local HTTPS

The Docker stack includes an Nginx reverse proxy for browser features that
require a secure context. Generate a local self-signed certificate before
building the stack:

```bash
./scripts/generate-local-cert.sh
```

Then start Compose normally. The proxy image copies the local certificate and
key into the image during build, so the running Nginx container does not need a
cert volume mount:

```bash
docker compose up -d --build
```

Open:

```text
https://localhost:8443
```

The HTTPS proxy terminates TLS and forwards requests to the app container at:

```text
http://bhf-web:8080
```

The default HTTPS host port is controlled by `BHF_HTTPS_PORT` and defaults to
`8443`. The normal HTTP endpoint at `http://localhost:8080` remains available.

Because the generated certificate is self-signed, your browser will show a
local certificate warning unless you explicitly trust `.bhf/certs/localhost.crt`
on your machine. The private key is written under `.bhf/certs/`, which is
ignored by git.

If you regenerate the certificate later, rebuild the proxy image:

```bash
docker compose build bhf-https-proxy
docker compose up -d bhf-https-proxy
```

To verify the local HTTPS endpoint without trusting the certificate:

```bash
curl -k https://localhost:8443/api/health
```

## Ollama On The Host

Run Ollama on your host machine and make sure the model is available:

The app container talks to Ollama over the Compose network at:

```text
http://ollama:11434
```

The host can reach the same Ollama service at:

```bash
curl http://localhost:11434/api/tags
```

On first start, the `ollama-init` service waits for Ollama, then pulls the
default lightweight model:

```text
qwen2.5:0.5b
```

Because the model lives in the named Docker volume `ollama`, it is reused on
subsequent starts instead of being pulled again.

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

If you want to use LM Studio instead of Ollama, set `LLM_PROVIDER` to
`openai_compatible` and point `BHF_BASE_URL` at the LM Studio server. The
Ollama services can be removed from `docker-compose.yml` or ignored if you do
not need the local containerized model runtime.

## Swap Models

Change the default local model by updating:

```dotenv
OLLAMA_MODEL=qwen2.5:0.5b
```

To pull another model manually:

```bash
docker exec -it <ollama-container-name> ollama pull llama3.2:1b
```

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

The compose file publishes the HTTP UI on the host port configured by
`BHF_PORT` and defaults to `8080`. It publishes local HTTPS on the host port
configured by `BHF_HTTPS_PORT` and defaults to `8443`.

From another trusted device on your LAN, open:

```text
http://YOUR_HOST_LAN_IP:8080
https://YOUR_HOST_LAN_IP:8443
```

This setup is intended for trusted local or LAN use only. It has no
authentication, account system, rate limiting, or public internet hardening.
Do not expose it directly to the public internet.
