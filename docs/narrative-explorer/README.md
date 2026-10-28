# Narrative Explorer

Narrative Explorer is BHF's primary passage and evidence exploration
experience. It presents CKL-backed evidence and relationships for the selected
passage, with source identity, connection type, uncertainty, and provenance.
The Canonical Knowledge Library is the authoritative research source.

## Passage route and navigation

The read-only passage route is:

```text
GET /api/narrative-explorer/v1/passages/{book}/{chapter}
    ?verse_start={verse}&verse_end={verse}
```

Verse parameters are optional. Invalid passages return a client error;
unavailable canonical lookup returns HTTP 503. The response is a deterministic
projection over current CKL evidence and curation data. Reader links open a
related passage or subject and preserve a return path to the original passage.

NE-9C relationship curations and NE-10 passage bridge registry records are
read-only inputs. They preserve the reviewed relationship, direction,
eligibility, identity, held-candidate state, and provenance. They do not replace
CKL objects or add evidence during display.

## Neighboring study features

Narrative Explorer shares the Bible reader with translations, Maps and
Archaeology, Greek/Hebrew word study, Tyndale Open Study Notes, personal notes
and highlights, saved studies, and offline packs. Tyndale is a separate
attributed notes service. Ask BHF hands the passage and user-authored question
to an external assistant.

Generated BHF Commentary was retired in NE7R3. `/api/bhf-commentary` URLs keep
HTTP 410 compatibility responses. Current runtime and package inputs do not
include the generated Commentary corpus or generator.

## Historical research and release records

- [NE-7R3 retirement audit and reader results](ne7r3/01-commentary-dependency-audit.md)
- [NE-9C bulk curation final report](ne9c-bulk-curation/final-report.md)
- [NE-10 evidence discovery audit](ne10-evidence-discovery-audit.md) and
  [NE-10 results](ne10-results.md)
- [NE-11C1 Jonah / Matthew bridge implementation](ne11c1-jonah-matthew-bridge.md)
- [NE-11D4 final feature acceptance gate closure](ne11d/13-feature-gate-closure.md)
- [Historical architecture index](../maintenance/historical-decisions.md)

The numbered `ne7`, `ne8`, and earlier pilot/audit pages describe their
original checkpoints. Treat them as historical snapshots rather than current
runtime documentation.
