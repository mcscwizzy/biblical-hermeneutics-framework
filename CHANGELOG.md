# Changelog

All notable changes to the Biblical Hermeneutics Framework are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning is two-level: this file tracks the **framework** version (also in
[`VERSION`](VERSION)); each module additionally carries its own `version` in
frontmatter. See [`docs/architecture.md`](docs/architecture.md#versioning).

## [Unreleased]

### Added

- **Book modules** (hermeneutic profiles, the top framework layer):
  `book.genesis`, `book.psalms`, `book.matthew`, `book.revelation`, and a
  rewritten `book.romans`. Each assumes Core/Genre/Context/Language are already
  loaded and specializes — teaching what to notice and what questions to ask,
  not what the book means. Method only; denomination-neutral.
- **Context layer** (`framework/context/`): a category for historical, cultural,
  and literary background reusable across books and genres. New modules:
  `context.ancient-near-east`, `context.second-temple-judaism`, `context.temple`,
  `context.covenant`, and `context.honor-shame` (joining the migrated
  `context.roman-empire` and `context.patronage`). Method only — they teach what
  questions to ask about the world behind the text, not what a passage concludes.
- **`scholar` profile** — full-depth assembly (all core, genre, and context
  modules plus `language.greek`) for frontier models with large context windows.
- **Genre modules** completing the set of seven: `genre.narrative`,
  `genre.poetry`, `genre.wisdom`, `genre.prophecy`, `genre.gospel`, and
  `genre.apocalyptic` (joining the existing `genre.epistle`). Each follows the
  genre template and `genre.epistle`'s structure: how the genre communicates,
  common misreadings, and uncertainty handling — method only, no doctrine.
- **Core module `core.genre-awareness`** — identify literary genre before
  interpreting (the universal reflex; depth stays in the `genre/` modules).
- **Core module `core.intertextuality`** — recognize where a text quotes,
  alludes to, or develops earlier Scripture, framed as literary observation
  (a neutral reframing of the proposed "Scripture interprets Scripture"; the
  doctrinal canonical-unity assumption was deliberately not adopted).
- Optional `order` frontmatter field: a within-type sequencing hint so the
  composed prompt follows a hermeneutical workflow instead of alphabetical id
  order. Composition now sorts by `(type, order, id)`.

### Changed

- **Book module section contract** redefined as a hermeneutic profile:
  Purpose, When to apply, Genre signals, Historical anchors, Literary features,
  Key interpretive questions, Common misreadings, Handling uncertainty,
  Cross-references (replacing the v0.1 placeholder book sections). `validate.py`
  and `docs/module-spec.md` updated accordingly.
- Reordered and renumbered the `core/` modules to a workflow sequence:
  framework → genre awareness → original audience → observe/interpret/apply →
  intertextuality → epistemic humility → anti-hallucination.
- Profiles updated: `minimal-7b` now includes genre awareness; `standard`
  includes all seven core modules in workflow order.
- **Renamed the `historical` module type/category to `context`** (folder
  `framework/historical/` → `framework/context/`; type `historical` → `context`).
  This is a pre-1.0 breaking change to two module ids
  (`historical.roman-empire` → `context.roman-empire`,
  `historical.patronage` → `context.patronage`); all cross-references, tooling,
  spec, and docs were updated. "Context" better fits a layer that includes
  cultural systems (honor/shame, patronage) and literary themes (temple,
  covenant), not only history.

- `LICENSE` now contains the canonical MIT text (no preamble) so GitHub's
  license detection recognizes it; the code/content split is documented in
  `README.md`.
- `LICENSE-CONTENT` now contains the full official CC BY 4.0 legal code.
- Reformatted the Python tooling to PEP 8 (88-column limit); composed output is
  byte-for-byte unchanged.

### Added

- `SPDX-License-Identifier` headers to the Python tooling (MIT) and to
  `LICENSE-CONTENT` (CC-BY-4.0).
- Contributor notes: virtualenv/PEP 668 setup tip and a documented code-style
  convention in `tools/README.md` and `CONTRIBUTING.md`.

## [0.1.0] — 2026-06-19

### Added

- **Core framework** (5 modules): `core.core-framework`,
  `core.observe-interpret-apply`, `core.original-audience`,
  `core.epistemic-humility`, `core.anti-hallucination`.
- **Genre module:** `genre.epistle`.
- **Book module:** `book.romans`.
- **Historical modules:** `historical.roman-empire`, `historical.patronage`
  (renamed to `context.*` in a later release — see Unreleased).
- **Language module:** `language.greek`.
- **Tooling:** `tools/validate.py` (frontmatter + structure + dependency +
  link + token-budget validation) and `tools/compose.py` (dependency-resolving
  prompt assembly).
- **Profiles:** `minimal-7b`, `standard`.
- **Docs:** philosophy, architecture, module spec, style guide, glossary,
  how-to-use guides, governance/neutrality charter, contributor guide.
- **Tests:** behavioral rubric (`core-behaviors`) + Romans fixture.
- **Licensing:** dual CC BY 4.0 (content) + MIT (code).

[Unreleased]: https://github.com/mcscwizzy/biblical-hermeneutics-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mcscwizzy/biblical-hermeneutics-framework/releases/tag/v0.1.0
