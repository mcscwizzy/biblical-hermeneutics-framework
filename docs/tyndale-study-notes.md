# Tyndale Open Study Notes

Tyndale Open Study Notes are a published secondary study resource displayed beside the BHF Bible reader. They are separate from Scripture, the BHF-curated Canonical Knowledge Library (CKL), and the lexicon. The reader pane works without an AI provider and does not automatically inject Tyndale material into BHF answers.

## License and attribution

The supported source is Tyndale Open Study Notes, Copyright © 2022 Tyndale House Publishers, licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0): <https://creativecommons.org/licenses/by-sa/4.0/>.

BHF stores this provenance in the commentary database. The generated SQLite file is an adapted storage/format conversion; the underlying commentary wording is not intentionally altered. This source license is separate from BHF's global content license.

## Obtain and import the official source

Obtain the official Tyndale Open Study Notes archive through a lawful source and save it locally. BHF does not scrape a website or download the archive automatically.

From the repository root, run:

```sh
.venv/bin/python -m framework.commentary import-tyndale \
  --source /path/to/tyndale_open_studynotes.zip \
  --output .bhf/commentary.sqlite
```

The importer inspects the supplied archive, safely rejects ZIP path traversal and symlinks, supports structured JSON/XML/CSV/TSV records, normalizes Bible book names using BHF's Bible logic, preserves source text, and reports entry/anchor counts, recognized books, warnings, and records that could not be mapped. It never calls the network or an LLM.

For a production import, add `--fail-on-unmapped`. The importer then leaves the existing database untouched if a supplied Scripture reference cannot be mapped. Rebuilds are atomic, so an interrupted or failed import does not leave a partially written runtime database.

Before installing an unfamiliar archive, qualify it with a non-mutating dry run:

```sh
.venv/bin/python -m framework.commentary import-tyndale \
  --source /path/to/tyndale_open_studynotes.zip \
  --dry-run
```

Review `recognized_files`, `entry_count`, `anchor_count`, `recognized_books`, `unmapped_records`, `unrecognized_records`, and `warnings` in the JSON report. Use `--strict` for the final import after review; it rejects unmapped references, unsupported records, parser warnings, and empty archives before the installed database can be replaced.

The default runtime database is `.bhf/commentary.sqlite`. It is generated local data and is ignored by Git. To rebuild it, run the same command again; the existing commentary tables are replaced from the supplied source archive. To remove the installed resource, delete `.bhf/commentary.sqlite`.

## Reader behavior

The Bible reader has a labeled, collapsible Tyndale Study Notes companion pane. It automatically follows book/chapter changes, previous/next chapter navigation, translation-reader navigation, and restored reader tabs. The current chapter is fetched from:

`GET /api/commentary/{book}/{chapter}`

The API returns structured entries, anchors, and one source/provenance block. If the database is absent, it returns an ordinary `available: false` response with `reason: commentary_not_installed` and no error page.

Installation and import status are available at `GET /api/commentary/diagnostics`. The response includes the source provenance and the persisted import report, including unresolved reference indexes and intentionally anchorless records.

Selecting one verse or a verse range focuses overlapping notes in the chapter pane and scrolls the first match into view. Other chapter notes remain visible. A selection with no matching note leaves the pane usable and does not show an error.

The browser caches the current response and lightly prefetches adjacent chapters. The standard BHF API cache and service worker include commentary responses, so an installed local database can support offline reading after the relevant chapter response has been cached. No AI or network call is required to read an installed/cached resource.

## Architecture boundary

The flow is:

`official local archive → framework.commentary importer → .bhf/commentary.sqlite → CommentaryRepository → CommentaryService → reader API and pane`

The service is deterministic, indexed, and read-only at runtime. The optional
AI evidence integration is described below; it remains separate from CKL
retrieval, CKL ranking, and lexicon lookup.

## Optional AI evidence integration

The selective AI evidence path is enabled separately from the reader. Add this
to the agent or web configuration after installing the database:

```json
{
  "commentary": {
    "enabled": true,
    "database_path": ".bhf/commentary.sqlite",
    "max_entries": 4
  }
}
```

When enabled, BHF retrieves a small set of locally stored notes only when the
question explicitly requests Tyndale/commentary/source material or when the
deterministic coverage pass identifies a narrow historical, cultural, original-
audience, customs, or difficult-passage gap. Ordinary questions do not receive
Tyndale context automatically. The notes are inserted under a clearly labeled
`SECONDARY TYNDALE EVIDENCE` block and remain distinct from Scripture, CKL, and
lexicon evidence. Coverage is evaluated again after retrieval, and source
provenance is retained in developer metadata.
