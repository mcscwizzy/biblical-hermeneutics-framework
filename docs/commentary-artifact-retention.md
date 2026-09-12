# Commentary artifact retention and cleanup

Last reviewed: 2026-09-12

This document defines which commentary artifacts remain available for runtime use, release promotion, reproducibility, or audit review. The companion [inventory](commentary-artifact-inventory.json) is a deterministic directory-level snapshot; it retains a tombstone for the one diagnostic artifact removed in this cleanup.

## Retained runtime releases

- `.bhf-data/bhf-commentary-v1.1/` is the default packaged release and remains the compatibility baseline.
- `.bhf-data/bhf-commentary-v1.2/` is the opt-in packaged release. Its manifest/checksum index and 62 published chapters are required for runtime integrity.
- `.bhf-data/bhf-commentary/` is retained as the legacy `commentary-v1.0` compatibility layout.
- `.bhf-data/bhf-commentary-production/` and its `v1/` historical layout remain review-only. Existing historical tests and audit tooling still reference them, and no replacement has been established.

The packaged releases are intentionally separate from `.bhf-data/bhf-commentary-candidates/`. Candidate material is not a runtime fallback and is excluded from the Vercel package through the existing deployment configuration.

## Retained validation and audit material

Candidate roots with active release, provenance, conformance, reader-projection, renderer, or richness validation consumers remain in place. Modified or newly created worktree roots are retained as `REVIEW_ONLY` unless an explicit dependency scan proves that removal is safe. Unknown artifacts are never deleted by this cleanup.

The inventory records repository references from Python, tests, documentation, and deployment configuration. A root is retained when it is required for v1.1 compatibility, v1.2 promotion, reproducibility, active validation, or historical audit.

## Removed superseded artifact

The following diagnostic was removed from the working tree:

- `.bhf-data/bhf-commentary-candidates/commentary-renderer-transport-diagnostic-v1/`
- `tools/commentary_v12_renderer_transport_diagnostic.py`
- `tests/test_commentary_v12_renderer_transport_diagnostic.py`

The deletion is safe because the transport investigation is complete, no runtime or release-promotion code consumes the tool, and the dedicated test only exercises that retired tool. The immutable report remains at `docs/commentary-v1.2-renderer-transport-diagnostic-v1.md`; the raw source artifact is recoverable from Git commit `5a3cb3329a3671f81db187f85478b770f068f233` (`Add renderer transport diagnostic for Numbers 2`).

No release payload, manifest, checksum, candidate source required by the v1.2 promotion path, active runtime layout, or unknown worktree artifact was removed.

## Measured effect

Counts below cover the five commentary roots and the candidate tree listed in the inventory. The distinct `.bhf-data` total avoids double-counting the nested production `v1/` root.

| Scope | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Candidate files | 8,878 | 8,861 | 17 |
| Candidate bytes | 400,592,023 | 400,517,308 | 74,715 |
| Candidate recursive directories | 1,074 | 1,073 | 1 |
| Candidate first-level roots | 41 | 40 | 1 |
| Distinct `.bhf-data` files | 11,465 | 11,448 | 17 |
| Distinct `.bhf-data` bytes | 408,540,334 | 408,465,619 | 74,715 |

The cleanup therefore removes approximately 0.0187% of candidate bytes and 0.0183% of the measured `.bhf-data` bytes. The small reduction is intentional: dependency evidence supports retaining the remaining validation and audit corpus.

## Future cleanup policy

1. Inventory the directory and repository references before deletion.
2. Keep active releases, manifests, checksums, provenance inputs, and audit reports.
3. Treat modified, untracked, or unknown roots as review-only until their consumers are proven absent.
4. Remove only a named superseded artifact with an immutable report or Git source preserved.
5. Re-run focused release, packaging, and reader tests after cleanup; do not regenerate commentary or alter CKL records as part of cleanup.
