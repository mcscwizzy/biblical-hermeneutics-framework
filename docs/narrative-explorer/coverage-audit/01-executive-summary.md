# NE-A1 CKL coverage audit — executive summary

**Baseline:** NE-5B `8e6283a68c020691161278504127e566f63c41a4`; audit branch base is identified in `methodology-validation.json`.
**CKL inventory:** 687 validated objects; fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.
**Census:** 1,189 of 1,189 canonical chapters; all rows are generated from the authoritative ASV/BHF book list.

## Chapter coverage

- Passage-specific evidence: 985 chapters; 986 chapters have at least one sourced claim/evidence placement, including any chapter whose lookup remains incomplete.
- Contextual or entity-only coverage: 71 chapters.
- No eligible CKL material under NE-5B passage rules: 132 chapters.
- Incomplete or unknown CKL coverage: 1 chapter.
- Broad-scope parent records excluded in 0 chapters; unscoped book anchors occur in 0 chapters; multi-chapter anchors occur in 704 chapters.

These are inventory states, not judgments about whether a chapter should have archaeology, physical geography, or cosmic-geography material. A completed empty CKL lookup is not evidence that external scholarship contains nothing relevant.

## External domains

- Explicit map/place links: 7741 stored rows; 7741 pass book/chapter/verse checks; 0 target IDs do not resolve.
- Explicit route links: 2 rows; territory/context links: 13 rows.
- Archaeology service: 75 items; 71 have valid passage links and 4 do not. It has 94 explicit link rows; manuscript service is separate.
- Full-corpus map and archaeology API counts are not inferred from the explicit-link tables. The API prefers passage-text matches before reference-link fallback, so only sampled chapters have live resolver results; other API states remain unknown in the CSV.

## Provenance and relationships

- Unique source IDs referenced: 2784; unresolved source IDs: 2; records with weak bibliography fields: 16.
- Authored object relationships: 4061; resolvable destinations: 4061; missing destinations: 0; exact reciprocal pairs: 98; 4061 fall into the current `uncategorized` projection type.
- Projected CKL records without a Narrative Explorer section: 591 chapters contain at least one; investigate classification before adding evidence.

## Validation

- Deterministic stratified sample seed: `20261015`; actual chapters compared: 19.
- Resolver-backed builds: 16 targeted chapters; all selected chapters passed local normal-retrieval/projector comparison: True.
- Census rows: 1189; unique identities: 1189; checks: `pass`.
- CKL, map, and archaeology source records were not edited. Read-only database checks and sample details are in `methodology-validation.json`.
