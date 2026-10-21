# BHF documentation

BHF is a Bible study workspace built around a documented hermeneutical method.
Narrative Explorer is the primary evidence-exploration experience, with CKL as
the authoritative reviewed research source.

## Use BHF

- [Website and PWA](web-pwa.md) — reader workflow, Ask BHF, installation, and
  offline behavior.
- [Docker](docker.md) — local install, configuration, persistent data, and
  operations.
- [Local development](local-development.md) — setup, databases, tests, and
  package builds.
- [Frontend and backend routing](deployment-routing.md) — same-origin and
  split-host deployment configuration.
- [Study Vault Sync](study-vault-sync.md) — personal study record backup and
  optional encrypted sync.
- [Tyndale Open Study Notes](tyndale-study-notes.md) — active, separately
  attributed notes service and reader.
- [Ask BHF assistant handoff](assistant-handoff.md) — scope and privacy
  boundary for external conversation.

## Understand BHF

- [Architecture](architecture.md) — runtime, evidence flow, services, and
  packaging boundaries.
- [Narrative Explorer](narrative-explorer/README.md) — passage routes,
  evidence navigation, and curation inputs.
- [Canonical Knowledge Library](canonical_knowledge_library.md) — CKL source,
  authoring, retrieval, and governance.
- [Maps and archaeology](archaeology.md) — catalog, evidence, media rights,
  provenance, and offline behavior.
- [Lexicon architecture](lexicon-architecture.md), [word study](word-study.md),
  and [lexicon sources](lexicon-sources.md).
- [Translation management](translations.md).
- [Philosophy](philosophy.md), [glossary](glossary.md), and
  [framework module specification](module-spec.md).
- [Data retention](bhf-data-retention.md) — what is source data, runtime
  output, and historical evidence.
- [Historical decisions index](maintenance/historical-decisions.md) — Git
  references for major research and architecture milestones.

## Develop and maintain

- [Tooling reference](../tools/README.md).
- [Testing guide](../tests/README.md).
- [Examples and sample configurations](../examples/README.md).
- [Compile the lexicon](compile-lexicon.md).
- [Contributing guide](../CONTRIBUTING.md) and [style guide](style-guide.md).
- [Repository cleanup report](maintenance/repository-cleanup-report.md).

Historical research decisions, CKL methodology, source identities, and
hermeneutical classification rules remain part of the maintained research
record. Superseded implementation reports are removed from the current docs
tree or marked as historical snapshots; Git history preserves earlier copies.
