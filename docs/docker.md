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
docker compose up -d
```

Open:

```text
http://localhost:8080
```

The container starts:

```bash
uvicorn bhf_web.app:app --host 0.0.0.0 --port 8080
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
./.bhf:/app/.bhf
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

Do not put secrets in committed files. `.bhf/` and `.env` are ignored by git.

## Reset Sessions

Stop the container and remove local session files:

```bash
docker compose down
rm -rf .bhf/sessions
mkdir -p .bhf/sessions
```

## LAN Access

The compose file publishes the UI on the host port configured by `BHF_PORT`
and defaults to `8080`.

From another trusted device on your LAN, open:

```text
http://YOUR_HOST_LAN_IP:8080
```

This setup is intended for trusted local or LAN use only. It has no
authentication, HTTPS termination, account system, rate limiting, or public
internet hardening. Do not expose it directly to the public internet.
