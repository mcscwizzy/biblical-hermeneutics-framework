# Frontend and Backend Routing

BHF supports both a same-origin application and a split-host frontend/backend.
These are explicit deployment choices:

- `BHF_RUNTIME_MODE` controls UI behavior, installability, and native-wrapper
  behavior. It does not select the API host.
- `BHF_BACKEND_MODE` controls network topology. It accepts `same-origin` or
  `remote` and defaults to `same-origin`.
- `BHF_API_BASE_URL` identifies the backend only in `remote` mode.

## Configuration matrix

| Deployment | `BHF_RUNTIME_MODE` | `BHF_BACKEND_MODE` | `BHF_API_BASE_URL` |
|---|---|---|---|
| Vercel single service | `web` or `pwa` | `same-origin` | Unset |
| Vercel frontend + durable backend | `pwa` | `remote` | Backend public HTTPS URL |
| NAS / self-hosted PWA | `pwa` | `same-origin` | Unset |
| Local development | `web` | `same-origin` | Unset |
| Docker | `web` or `pwa` | `same-origin` | Unset |

Vercel is stateless between function invocations. In Vercel `same-origin`
mode, BHF therefore sends Ask, fallback-search, and optional AI-presentation
work through bounded synchronous HTTP requests instead of returning before a
detached thread finishes. Scripture and deterministic Companion evidence render
before the separate presentation request begins. In `remote` mode the browser
submits and polls presentation jobs on the configured durable backend. Docker,
NAS, and local persistent servers use the same job transport on their origin.

The rendered runtime exposes this decision directly as
`presentationTransport: "job" | "synchronous" | "unavailable"`. The browser
does not infer it from hosting names. A broken remote configuration fails closed
as `unavailable`; a valid remote configuration is `job` even when the frontend
runs on Vercel.

An installed PWA is not inherently a remote-backend deployment. A NAS can
serve an installable PWA and its FastAPI backend from the same origin without
Railway or internet-based API routing.

In ordinary `same-origin` mode, browser requests remain relative:

```text
POST /ask/jobs
GET  /ask/status/{id}
GET  /ask/result/{id}
GET  /api/health
POST /api/study/presentation
GET  /api/study/presentation/jobs/{id}
```

On Vercel, the equivalent same-origin Ask request is `POST /ask`; deterministic
fallback search uses `POST /api/bible/search/fallback`; AI presentation uses one
`POST /api/study/presentation` and does not poll. The repository pins the
FastAPI entrypoint in `pyproject.toml` and configures Fluid Compute plus a
60-second `maxDuration` in `vercel.json`. BHF's presentation-provider deadline
defaults to 20 seconds and is capped at 30 seconds, so BHF returns a controlled
fallback before Vercel's invocation ceiling.

Vercel documents `functions.*.maxDuration` as the supported Python/FastAPI
configuration and `fluid` as the repository-controlled Fluid Compute setting:
[function duration](https://vercel.com/docs/functions/configuring-functions/duration)
and [Fluid Compute](https://vercel.com/docs/fluid-compute). Existing projects
should redeploy this configuration and confirm the deployment's function detail
shows a 60-second maximum. No dashboard-only toggle is required by this repo.

In `remote` mode, `/ask*` and `/api*` requests are joined to
`BHF_API_BASE_URL`. Frontend resources such as `/static/*`,
`/manifest.webmanifest`, and `/sw.js` always stay on the frontend origin.
Absolute URLs are not rewritten.

Remote mode requires a valid HTTP(S) `BHF_API_BASE_URL`. If it is blank or
invalid, the runtime config contains a deterministic configuration error and
the browser refuses to submit a request. It does not fall back to the frontend
origin.

## Vercel same-origin

No routing variables are required for a single Vercel FastAPI deployment.
Optionally set `BHF_RUNTIME_MODE=pwa` to select the hosted PWA presentation.
Ask BHF uses a single request, so it does not expose the multi-request progress
history available from a durable backend. Browser-local notes, highlights,
and saved studies remain device-only; do not rely on Vercel's ephemeral
filesystem for durable server data.
Writable server defaults resolve beneath `/tmp/bhf-data` on Vercel, including
the study database, presentation cache, translations registry, and reader
settings. A cold instance reconstructs the built-in study schema and seed data
on first use. The immutable BHF Commentary v1.0 corpus is the exception: it is
read directly from the packaged repository artifact at
`.bhf-data/bhf-commentary/`, rather than copied into `/tmp`. An explicit
`BHF_COMMENTARY_STORAGE_PATH` still overrides that packaged path. `BHF_DATA_DIR`
and the individual writable `BHF_*_PATH` overrides remain available, but
Vercel local files are still transient and are not cloud persistence.

The same runtime-path split also keeps the existing translations and study/map
data flows on writable runtime paths under `/tmp` in Vercel. Legacy explicit
paths such as `BHF_CKL_DATABASE_PATH=.bhf/ckl.sqlite` remain operator overrides;
they should point to a packaged read-only artifact or a writable runtime path
as appropriate.
Deterministic Did You Know / Walk the Land / Why It Matters content renders
first. When the reader enables AI passage summaries, the browser then makes one
bounded synchronous presentation request. Provider timeout, invalid model
output, abort, or infrastructure failure leaves the deterministic cards intact.
The transient browser OpenRouter key exists only in that request and provider
call; it is not placed in SQLite or any Vercel storage service.

## Vercel + optional durable backend

Remote mode is optional. Railway is one deployment example, not a requirement
for AI passage summaries.

Set these variables for the Vercel frontend:

```dotenv
BHF_RUNTIME_MODE=pwa
BHF_BACKEND_MODE=remote
BHF_API_BASE_URL=https://<railway-public-domain>
```

`BHF_API_BASE_URL` is injected into the rendered application shell. Redeploy
Vercel after changing it. Do not include a trailing API route such as
`/ask/jobs`; supply only the backend base URL (and an intentional application
base path, if the backend is mounted beneath one).

Set this on the Railway backend:

```dotenv
BHF_CORS_ORIGINS=https://biblical-hermeneutics-framework.vercel.app
```

`BHF_CORS_ORIGINS` accepts comma-separated exact HTTP(S) origins. Wildcards and
origins containing paths are rejected. The middleware permits the methods used
by BHF and the `Accept`, `Content-Type`, `X-BHF-OpenRouter-Key`,
`X-BHF-Refresh`, and `X-BHF-Offline-Pack` request headers. Same-origin
deployments do not need to enable CORS.

For the single-instance Railway beta, also mount a persistent writable volume
and set `BHF_DATA_DIR=/data` as described in [Docker installation and
operations](docker.md#railway-public-beta). This routing change does not alter
the SQLite job store or add a shared database.

The public beta keeps BYO OpenRouter behavior: the browser sends the user's key
in `X-BHF-OpenRouter-Key`; the backend uses it transiently and does not persist
it. Do not configure a shared production OpenRouter key merely to enable this
routing topology.

## NAS, Docker, and local configuration

NAS or self-hosted PWA:

```dotenv
BHF_RUNTIME_MODE=pwa
BHF_BACKEND_MODE=same-origin
# BHF_API_BASE_URL is unset
```

Local and Docker deployments may omit all three routing variables and receive
the `web` plus `same-origin` defaults. Docker Compose exposes the variables for
operators who intentionally choose PWA presentation, but keeps same-origin
routing by default. `BHF_CORS_ORIGINS` should remain unset unless a trusted
frontend on another origin must call the backend.

## Production verification

After deploying both services:

1. Open the Vercel production site and force a normal refresh so the latest
   service worker and shell are active.
2. In DevTools Console, evaluate `window.BHFRuntimeConfig`. Confirm the relevant
   values are `mode: "pwa"`, `backendMode: "remote"`,
   `presentationTransport: "job"`, and
   `apiBaseUrl: "https://<railway-public-domain>"`.
3. Evaluate `window.BHFRuntimeConfig.apiBaseUrl` separately and confirm it is
   the Railway URL.
4. Open DevTools Network, submit a question, and confirm this sequence:

   ```text
   POST https://<railway>/ask/jobs
   GET  https://<railway>/ask/status/{id}
   GET  https://<railway>/ask/result/{id}
   POST https://<railway>/api/study/presentation
   GET  https://<railway>/api/study/presentation/jobs/{id}
   ```

5. Confirm no `/ask/*` request goes to
   `https://biblical-hermeneutics-framework.vercel.app` and that the preflight
   response allows the Vercel origin and `X-BHF-OpenRouter-Key`.
6. Stop or redeploy the Railway service during a disposable test job. A missing
   job must stop polling and ask the user to submit again; it must not leave the
   spinner running.
7. On a NAS/self-hosted PWA configured for `same-origin`, repeat the submission
   and confirm the Network panel shows relative `/ask/jobs`, `/ask/status/{id}`,
   and `/ask/result/{id}` requests against the NAS origin. Confirm presentation
   uses `POST /api/study/presentation` followed by
   `GET /api/study/presentation/jobs/{id}`.
8. On a same-origin Vercel deployment, confirm
   `presentationTransport: "synchronous"` and one presentation `POST` with no
   presentation-job polling.

Async job and fallback-search endpoints are always live-network requests in the
service worker. They are not served from an offline cache. The application
shell remains network-first and the service worker version changes with this
routing release, so an online refresh receives newly deployed routing config
while existing Bible/offline packs remain available.
