# Commentary candidate retention

Candidate namespaces are evidence only when a current verifier, runtime,
release test, or lineage reconstruction depends on them. The packaged release
remains authoritative after freeze.

## Keep

- frozen packaged releases and their descriptors/checksum indexes;
- the current source-lineage baseline;
- historical qualification and scale-pilot artifacts explicitly required to
  reconstruct current lineage or provenance;
- deliberate deterministic test fixtures and release-promotion inputs.

## Delete after freeze

- completed generation sessions and raw transport responses;
- transient renderer-input staging and batch checkpoints;
- duplicate or superseded pilot workspaces;
- temporary canaries and prechecks not referenced by current verification;
- local runtime scratch state.

The full v1.2 corpus-runner result tree is retained while current promotion
and reconciliation tests consume its historical results. New scratch output
belongs in ignored, version-specific workspaces rather than beside retained
audit artifacts.
