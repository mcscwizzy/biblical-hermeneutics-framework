# BHF architecture

BHF combines a reviewed hermeneutics framework with a local-first Bible study
application. Narrative Explorer is the primary passage and evidence exploration
experience. The Canonical Knowledge Library (CKL) is the authoritative source
for curated research data.

## Request and evidence flow

```text
Browser passage reader
    ├── Bible translation and passage navigation
    ├── Narrative Explorer passage projection
    ├── maps, archaeology, lexicon, and Tyndale notes
    └── private notes, highlights, saved studies, and offline packs
            │
            ├── FastAPI routes and deterministic local services
            ├── CKL objects, sources, schema, and reviewed curation data
            └── NE-9C relationship curation + NE-10 passage bridge records
                    │
                    └── Ask BHF handoff → external conversational assistant
```

The read-only Narrative Explorer API is
`GET /api/narrative-explorer/v1/passages/{book}/{chapter}`. Optional
`verse_start` and `verse_end` parameters scope the response to a selected verse
range. The route resolves passage evidence through the CKL runtime and returns
provenance-bearing relationship and bridge data. The browser's passage links
let a reader navigate from a connection into the related passage and inspect
its evidence.

NE-9C curations classify CKL relationships for reader exploration. NE-10 adds
the accepted passage bridge registry and its held-candidate decisions. These
files preserve source identity and curation status and are inputs to the
runtime; the application does not edit them.

## Active components

- **Bible reader and translations:** bundled ASV and KJV data, passage
  navigation, translation comparison, and device-local translation import.
- **CKL:** version-controlled JSON records, object sources and evidence,
  schema, manifest, source locks, and reviewed curation registries. SQLite is a
  generated serving database.
- **Maps and archaeology:** reviewed records, rights-aware media metadata,
  routes, places, timelines, historical layers, and passage cross-links.
- **Lexicon:** packaged compressed lexical database and deterministic word
  lookup, with build/import tools and recorded licenses and revisions.
- **Tyndale Open Study Notes:** a separate attributed dataset with schema,
  importer, indexed repository, service, API, and reader pane. It is not the
  retired generated BHF Commentary product.
- **Private study and offline:** notes, highlights, saved studies, PWA assets,
  service-worker caching, and IndexedDB data remain separate from canonical
  research data.
- **Ask BHF:** prepares a passage-aware prompt and opens the configured external
  assistant. The reader does not embed or automate that assistant.

Generated BHF Commentary was retired in NE7R3. Stable `/api/bhf-commentary`
compatibility routes return HTTP 410. No generated Commentary release or
generation package is loaded by current runtime routes.

## Packaging and deployment

The Python wheel and source distribution package Python runtime modules and
declared package data. Docker builds CKL and lexical databases and obtains the
Tyndale source archive by pinned SHA-256 before creating its image. Vercel runs
the CKL build hook and bundles CKL resources plus the Tyndale database when the
build hook creates it. `.bhf-data` is local writable state and is excluded from
deployment bundles and Docker contexts.

See [local development](local-development.md), [Docker](docker.md),
[Narrative Explorer](narrative-explorer/README.md), and
[Ask BHF handoff](assistant-handoff.md) for operational details.
