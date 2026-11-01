# Scripture Trails Plugin Design

## Intent

Build a portable, skills-only Scripture Trails plugin from approved BHF framework modules. Users receive a conversational Bible study companion with answer-first responses and evidence-ranked optional rabbit trails. The build repository supplies methodology; the installed plugin must not need BHF, an API, a server, credentials, a database, or network access.

## Goals and boundaries

- Keep the seven required BHF core modules in the package on every build.
- Select extra genre, context, language, and book guidance in an explicit YAML configuration.
- Generate separate Markdown references and provenance from BHF modules using the existing module parser and dependency resolver.
- Validate generated resources, the portable plugin manifest, skill frontmatter, relative references, and ZIP contents deterministically.
- Keep CKL, Narrative Explorer, Tyndale data, translation datasets, application behavior, deployments, and APIs out of scope.
- Keep model behavior evaluations as manual cases; deterministic tests validate packaging and instructions only.

## Approaches

1. **Recommended: modular generated references.** Reuse `tools/bhf_lib.py`, resolve a curated module set, and emit smaller themed references next to one concise skill. This meets the package boundary while keeping methodology traceable.
2. **Single generated prompt.** Reuse `compose.py` to flatten all selected modules into one skill. This reuses existing output but produces a large, rigid prompt and weakens the requested modular reference behavior.
3. **Hand-copy framework guidance.** Author plugin methodology independently. This would make source drift and provenance harder to detect and would duplicate reviewed material.

The task brief selects the modular generated-reference approach and a portable root `plugin.json` with `skills/` discovery as described in the current OpenAI plugin documentation.

## Architecture

`tools/build_scripture_trails.py` reads `plugins/scripture-trails/config/module-selection.yml`, loads modules through `bhf_lib`, validates the selected dependency closure, adapts internal module references to titles, and writes generated references plus a source manifest. The skill references those resources conditionally. An allowlisted, deterministic ZIP writer creates the distributable archive, SHA-256 file, and external build manifest. `--check` compares regenerated content with committed resources and reports affected references.

## Conversation and trail behavior

The skill answers the user's question first, applies observation, interpretation, and application distinctly, uses historical and genre guidance as relevant, and offers one to three useful optional connections only when evidence supports them. It distinguishes quotations, citations, allusions, patterns, themes, and cultural parallels; ranks connection confidence internally as Very High, High, Moderate, or Low; and never treats shared vocabulary as sufficient evidence. Follow-up turns preserve the active passage and selected trail.

## Constraints and open implementation calls

- BHF content is CC BY 4.0; the plugin will retain attribution and a license notice.
- The ZIP contains instructions, references, provenance, and license text only. Developer configuration and acceptance fixtures remain outside it.
- The portable manifest uses a stable kebab-case plugin name and root skill discovery. No MCP or authentication configuration is included.
- Public publication still requires OpenAI's package checks, verified publisher identity, any listing metadata/assets required at submission, and review. This task stops at a structurally validated ZIP and local installation guidance.
- Selection of concrete context, genre, and book modules is the implementation call recorded in the plugin configuration.
