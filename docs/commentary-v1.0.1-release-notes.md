# BHF Commentary v1.0.1

This patch release promotes the certified `commentary-v1.0.1` snapshot from
the `commentary-v1.0.1` candidate directory. `commentary-v1.0` remains an
immutable base release.

## Highlights

- Corrected Scripture range parsing.
- Restored anchored interpretive-note retrieval.
- Corrected EvidenceBundle projection.
- Added deterministic weighted evidence-availability classification.
- Applied 249 semantic chapter corrections: 95 commentary artifacts, 91
  legacy availability metadata corrections, and 63 status corrections.
- Refreshed evidence hashes after retrieval repairs.
- Corrected 1 Samuel 28 from `DATA_GAP` to `THIN`.
- Updated future `DATA_GAP` generation to prefer transparent fallback wording.

No CKL expansion or new commentary research is included in this release.
The remaining 132 likely true CKL data gaps are a separate milestone.

## Release facts

- Chapters: 1,189
- Availability: 827 `AVAILABLE`, 210 `THIN`, 152 `DATA_GAP`
- Validation: 1,189 validated; 0 partial; 0 needs review; 0 failed
- Evidence citations: 1,077/1,077 valid
- Verse references: 1,208/1,208 valid
- JSON/SQLite disagreements: 0
- Likely retrieval bugs: 0

Production should select this snapshot with:

```text
BHF_COMMENTARY_RELEASE=commentary-v1.0.1
```

The repository default remains `commentary-v1.0` so local/NAS development
continues to use the frozen release unless explicitly configured.
