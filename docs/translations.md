# Translation Workflow

BHF now uses one curated translation catalog and one local storage directory for
all non-bundled Bible texts.

## What Ships With BHF

- ASV is the only bundled Bible translation.
- ASV lives at `bhf_agent/data/asv_bible.json`.
- ASV is public domain in the United States.
- ASV is always available offline with no setup.

## What Can Be Installed

Only translations listed in the curated catalog can appear in the UI.

- Reviewed public-domain or openly licensed translations may be downloaded from
  their curated raw source URL and stored locally for offline use.
- Copyrighted translations remain visible as license-required entries and do
  not expose a BHF download button unless an authorized provider is configured.
- A public GitHub repository does not by itself prove that a translation is
  legally redistributable.
- Users may privately import lawfully obtained XML files for personal offline
  use on their own device.

## Local Storage

The default storage root is `.bhf/translations/`.

Environment override:

- `BHF_TRANSLATIONS_PATH`

Installed files are stored as:

- `.bhf/translations/kjv.json`
- `.bhf/translations/kjv.metadata.json`

The JSON file is the normalized Bible dataset. The metadata file records source
and validation details, including SHA-256 hashes, counts, source URL, and
license status.

## Install Flow

The backend installer performs the same workflow for direct downloads and local
XML imports:

1. Resolve the translation from the curated catalog.
2. Fetch the exact approved URL or accept the imported XML bytes.
3. Reject non-HTTPS, non-allowlisted, or unapproved sources.
4. Reject HTML or oversized downloads.
5. Parse the XML.
6. Validate the translation identity, canon, counts, and verse integrity.
7. Write a normalized JSON dataset to a temporary file.
8. Atomically rename the JSON and metadata into place.
9. Update the search cache and reader defaults.

Failures do not replace a working existing installation.

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
file local to the current device.
