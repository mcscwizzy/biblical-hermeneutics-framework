# Architecture

BHF is a library of small, composable Markdown **modules** plus light tooling to
validate and assemble them. This document explains how the pieces fit together.
The authoritative module contract lives in [`module-spec.md`](module-spec.md).

## The module model

Every module is one Markdown file with **YAML frontmatter** (machine-readable
metadata) and a **fixed-section body** (the human- and AI-readable guidance).
Modules fall into six types:

| Type | Folder | Role |
|------|--------|------|
| `core` | `framework/core/` | The always-on interpretive posture. |
| `genre` | `framework/genres/` | How to read a literary genre. |
| `book` | `framework/books/` | How to read a specific book. |
| `context` | `framework/context/` | Historical, cultural, and literary background (setting, institutions, social systems, recurring themes). |
| `language` | `framework/language/` | Original-language and literary-device guidance. |
| `profile` | (generated to `profiles/`) | Pre-assembled bundles of the above. |

## Composition and dependencies

Modules declare relationships in frontmatter:

- **`requires`** — hard dependencies, **auto-included** by `compose.py`
  (e.g., every module requires `core.core-framework`).
- **`recommends`** — suggested companions, surfaced but not auto-included.
- **`tokens`** — an approximate cost so a prompt can be assembled within a
  model's budget.

`tools/compose.py` takes a set of module ids (or a named profile), computes the
transitive `requires` closure, topologically orders the result, and concatenates
the bodies into a single prompt. Dependencies always precede dependents; among
modules with no ordering constraint between them, the sort key is
`(type, order, id)` — so `core` comes before `genre` before `book`, and the
optional `order` field sequences the core modules into a hermeneutical workflow
(framework → genre awareness → original audience → observe/interpret/apply →
intertextuality → epistemic humility → anti-hallucination). The dependency graph
is guaranteed acyclic by `validate.py`.

```
selected ids ──► resolve requires (transitive) ──► topological order ──► one prompt
```

This is what lets the *same library* serve a 7B phone model (small profile, tight
token budget) and a frontier model (deep, multi-module assembly).

## Profiles

Profiles are named module sets defined in
[`profiles/profiles.yml`](../profiles/profiles.yml). The committed `profiles/*.md`
files are **generated artifacts** (`compose.py --profile <name> --write`) so that
non-coders can copy/paste a ready prompt without running any tooling. CI checks
they stay in sync with their definitions.

## Tooling

- `tools/validate.py` — enforces [`module-spec.md`](module-spec.md) (CI gate).
- `tools/compose.py` — assembles modules/profiles into a prompt.
- `tools/bhf_lib.py` — shared loading, parsing, and dependency resolution.

Tooling is intentionally light (Python + PyYAML). The Markdown is the product;
the scripts are a convenience.

## Versioning

Two levels of SemVer:

- **Framework version** ([`VERSION`](../VERSION), [`CHANGELOG.md`](../CHANGELOG.md)):
  - **MAJOR** — breaking change to `module-spec.md` or the core method.
  - **MINOR** — new modules or new sections.
  - **PATCH** — corrections and clarifications.
- **Per-module version** (frontmatter `version`) — each module evolves
  independently, so adding or fixing one book doesn't force a framework bump.

The `status` field (`draft → review → stable → deprecated`) tracks each module's
lifecycle. Releases are git tags (e.g., `v0.1.0`).
