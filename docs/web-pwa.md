# Using the Website and PWA

The same FastAPI application serves the hosted website, a self-hosted website,
and the installable Progressive Web App (PWA). The PWA is not a separate native
application; it is the BHF website installed with a standalone window, service
worker, browser caches, and IndexedDB storage.

## Open the website

Use the HTTPS address published by the BHF project maintainer, or open your
self-hosted address such as <http://localhost:8080>. This repository does not
currently declare or deploy a canonical production domain.

Do not treat hostnames found in tests, Git history, screenshots, or personal
reverse-proxy examples as the official public URL.

## First launch and AI setup

The setup dialog offers three choices:

1. **Connect OpenRouter** — recommended for a hosted HTTPS site or localhost.
2. **Use Local AI** — connect Ollama running on the same computer or a trusted
   network host.
3. **Use Another OpenAI-Compatible Service** — connect LM Studio, llama.cpp, or
   another compatible endpoint.

You can also continue without AI. Bible reading, deterministic local Bible
search, Maps, Explore → Archaeology, the Canonical Context browser, notes, highlights, saved studies,
and installed offline data remain useful without a model connection.

OpenRouter authorization uses a browser PKCE flow. The callback must return to
the same BHF origin and browser session:

- `http://localhost:<port>` and `http://127.0.0.1:<port>` are supported for
  local use.
- A remotely hosted BHF origin must use browser-trusted HTTPS.
- A plain `http://192.168.x.x` LAN address is not a secure OpenRouter callback.

The connected OpenRouter key is encrypted with Web Crypto and stored in that
browser profile. A non-extractable browser encryption key protects the stored
record; the decrypted value is held in memory and sent to BHF only for the
current AI request. It is excluded from application logs, saved studies,
service-worker caches, and offline exports. Clearing site data, reinstalling
the PWA, or changing devices can require reconnection.

OpenRouter and its selected upstream model have their own privacy and retention
policies. Do not submit sensitive material until you have reviewed them.

## Read and study

The main workspace contains the Bible reader and a study panel.

1. Choose a translation, book, and chapter.
2. Read the chapter or select a verse range.
3. Open **Ask BHF** and enter a question. With no selection, the current chapter
   supplies the reader context.
4. Use the answer's study controls to save work or continue exploring.

The **Explore** section is for free research: ask about any person, place,
theme, or passage, or browse the research collections. Explore questions are
not constrained by the verse or chapter currently open in the reader.

ASV and KJV are bundled. The translation manager can install approved sources
or import a lawfully obtained XML translation into the current browser for
device-only use. See [Translations](translations.md) for formats and licensing.

Selecting text or opening a verse action menu provides study actions such as:

- Full, historical, cultural, and literary context.
- Cross references and related Old Testament themes.
- New Testament fulfillment analysis.
- Translation comparison, timeline, maps, and word study.
- Notes, highlights, and saved studies.

Word study uses generated source-language dictionaries and verse-token data
when present. If deterministic lexical data is unavailable, BHF should say so
instead of substituting a confident definition from model memory.

## Navigation on desktop and mobile

The labeled application dock groups actions by purpose: **Read** (Bible),
**Study** (Ask, Notes, New note, and saved studies), **Explore** (free BHF
search, maps, archaeology, and research collections), and **App** (workspace
restore and settings).
On larger screens the reader and study workspace remain side by side. On phones
and compact tablets the dock switches between full-screen reader and workspace
views while preserving the current passage and selection.

Explore includes maps and journey views. Some map tiles or outbound reference
links can still need a network connection even when the map data pack is
installed.

## Install the PWA

PWA installation requires HTTPS, except browsers treat `localhost` and
`127.0.0.1` as secure development origins.

### Chrome or Edge on desktop

1. Open BHF and wait for the page to finish loading.
2. Use the install icon in the address bar or the browser menu's app-install
   action.
3. Confirm that BHF opens in a standalone window.

### Android

1. Open BHF in Chrome.
2. Use **Install app** in BHF settings or **Install app / Add to Home screen**
   from the browser menu.
3. Launch BHF from the new home-screen icon.

### iPhone or iPad

1. Open BHF in Safari.
2. Tap **Share**.
3. Choose **Add to Home Screen** and confirm.

iOS uses this manual share flow rather than the Chromium install prompt.

### Uninstall the PWA

Use the operating system or browser's normal app-uninstall action. Uninstalling
the icon may leave site data behind. To remove cached packs and local records,
also clear BHF's storage in the browser's site settings. Export your offline
data first if you want to preserve notes, highlights, or saved studies.

## What works offline

After one successful online load, the service worker caches the application
shell and static assets. BHF also warms installed translation data and supports
installable data packs.

| Capability | Offline behavior |
|---|---|
| App shell and bundled assets | Cached by the service worker. |
| ASV/KJV and installed translations | Readable after their data has been warmed. |
| Local Bible search | Runs against cached translation data. |
| Canonical Context | Available after the study pack is installed. |
| Maps and journeys | Core data is available after the maps pack is installed; external tiles/links may not be. |
| Notes, highlights, saved studies | Stored for the browser profile in IndexedDB and available offline. |
| Imported translations | Device-only and available from that browser profile. |
| AI answers and LLM health | Require a reachable internet or local model service. |
| Translation downloads and licensed-provider content | Require a network/provider. |

The `study` and `maps` packs are installed by default after a successful online
load. The larger `sources` pack is optional and must be installed explicitly
from the offline controls.

An installed PWA is therefore offline-capable, not fully offline AI. With a
reachable Ollama server on the local network, AI may work without internet, but
the PWA must still be able to reach that server through the BHF backend.

## Manage offline storage

The settings sheet provides:

- **Install app** — opens the browser install prompt when supported, or shows
  the platform-specific browser steps for manual installation.
- **App update** — clears rebuildable/API cache data, preserves personal local
  records and device-imported translations, and asks the service worker to
  check for a new shell. The button reports when an update is available.
- **Offline readiness** — summarizes the service worker, translations, packs,
  local records, and queued mutations.
- **Refresh offline data** — re-downloads rebuildable installed data without
  clearing user-created records.
- **Clear offline cache** — removes rebuildable cache entries while preserving
  notes, highlights, saved work, queued map mutations, and device-imported
  translations.
- **Export offline data** — downloads a JSON snapshot of browser-local records
  and pack metadata.
- **Import offline data** — merges a prior snapshot into the current browser
  profile without clearing existing records.
- **Encrypted study vault** — downloads or restores an end-to-end encrypted
  portable copy of notes, highlights, saved studies, and map studies. Restores
  merge newer records and retain an explicit conflict copy if needed.
- **Share notes and studies** — sends a readable copy to Apple Notes, Google
  Keep, or another installed sharing target. This is an export, not two-way
  sync.
- **Cloud study sync** — synchronizes the encrypted vault with configured
  OneDrive or iCloud/CloudKit accounts. A deployment must enable a provider
  before its connection control becomes available.

Exported snapshots intentionally exclude provider credentials.

## Updates and stale content

When a new BHF release changes the service worker, the PWA installs the new
shell and removes old versioned caches. **App update** also clears rebuildable
API/offline data so backend changes are fetched again, while preserving local
records and device-imported translations. Use **Refresh offline data** afterward
when the shell or installed data packs need to be rebuilt.

## Privacy and data boundaries

- PWA storage belongs to the current browser profile and origin until the user
  explicitly creates a Study Vault or connects a configured cloud provider.
- Cloud providers receive the encrypted Study Vault, not the passphrase or BHF
  AI credentials. Apple Notes and Google Keep receive only the readable copy a
  person explicitly shares.
- Device-imported translations and offline records are not included in Git or
  a Docker image.
- Server-side `.bhf/study.sqlite` data and browser IndexedDB are separate
  storage layers. Export browser data before clearing site storage.
- Map-note mutations may queue for replay when connectivity returns. Notes,
  highlights, and saved studies are treated as device-local PWA records.
- Optional agent conversation memory is a separate server setting and is off
  by default.

## Troubleshooting

**No install option appears:** confirm the page is on HTTPS or localhost, reload
after the service worker registers, and check whether the browser supports PWA
installation.

**The app opens offline but a study area is empty:** reconnect, open settings,
install or refresh the relevant study, maps, sources, or translation data.

**Ask BHF fails offline:** connect to the internet provider or make sure the BHF
backend can reach the configured local model server.

**OpenRouter setup is rejected:** use the same browser session and origin that
started setup, and use trusted HTTPS for non-localhost deployments.

**A PWA update looks stuck:** use **App update**. It clears rebuildable/API
cache data, checks for a new shell, and reloads the app. Reload all BHF windows
if one still shows the old shell. Refresh the data packs afterward if needed.

For provider configuration, encryption details, and recovery guidance, see
[Study Vault Sync](study-vault-sync.md).
