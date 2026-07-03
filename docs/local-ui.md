# BHF Agent Local UI

The local UI is a small FastAPI ASV reader and study workspace that submits
questions to the existing `BHFAgent(config).ask(question)` pipeline. It is
intended for localhost use with an OpenAI-compatible local model runtime.

It has no accounts, sync, database, or authentication. Notes are local-only and
single-user. Do not bind it to a public interface unless you add your own access
controls first.

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

## ASV Reader

The first screen is a reader for the bundled American Standard Version dataset
at `bhf_agent/data/asv_bible.json`. The ASV text is public domain in the United
States and is committed so the UI works offline immediately. The normalized
dataset records its upstream source in its translation metadata.

Choose a book and chapter with the reader controls. The chapter text is the
primary workspace. On desktop, Ask BHF, status, answer output, and notes appear
in the right study panel; on smaller screens they stack below the reader.

### Mobile Layout

The UI is now mobile-first on phone widths:

- The Bible reader stays readable with tighter spacing and larger touch targets.
- The study workspace is reachable from a bottom navigation bar with Bible,
  Ask, Notes, Studies, and Maps tabs.
- Verse actions have both long-press and button-based touch entry points.
- Horizontal scrolling is avoided by default on phone widths.

To test phone layouts in a browser:

1. Open the app in Chrome, Firefox, or Safari dev tools.
2. Switch to a phone viewport such as 390 x 844.
3. Verify the bottom nav appears.
4. Switch between Bible and Ask, then confirm the reader and study panel still
   retain their state.
5. Use the verse action button to open note/highlight actions on touch-sized
   screens.

## Ask BHF From A Passage

Select verse text in the chapter to focus the request on that verse range, then
use **Ask BHF**. If no text is selected, the form asks about the current
chapter. You can also type a specific question in the question box.

The browser sends reader fields such as book, chapter, selected verse range, and
selected text to the server. The server builds the actual BHF question,
including the ASV reference, selected text, full chapter context when available,
and a method reminder to observe before interpreting and apply last. The prompt
wording is not owned by the UI JavaScript.

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

Right-clicking Bible text opens a local study menu. If text is selected, actions
use the selected text and resolved verse range. If no text is selected, actions
use the verse that was right-clicked.

Available actions:

- **Ancient Context** asks BHF to explain the passage in its ancient setting,
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
- **Compare Translations** compares the bundled ASV and KJV texts, both
  public domain, and asks BHF to explain wording differences and interpretive
  caution.
- **Timeline** places the passage in a broad biblical-historical setting
  without pretending to know exact dates when the evidence is uncertain.
- **Maps** keeps geography text-based for now by identifying places mentioned
  in the passage and noting when a location is debated.
- **Word Study** starts a cautious ASV-English word study helper.
- **Add note to this verse / selection** opens the note editor with the
  reference prefilled.
- **Highlight this verse / selection** applies a visible highlight and persists
  it locally.

The menu closes after choosing an action, clicking outside, pressing Escape, or
navigating away.

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
dataset. The **Look up Hebrew/Greek word** action sends the English ASV
selection and verse context to BHF with strict guardrails:

- The selected word is from the ASV English text.
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
  "max_tokens": 2048,
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

The current PWA setup caches the app shell and static assets conservatively. It
does not aggressively cache API responses, so study data still comes from the
backend when the device is online.

## Known Limitations

- The Maps tab is mobile-safe, but some map workflows still depend on the
  existing desktop-oriented panels and external tile/data sources.
- The Apple native AI bridge is only a placeholder in the runtime config.
- Offline mode covers the shell and static assets, not live agent responses or
  map data that requires the backend.

## Future Path

- Keep tightening the PWA shell without changing the backend contract.
- Wrap the same browser app with Capacitor once the mobile shell stabilizes.
- Add a native Apple AI bridge later, behind the runtime abstraction point.
