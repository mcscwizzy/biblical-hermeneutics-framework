# BHF Documentation

BHF is an AI-optional Bible study workspace as well as a hermeneutical
framework. Start with the guide that matches whether you want to use the app,
understand its evidence model, or develop and maintain it.

## Use BHF

- [Website and PWA](web-pwa.md) — use the hosted or self-hosted application,
  connect AI, install the PWA, and understand what works offline.
- [Frontend and backend routing](deployment-routing.md) — configure same-origin
  deployments, same-origin Vercel, or an optional durable remote backend.
- [Study Vault Sync](study-vault-sync.md) — encrypt, back up, share, and
  configure OneDrive or iCloud synchronization for personal study records.
- [Docker](docker.md) — install, configure, operate, update, reset, and uninstall
  a local containerized deployment.
- [Local build and development](local-development.md) — run from source, select
  a provider, build databases, run tests, and build a Python package.
- [ChatGPT, Claude, and Gemini](how-to-use/claude-chatgpt-gemini.md) — use the
  prompt-only framework without the BHF application.
- [Local models](how-to-use/local-models.md) and
  [small models](how-to-use/small-models-7b.md) — prompt-only runtime guidance.

## Understand BHF

- [Architecture](architecture.md) — components, trust boundaries, and the full
  path from a question to a validated answer.
- [Contextual presentation](contextual-presentation.md) — EvidenceBundle,
  salience ranking, validated discovery cards, Dig In, caching, and fallback.
- [Philosophy](philosophy.md) — why BHF teaches method rather than conclusions.
- [Glossary](glossary.md) — project terminology.
- [Framework module specification](module-spec.md) — authoritative Markdown
  module contract.
- [Canonical Knowledge Library](canonical_knowledge_library.md) — CKL authoring,
  retrieval, storage, and governance.
- [Lexicon architecture](lexicon-architecture.md) and
  [word study](word-study.md) — lexical storage and runtime behavior.
- [Archaeology evidence and media policy](archaeology.md) — deterministic
  first-class evidence, rights-aware media, importing, presentation, CKL links,
  and offline behavior.

## Build and maintain data

- [Tooling reference](../tools/README.md).
- [Testing guide](../tests/README.md).
- [Examples and sample configurations](../examples/README.md).
- [Compile the lexicon](compile-lexicon.md).
- [Lexicon source policy](lexicon-sources.md).
- [Translation management](translations.md).
- [Tyndale Open Study Notes](tyndale-study-notes.md) — install and use the attributed commentary reader companion.
- [Evaluation](evals.md).

## Contribute content

- [Style guide](style-guide.md).
- [Framework module specification](module-spec.md).
- [Canonical Knowledge Library](canonical_knowledge_library.md).
- [Contributing guide](../CONTRIBUTING.md).

Historical implementation prompts, completed repair plans, and dated progress
reports are intentionally excluded from `docs/`. Git history remains the source
for that project archaeology.
