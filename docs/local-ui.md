# BHF Agent Local UI

The local UI is a small FastAPI Bible reader and study workspace that submits
questions to the existing `BHFAgent(config).ask(question)` pipeline. It is
intended for localhost use with an OpenAI-compatible local model runtime.

It has no accounts, server-side sync, or authentication. Notes and other reader
state are local-only and single-user, with optional browser-local IndexedDB
offline storage. Do not bind it to a public interface unless you add your own
access controls first.

## Install

```bash
pip install -r tools/requirements.txt
```

## Run

```bash
uvicorn bhf_web.app:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The shell serves a PWA manifest at `/manifest.webmanifest`, registers a
service worker from `/sw.js`, and provides a basic offline fallback page at
`/offline`.

The PWA exposes an offline pack manifest at `/api/offline/manifest`. On a
successful online load, the browser warms the app shell, installed translation
metadata, and installed translation datasets into IndexedDB. Once warmed, the
reader can resolve chapters and run deterministic local Bible search from the
cached dataset while offline.

Notes, highlights, and saved studies are device-only. They are written directly
to IndexedDB with client-generated IDs and are never sent to the server or
replayed through a sync queue. AI requests, LLM health checks, AI search
fallbacks, remote translation downloads, and licensed-provider content remain
outside the offline boundary.

The browser also installs the `study` and `maps` offline packs by default after
the app loads online. The `study` pack stores serialized Canonical Knowledge
Library objects so the Canonical Context browser can browse, search, and open
object details offline. The `maps` pack stores base map catalog, place,
archaeology, manuscript, route, historical-layer, and political-context
responses. The `sources` pack remains explicit because the source corpus is
large; when explicitly installed through `window.BHFPWA.installOfflinePack("sources")`,
it stores the source registry and source detail responses for offline browsing.
The reader settings sheet shows install/refresh controls and cached counts for
the study, maps, and sources packs.

Saved map studies can be created and deleted offline. They use client-generated
IDs, write to IndexedDB immediately, and replay through `/api/map-studies` when
connectivity returns. Map notes follow the same client-ID replay contract.
Saved studies are stored in IndexedDB and can be opened offline; the browser
renders a conservative HTML version of the saved answer and canonical links.

The reader settings sheet includes an Offline sync control for server-backed
map studies and map notes. Older note, highlight, and saved-study queue entries
are discarded by the updated app so they cannot be uploaded. Map changes still
retry automatically when the browser reports that it is online again.

The same sheet includes PWA lifecycle controls. Install app uses the browser's
install prompt when Chrome or another supporting browser exposes it. App update
checks the registered service worker for a newer shell. Offline storage shows
the browser's current storage estimate so large packs are visible to the user.
Offline readiness summarizes service-worker status, cached translations,
required packs, installed study data, local records, and queued sync work.
Refresh offline data re-warms the manifest, installed translation datasets,
default packs, and optional packs that are already installed. It does not clear
local records or the sync queue.
Clear offline cache removes rebuildable offline content and API cache entries
while preserving notes, highlights, saved work, and map sync mutations.
Export offline data writes a JSON snapshot of user-created offline records,
queued mutations, and pack metadata. Import offline data merges a snapshot back
into IndexedDB without clearing existing records.

Map rendering uses vendored Leaflet assets from `/static/vendor/leaflet/`
instead of a CDN. The service worker precaches the Leaflet runtime, stylesheet,
and marker/layer images so the map workspace can initialize while offline.

## Bible Reader

The first screen is a reader for the bundled American Standard Version and King
James Version datasets at `bhf_agent/data/asv_bible.json` and
`bhf_agent/data/kjv_bible.json`. Both work offline immediately with no setup.
The normalized datasets record their upstream sources in their translation
metadata.

Only ASV and KJV are served by the BHF server. A lawfully obtained XML file can
be imported in the browser for device-only offline use; the browser parses and
stores it locally. Copyrighted translations stay in the license-required section
unless imported privately on that device.

Choose a book and chapter with the reader controls. The chapter text is the
primary workspace. On desktop, Ask BHF, status, answer output, and notes appear
in the right study panel; on compact screens the app dock switches between the
reader and workspace views.

### App Dock And Compact Layout

The UI uses a shared application dock on phone, tablet, desktop, PWA, and
future wrapper layouts:

- The Bible reader stays readable with tighter spacing and larger touch targets.
- Primary navigation uses Bible, Ask, Notes, Studies, and Explore destinations.
- On phone and compact tablet widths, the dock switches between full-screen
  reader and workspace sections.
- On desktop widths, the dock activates the workspace tool while preserving the
  side-by-side reader and study workspace.
- Studies groups Highlights and Saved Studies; Explore groups Maps and 3D
  Journey.
- Verse actions have both long-press and button-based touch entry points.
- Horizontal scrolling is avoided by default on phone widths.

To test phone layouts in a browser:

1. Open the app in Chrome, Firefox, or Safari dev tools.
2. Switch to a phone viewport such as 390 x 844.
3. Verify the app dock appears.
4. Switch between Bible and Ask, then confirm the reader and study panel still
   retain their state.
5. Use the verse action button to open note/highlight actions on touch-sized
   screens.

## Ask BHF From A Passage

Select verse text in the chapter to focus the request on that verse range, then
use **Ask BHF**. If no text is selected, the form asks about the current
chapter. You can also type a specific question in the question box.

The browser sends reader fields such as book, chapter, selected verse range,
selected text, and the selected translation to the server. The server builds
the actual BHF question, including the translation reference, selected text,
full chapter context when available, and a method reminder to observe before
interpreting and apply last. The prompt wording is not owned by the UI
JavaScript.

## Live Status

When JavaScript is enabled, the form starts an in-memory ask job and polls the
FastAPI app for backend status while the agent runs. The status panel shows
real pipeline stages such as preparing the request, detecting the biblical
reference, classifying genre and question type, loading the BHF profile,
checking local knowledge, building the prompt, contacting the model backend,
waiting for the model response, cleaning, validating, finalizing, and
completion.

While a job is running, the UI shows a playful rotating waiting line instead of
a progress bar or live timer. The text changes locally while the backend is
blocked waiting for LM Studio, Ollama, or another OpenAI-compatible model
runtime, and each phrase pauses for about 3 seconds with a small random jitter.
After a successful answer render, the active status panel collapses to a compact
completion summary with the total response time. On errors, the panel stays open
with the failed step and error message.

The non-JavaScript fallback still posts to `/ask` and renders the same answer
partial after the agent finishes. Job status is local process memory only, so
active jobs and old status history reset when the FastAPI app restarts.

## Right-Click Study Menu

Right-clicking Bible text opens a compact local study menu with Study, Context,
Reference, and Study Actions submenus. If text is selected, actions use the
selected text and resolved verse range. If no text is selected, actions use the
verse that was right-clicked. Click a verse number, then Shift-click another
verse number to select a multi-verse range before highlighting, adding a note,
or asking BHF.

Available actions:

- **Full Context** asks BHF for a broad contextual reading of the selected passage.
- **Historical Context** asks BHF to explain the passage in its historical setting.
- **Cultural Context** asks BHF to explain the passage in its ancient setting,
  with OT/NT background appropriate to the book and a clear distinction between
  certain and probable background.
- **Literary Context** asks BHF to explain how the passage functions in its
  paragraph, chapter, book, genre, and argument or narrative flow.
- **Cross References** asks BHF for relevant quotations, allusions, repeated
  phrases, and canonical connections, with strong and possible links separated.
- **Related OT Themes** asks BHF for OT themes behind the passage, especially
  for NT text, with careful distinction between strong and possible thematic
  links.
- **Fulfillment in the NT** asks BHF to evaluate whether a passage is cited,
  echoed, typologically reused, or thematically developed in the NT, with
  explicit caution against forcing unsupported fulfillment readings.
- **Compare Translations** compares the installed local translations available
  for the selected passage and asks BHF to explain wording differences and
  interpretive caution.
- **Timeline** places the passage in a broad biblical-historical setting
  without pretending to know exact dates when the evidence is uncertain.
- **Maps** keeps geography text-based for now by identifying places mentioned
  in the passage and noting when a location is debated.
- **Word Study** starts a cautious ASV-English word study helper.
- **Add note to this verse / selection** opens the note editor with the
  reference prefilled.
- **Highlight this verse / selection** applies a visible highlight and persists
  it locally.

The menu stays visible while the page scrolls, and closes after choosing an
action, clicking outside, pressing Escape, or navigating away.

## Notes And Highlights

Selecting verse text enables **Add note**. Notes are stored in SQLite at
`.bhf/study.sqlite`, which is ignored by git. Each note records its id, book,
chapter, start and end verse, optional selected text, body, and timestamps.

Notes are shown for the current chapter and can be edited or deleted without
leaving the reader. There is no sync, authentication, or multi-user conflict
handling.

Highlights are also stored in `.bhf/study.sqlite`. A highlight records its id,
book, chapter, verse range, optional selected text, color, and timestamps.
Highlights reload when you return to a chapter and can be removed from the
Highlights panel.

The SQLite database is created automatically on first use. The current
implementation does not import older `.bhf/notes.json` files.

## Word Study Helper Limitations

The bundled reader uses ASV English text, not a source-language or interlinear
dataset. The **Look up Hebrew/Greek word** action sends the selected installed
translation and verse context to BHF with strict guardrails:

- The selected word is from the current reader translation text.
- The answer must not claim exact Hebrew/Greek alignment unless the app has
  source-language data.
- Possible Hebrew or Greek terms are possibilities only and should be stated
  with uncertainty.
- The answer should recommend checking an actual lexicon or interlinear.
- Semantic range, usage, and context should be explained cautiously.

Future interlinear support should add a source-language Bible dataset, lemma
alignment, Strong's or morphology data, lexicon integration, reverse
interlinear mapping, and word-level selection tied to original-language data.

## Planned Context Menu Phases

Only Ancient Context, Literary Context, Cross References, Related OT Themes,
Fulfillment in the NT, Compare Translations, Timeline, Maps, Word Study, notes,
highlights, and Save Study are active in this phase.

Save Study persists generated study results in the existing SQLite database
and adds them to the Saved Studies panel for reopening or deletion.

## Translation Manager

The translation manager is the catalog-driven dialog behind the reader version
control. It groups bundled ASV/KJV translations, device-local imports, and
license-required translations. Device-local imports never enter the server
catalog and are available only in the browser profile that imported them.

Settings are persisted locally. The default translation key is
`default_translation`, and BHF falls back to ASV if the configured translation
is missing.

See [`docs/translations.md`](translations.md) for the storage layout, install
workflow, source notices, and supported XML structure.

## Local Defaults

The UI reads optional defaults from `.bhf/web-config.json`. This path is
ignored by git, so local model names, endpoints, session paths, and secrets are
not committed.

If the file is missing or invalid, the UI uses built-in local defaults:

```json
{
  "config_version": 1,
  "adapter": "openai_compatible",
  "base_url": "http://localhost:11434/v1",
  "model": "llama3.1:8b",
  "profile": "minimal-7b",
  "answer_mode": "study",
  "temperature": 0.3,
  "max_tokens": 8192,
  "context_window": 12288,
  "timeout_seconds": 360,
  "show_method_notes": true
}
```

Runtime behavior can also be controlled with environment variables:

- `BHF_RUNTIME_MODE` sets the shell mode to `web`, `pwa`, or `capacitor`.
- `BHF_API_BASE_URL` points the browser helper at a different backend origin or
  path prefix.
- `BHF_PROVIDER_LABELS_JSON` can override provider labels for future UI
  surfaces.

If `BHF_API_BASE_URL` is unset, the browser keeps using same-origin requests.

`timeout_seconds` controls the outbound OpenAI-compatible model request timeout.
You can set it in `.bhf/web-config.json`, with `BHF_TIMEOUT_SECONDS`, or in the
form for quick local testing.

Example Ollama base URL:

```text
http://localhost:11434/v1
```

Example LM Studio base URL:

```text
http://localhost:1234/v1
```

If your local runtime requires an API key, place it only in
`.bhf/web-config.json`. The UI does not render API keys back into the page.

## Memory

If memory is enabled in the form, the agent uses the existing local session
memory support. By default, session files are written under `.bhf/sessions/`,
which is also ignored by git.

## PWA Install

### Android

Open the site in Chrome, wait for the install prompt or use the browser menu to
install the app, and confirm the app launches in standalone mode.

### iOS

Open the site in Safari, use the Share button, and choose Add to Home Screen.
iOS does not use the same install prompt as Android, so the manual share flow is
the normal path.

The reader settings sheet exposes Install app, App update, offline pack
install/refresh controls, offline storage usage, and the Offline sync queue.
AI responses still require an online or local model runtime.

## Known Limitations

- The Explore Maps view is mobile-safe, but some map workflows still depend on the
  existing desktop-oriented panels and external tile/data sources.
- The Apple native AI bridge is only a placeholder in the runtime config.
- Offline mode covers the shell, bundled/static assets, installed translations,
  local reader records, and installed study/map/source packs. Live agent
  responses and data not captured in an installed offline pack still require an
  online connection or local runtime.

## Future Path

- Keep tightening offline coverage without changing the backend contract.
- Wrap the same browser app with Capacitor once the mobile shell stabilizes.
- Add a native Apple AI bridge later, behind the runtime abstraction point.
