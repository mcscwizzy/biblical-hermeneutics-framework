# Translation Workflow

BHF uses one curated translation catalog. ASV and KJV are server-side bundled
datasets; user-imported translations are parsed and stored only in the browser
device's IndexedDB.

## What Ships With BHF

- ASV and KJV are bundled Bible translations.
- ASV lives at `bhf_agent/data/asv_bible.json`.
- KJV lives at `bhf_agent/data/kjv_bible.json`.
- ASV is public domain in the United States.
- Both translations are always available offline with no setup.

## What Can Be Installed

Only translations listed in the curated catalog can appear in the UI. Bundled
translations are immediately available in the reader; other translations must
be installed or imported first.

- Only ASV and KJV are stored or served by the BHF server.
- Copyrighted translations remain visible as license-required entries and do
  not expose a BHF download button unless an authorized provider is configured.
- A public GitHub repository does not by itself prove that a translation is
  legally redistributable.
- Users may privately import lawfully obtained XML files for personal offline
  use on their own device. The browser parses the XML; the file is not uploaded
  to BHF and is not available to another browser or user.

## Server Storage

The default storage root is `.bhf-data/translations/`. It contains only bundled or
server-managed translation data; the web application does not upload or store
user-imported XML files there.

Environment override:

- `BHF_TRANSLATIONS_PATH`

Bundled files are stored as:

- `.bhf-data/translations/kjv.json`
- `.bhf-data/translations/kjv.metadata.json`

The JSON file is the normalized Bible dataset. The metadata file records source
and validation details, including SHA-256 hashes, counts, source URL, and
license status.

## Device Import Flow

The browser handles a private XML import locally:

1. Confirm that the file was obtained lawfully.
2. Parse the XML in the browser.
3. Normalize its books, chapters, and verses.
4. Store the normalized dataset in that browser's IndexedDB.
5. Use the local dataset for reader and offline requests.

No imported XML bytes or normalized private dataset are sent to the server.

## Supported XML Shape

BHF accepts a nested Bible XML structure similar to Beblia exports:

- A root element containing book elements.
- Book elements named `book` or `biblebook`.
- Book identity from `bname`, `name`, `book`, `osisID`, or a positive book
  number.
- Chapter elements named `chapter`.
- Chapter numbers from `cnumber`, `number`, `n`, or `id`.
- Verse elements named `verse` or `vers`.
- Verse numbers from `vnumber`, `number`, `n`, or `id`.
- Verse text taken from the element text content.

The installer normalizes the parsed result into BHF's internal JSON structure
with book, chapter, and verse ordering preserved.

## Default Translation

- The persisted reader default is `default_translation`.
- Default is ASV.
- The default must point to an installed translation.
- If the configured default is missing, BHF falls back to ASV.

## Source Notice

BHF does not maintain third-party translation repositories. A downloaded
translation should be treated as third-party content even if it is public
domain.

For protected imports, BHF shows a private-use notice and keeps the imported
file local to the current device. Removing the browser app or clearing site data
removes the device-local import.
