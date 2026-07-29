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
transitive `requires` closure, applies core framework inclusions, topologically
orders the result, and concatenates the bodies into a single prompt.
`core.intertextuality` is included whenever `core.core-framework` is present so
the core prompt always includes basic intertextual discipline. Dependencies
always precede dependents; among modules with no ordering constraint between
them, the sort key is
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

## Knowledge coverage and research expansion

The runtime keeps two CKL concepts separate:

- **Retrieval relevance** is the existing CKL ranking signal. It answers whether
  retrieved entries are related to the question and remains controlled by
  `canonical_library.minimum_relevance_score`.
- **Answer coverage** is a deterministic routing estimate performed after CKL,
  Scripture, lexicon, map, genre, and other local context have been gathered. It
  asks whether that context covers the dimensions the question actually requests.
  A highly relevant entry can therefore still have a material answer gap.

The default `knowledge_expansion` configuration uses `0.85` for sufficient
coverage and `0.60` for a major gap:

- `ckl_primary` uses the supplied context as the foundation and permits normal
  synthesis without treating CKL as exhaustive.
- `targeted_gap_expansion` keeps the CKL context and asks the model to address
  only the listed missing dimensions.
- `broad_knowledge_expansion` treats local context as partial background and
  requires explicit uncertainty and evidence distinctions.

Explicit requests for scholarly disagreement, archaeology, manuscript evidence,
Second Temple interpretation, translation analysis, ancient legal comparison,
reception history, or similar research can override a high coverage estimate.
This is a routing heuristic, not a mathematically exact percentage of available
scholarship.

Model-knowledge expansion is available by default, subject to
`canonical_library.fallback_to_model` and the knowledge-expansion settings.
External retrieval is provider-neutral and disabled by default; no web or
network call is made unless a caller supplies a provider and enables
`allow_external_retrieval`. A missing or failing provider degrades to the local
or model path. Strict CKL mode blocks both expansion sources and records the
block in debug metadata. These semantics also work with Ollama, local
OpenAI-compatible servers, remote models, and offline runs.
