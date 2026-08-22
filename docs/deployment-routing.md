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
| Vercel frontend + Railway backend | `pwa` | `remote` | Railway public HTTPS URL |
| NAS / self-hosted PWA | `pwa` | `same-origin` | Unset |
| Local development | `web` | `same-origin` | Unset |
| Docker | `web` or `pwa` | `same-origin` | Unset |

An installed PWA is not inherently a remote-backend deployment. A NAS can
serve an installable PWA and its FastAPI backend from the same origin without
Railway or internet-based API routing.

In `same-origin` mode, browser requests remain relative:

```text
POST /ask/jobs
GET  /ask/status/{id}
GET  /ask/result/{id}
GET  /api/health
```

In `remote` mode, `/ask*` and `/api*` requests are joined to
`BHF_API_BASE_URL`. Frontend resources such as `/static/*`,
`/manifest.webmanifest`, and `/sw.js` always stay on the frontend origin.
Absolute URLs are not rewritten.

Remote mode requires a valid HTTP(S) `BHF_API_BASE_URL`. If it is blank or
invalid, the runtime config contains a deterministic configuration error and
the browser refuses to submit an async job. It does not fall back to the
frontend origin.

## Vercel + Railway public beta

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
   values are `mode: "pwa"`, `backendMode: "remote"`, and
   `apiBaseUrl: "https://<railway-public-domain>"`.
3. Evaluate `window.BHFRuntimeConfig.apiBaseUrl` separately and confirm it is
   the Railway URL.
4. Open DevTools Network, submit a question, and confirm this sequence:

   ```text
   POST https://<railway>/ask/jobs
   GET  https://<railway>/ask/status/{id}
   GET  https://<railway>/ask/result/{id}
   ```

5. Confirm no `/ask/*` request goes to
   `https://biblical-hermeneutics-framework.vercel.app` and that the preflight
   response allows the Vercel origin and `X-BHF-OpenRouter-Key`.
6. Stop or redeploy the Railway service during a disposable test job. A missing
   job must stop polling and ask the user to submit again; it must not leave the
   spinner running.
7. On a NAS/self-hosted PWA configured for `same-origin`, repeat the submission
   and confirm the Network panel shows relative `/ask/jobs`, `/ask/status/{id}`,
   and `/ask/result/{id}` requests against the NAS origin.

Async job and fallback-search endpoints are always live-network requests in the
service worker. They are not served from an offline cache. The application
shell remains network-first and the service worker version changes with this
routing release, so an online refresh receives newly deployed routing config
while existing Bible/offline packs remain available.
