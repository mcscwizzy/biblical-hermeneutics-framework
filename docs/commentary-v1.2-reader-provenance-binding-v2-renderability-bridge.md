# Commentary v1.2 Reader Provenance Binding v2 Renderability Bridge

Reader-level projection determines which ideas have priority for a reader. It
must not be the sole source of safe provenance capability.

Binding v1 unintentionally made projection eligibility equivalent to
renderability: only synthesis units attached to projected reader ideas
received renderer-selectable provenance paths. A chapter could therefore have
legally usable synthesis and evidence while exposing no legal path that the
renderer was allowed to cite.

Binding v2 preserves the projected v1 priority paths exactly. When at least one
priority path exists, those paths are the only active renderer paths and the
fallback class is suppressed. When projection yields no priority paths, v2
conservatively checks the existing synthesis contracts and may expose
content-addressed `render_path_...` fallback paths for eligible synthesis
units. A fallback path is renderability-only provenance; it is not a reader
idea and does not claim CORE or RELEVANT status.

Each fallback path is derived from one real synthesis unit and that unit's
exact evidence IDs. The path retains passage scope, kind, verse references,
confidence, interpretation level, dispute status, and ancestry hashes. The
resolver accepts only listed, chapter-scoped, deterministic paths and maps
them to the unchanged canonical `synthesis_ids` and `evidence_ids` fields.
Cross-synthesis evidence pairing, fabricated reader ideas, out-of-chapter
paths, unknown paths, and duplicate paths remain rejected.

The bounded v2 diagnostic keeps Prompt 1.8, the compiled synthesis, evidence,
reader projection, ancestry envelope, output conformance, validator, scorer,
Gate, renderer, and effort unchanged. Its only renderer-input change is the
versioned path-selection adapter. The adapter also clarifies that the sample
output envelope illustrates field structure; actual values must come from the
supplied chapter contract.

Numbers 2 demonstrates the original deadlock: zero projected ideas and zero
v1 paths coexisted with two medium-confidence, disputed, current-chapter
synthesis units. V2 exposes exact fallback paths for those units without
altering their classifications or the reader-level projection.
