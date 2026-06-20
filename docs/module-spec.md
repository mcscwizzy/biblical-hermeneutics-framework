# Module Specification (authoritative)

This is the **single source of truth** for what a BHF module must look like.
`tools/validate.py` enforces this spec; CI runs it on every pull request.
Changes to this spec are versioned and require maintainer review
(see [GOVERNANCE.md](../GOVERNANCE.md#3-review-process)).

A module is a single Markdown file: **YAML frontmatter** followed by a
**fixed-section body**.

## 1. Frontmatter

Every module begins with a YAML frontmatter block delimited by `---`.

```yaml
---
id: genre.epistle              # REQUIRED. "<type>.<slug>", globally unique.
title: Epistle Genre Module    # REQUIRED. Human-readable.
type: genre                    # REQUIRED. One of the enum below.
version: 0.1.0                 # REQUIRED. SemVer (per-module).
status: stable                 # REQUIRED. draft | review | stable | deprecated
order: 100                     # OPTIONAL. Within-type sequencing hint (lower = earlier).
tokens: 450                    # REQUIRED. Approximate token cost (integer).
requires: [core.core-framework]            # OPTIONAL. Hard deps, auto-loaded.
recommends: [context.roman-empire]      # OPTIONAL. Suggested companions.
tags: [epistle, letters]       # OPTIONAL. List of strings.
sources_required: true         # OPTIONAL (default true). Claims need citations.
maintainers: ["@handle"]       # OPTIONAL. List of GitHub handles.
license: CC-BY-4.0             # OPTIONAL (default CC-BY-4.0).
---
```

### Field rules

| Field | Required | Rule |
|-------|----------|------|
| `id` | yes | Matches `^(core|genre|book|context|language|profile)\.[a-z0-9-]+$`. Must equal `<type>.<slug>`. Unique across the repo. |
| `title` | yes | Non-empty string. |
| `type` | yes | One of: `core`, `genre`, `book`, `context`, `language`, `profile`. Must be the prefix of `id`. |
| `version` | yes | SemVer `MAJOR.MINOR.PATCH`. |
| `status` | yes | One of: `draft`, `review`, `stable`, `deprecated`. |
| `order` | no | Integer sequencing hint (default `100`); composition orders modules by `(type, order, id)`, so dependencies always precede dependents. Used mainly to sequence the `core` modules into a hermeneutical workflow. |
| `tokens` | yes | Positive integer; approximate, used for budget-aware composition. Should be within ~25% of the validator's measured estimate. |
| `requires` | no | List of existing module ids. Must resolve; no cycles. |
| `recommends` | no | List of existing module ids. Must resolve. |
| `tags` | no | List of strings. |
| `sources_required` | no | Boolean, default `true`. |
| `maintainers` | no | List of strings. |
| `license` | no | String, default `CC-BY-4.0`. |

## 2. Body — required sections

The body must contain these level-2 headings, in this order:

1. `## Purpose` — one paragraph: what this module makes the AI *do*.
2. `## When to apply` — the signals/triggers for using it.
3. `## Interpretive moves` — the actual guidance, as a numbered or bulleted list.
4. `## Common errors to avoid` — anti-patterns, including doctrinal overreach.
5. `## Handling uncertainty` — how to label and qualify claims for this topic.
6. `## Cross-references` — links to related modules using `[[id]]` syntax.

### Book modules use a different section contract

Book modules are **hermeneutic profiles**, not commentaries. They do not use the
`Interpretive moves` / `Common errors to avoid` sections above. Instead they must
contain these level-2 headings, in this order:

1. `## Purpose` — how this module helps the AI approach this book.
2. `## When to apply` — when to load it (on top of Core, Genre, Context, Language).
3. `## Genre signals` — the dominant genre(s) and where each appears.
4. `## Historical anchors` — the relevant worlds, **referencing** Context modules.
5. `## Literary features` — what to look for (do not claim every feature exists).
6. `## Key interpretive questions` — questions to ask; **do not answer them**.
7. `## Common misreadings` — frequent method mistakes, described neutrally.
8. `## Handling uncertainty` — where scholarship is divided.
9. `## Cross-references` — `[[id]]` links to Core, Genre, Context, Language modules.

Book modules assume the earlier layers are already loaded and must not duplicate
their content; they specialize for the specific book.

## 3. Cross-reference syntax

Inside the body, reference other modules with `[[id]]`, e.g. `[[language.greek]]`.
The validator checks that every `[[id]]` resolves to an existing module.

## 4. Templates

Each category folder contains a `_TEMPLATE.md`. Files beginning with `_` are
templates: they are **excluded** from validation-as-modules and from
composition. Copy a template to start a new module.

## 5. What validation checks

`python tools/validate.py framework/` verifies: frontmatter parses and conforms
to the field rules; `id` matches filename-derived `type`; all required sections
are present and ordered; `requires`/`recommends`/`[[id]]` references resolve;
the dependency graph is acyclic; and the declared `tokens` is plausible.
