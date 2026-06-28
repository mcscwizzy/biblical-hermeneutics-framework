# Docker

The Docker setup runs only the BHF web/API server. It includes the Python BHF
agent package, web UI, framework modules, profiles, and agent data files. It
does not include a local model runtime.

Use an external OpenAI-compatible endpoint such as Ollama, LM Studio, or another
server on your machine or LAN.

## Build And Run

Copy the example environment file if you want to customize defaults:

```bash
cp .env.example .env
```

Start the web app:

```bash
docker compose up --build
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

```bash
ollama pull qwen2.5:7b
ollama serve
```

Use this base URL from inside Docker:

```text
http://host.docker.internal:11434/v1
```

On Linux, `docker-compose.yml` includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

That lets the container reach services running on the Docker host.

## LM Studio On The Host

In LM Studio, start the local server with OpenAI-compatible mode enabled. The
common base URL is:

```text
http://host.docker.internal:1234/v1
```

Set it in `.env`:

```dotenv
BHF_BASE_URL=http://host.docker.internal:1234/v1
BHF_MODEL=local-model
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

