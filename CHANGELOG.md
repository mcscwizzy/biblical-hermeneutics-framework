# Changelog

All notable changes to the Biblical Hermeneutics Framework are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning is two-level: this file tracks the **framework** version (also in
[`VERSION`](VERSION)); each module additionally carries its own `version` in
frontmatter. See [`docs/architecture.md`](docs/architecture.md#versioning).

## [Unreleased]

## [0.1.0] — 2026-06-19

### Added

- **Core framework** (5 modules): `core.core-framework`,
  `core.observe-interpret-apply`, `core.original-audience`,
  `core.epistemic-humility`, `core.anti-hallucination`.
- **Genre module:** `genre.epistle`.
- **Book module:** `book.romans`.
- **Historical modules:** `historical.roman-empire`, `historical.patronage`.
- **Language module:** `language.greek`.
- **Tooling:** `tools/validate.py` (frontmatter + structure + dependency +
  link + token-budget validation) and `tools/compose.py` (dependency-resolving
  prompt assembly).
- **Profiles:** `minimal-7b`, `standard`.
- **Docs:** philosophy, architecture, module spec, style guide, glossary,
  how-to-use guides, governance/neutrality charter, contributor guide.
- **Tests:** behavioral rubric (`core-behaviors`) + Romans fixture.
- **Licensing:** dual CC BY 4.0 (content) + MIT (code).

[Unreleased]: https://github.com/OWNER/biblical-hermeneutic-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/OWNER/biblical-hermeneutic-framework/releases/tag/v0.1.0
