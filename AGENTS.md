# BHF repository guidance

BHF is a Bible study workspace whose research experience is Narrative Explorer.
The Canonical Knowledge Library (CKL) is the authoritative, reviewed research
source. Application routes expose deterministic Scripture, passage evidence,
maps, archaeology, language tools, and private study features. Ask BHF hands the
selected passage and question to the configured external assistant.

## Safe repository work

- Read the relevant implementation, tests, and documentation before changing a
  behavior or data format. Follow consumers through imports, path constants,
  dynamic loading, packaging, and deployment configuration.
- Keep CKL JSON objects, source identities, evidence, source locks, schema,
  manifests, curations, and provenance aligned. Run the CKL integrity checks
  after any authorized CKL change. Do not revise scholarly content as a side
  effect of application or maintenance work.
- NE-9C curation records and NE-10 passage bridge records are read-only inputs
  to the Narrative Explorer. Do not alter them unless the task explicitly asks
  for reviewed research curation.
- Tyndale Open Study Notes is an active, separately attributed data service.
  `framework.commentary` includes its schema, importer, repository, service,
  and build hook. Do not remove these when working on retired BHF Commentary.
- Generated BHF Commentary was retired in NE7R3. Its old generation payloads
  and tools are not current runtime inputs. The retired `/api/bhf-commentary`
  routes intentionally return HTTP 410; preserve that compatibility behavior.
- Retain licenses, attribution, immutable source references, and verified
  provenance. Where a dependency or retention claim cannot be established,
  leave the artifact in place and document the uncertainty.
- Do not weaken the active `Validate` workflow, package checks, source
  integrity checks, CKL gates, or Narrative Explorer regression coverage.
- Avoid adding generated databases, local study data, temporary research
  output, or private records to Git. Use the repository ignore rules and check
  `git status` before committing.

## Development and verification

- Create a focused branch for repository changes and keep commits logically
  grouped.
- Run `python tools/validate.py framework/` for framework module changes.
- Run targeted Python and frontend tests for changed behavior. For CKL,
  Narrative Explorer, packaging, or routing changes, run the corresponding
  integrity and route tests as well.
- Validate Markdown links and documented commands when editing documentation.
- Before completion, review `git diff --check`, the full diff, generated-file
  status, and the final commit state. Report tests that could not run and
  pre-existing failures accurately.

The project maps and workflows are documented in [README.md](README.md) and
the [documentation index](docs/README.md).
