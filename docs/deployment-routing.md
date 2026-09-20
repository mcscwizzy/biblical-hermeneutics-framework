# Frontend and backend routing

BHF supports same-origin and split-host deployments for its deterministic web
application. These settings control where study-data requests go; they do not
configure or select a conversational model.

- `BHF_RUNTIME_MODE` controls UI behavior and installability.
- `BHF_BACKEND_MODE` accepts `same-origin` or `remote` and defaults to
  `same-origin`.
- `BHF_API_BASE_URL` identifies the deterministic backend only in `remote`
  mode.
- `BHF_ASSISTANT_URL` identifies the external destination opened by Ask BHF.

## Configuration matrix

| Deployment | `BHF_RUNTIME_MODE` | `BHF_BACKEND_MODE` | `BHF_API_BASE_URL` |
|---|---|---|---|
| Vercel single service | `web` or `pwa` | `same-origin` | Unset |
| Vercel frontend + durable backend | `pwa` | `remote` | Backend public HTTPS URL |
| NAS / self-hosted PWA | `pwa` | `same-origin` | Unset |
| Local development | `web` | `same-origin` | Unset |
| Docker | `web` or `pwa` | `same-origin` | Unset |

In same-origin mode, reader requests remain relative, for example:

```text
GET /api/health
GET /api/bible/{book}/{chapter}
GET /api/study/companion-context
POST /api/study/actions
```

Remote mode joins deterministic `/api/*` requests to `BHF_API_BASE_URL`.
Frontend resources such as `/static/*`, `/manifest.webmanifest`, and `/sw.js`
remain on the frontend origin. Absolute URLs are never rewritten. A missing or
invalid remote backend URL fails closed with a configuration error.

Ask BHF is intentionally outside this backend routing boundary. Its generic
destination is injected as `assistantUrl` and defaults to the current BHF
assistant hosted in ChatGPT. The browser opens that HTTPS URL directly from the
user's handoff click; BHF does not proxy, embed, scrape, or submit to it.

## Vercel, NAS, and Docker

No special model or provider variables are required. A split-host deployment
may use:

```dotenv
BHF_RUNTIME_MODE=pwa
BHF_BACKEND_MODE=remote
BHF_API_BASE_URL=https://<deterministic-backend-domain>
BHF_ASSISTANT_URL=https://<supported-bhf-assistant-destination>
```

Set `BHF_CORS_ORIGINS` on the backend only when a trusted frontend on another
origin must call deterministic `/api/*` routes. Same-origin deployments do not
need CORS. The assistant URL is not a secret and is safe to expose in the
rendered runtime configuration.

## Production verification

After deployment:

1. Confirm `window.BHFRuntimeConfig.backendMode` and `apiBaseUrl` match the
   chosen deterministic topology.
2. Browse Scripture and study evidence while watching Network; no provider,
   `/ask`, completion, or presentation-inference request should occur.
3. Open **Ask BHF** and confirm that the modal opens without a network request.
4. Click the handoff action and confirm the configured assistant destination
   opens in a new tab. Clipboard failure must leave the prepared text visible.
5. Disconnect the network and confirm reader, Commentary, CKL/evidence,
   lexicon, notes, highlights, and installed offline packs continue to work.

See [Ask BHF assistant handoff](assistant-handoff.md) for the user-facing
clipboard and popup behavior.
