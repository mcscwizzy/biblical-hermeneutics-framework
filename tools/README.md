# BHF Tooling

Python 3.9+ utilities for framework validation and composition, CKL authoring
and audits, lexical imports, storage benchmarks, and local evaluation. Run them
from the repository root so relative paths resolve consistently.

Use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r tools/requirements.txt
```

See the [local build guide](../docs/local-development.md) for the complete
application setup and test workflow.

## `validate.py`

Validates modules against [`../docs/module-spec.md`](../docs/module-spec.md):
frontmatter schema, id/type/folder agreement, required sections and ordering,
dependency + cross-reference (`[[id]]`) resolution, acyclicity, and token-estimate
plausibility. Exits non-zero on any problem (used by CI).

```bash
python tools/validate.py framework/
```

## `compose.py`

Resolves a set of modules (pulling in transitive `requires`, ordering core
first) into one prompt you can paste into any model.

```bash
# Ad-hoc selection
python tools/compose.py --modules genre.epistle,book.romans

# A named profile from profiles/profiles.yml
python tools/compose.py --profile standard

# Regenerate the committed profile artifact
python tools/compose.py --profile standard --write
```

## `bhf_lib.py`

Shared loading/parsing/dependency-resolution helpers imported by both scripts.

## CKL authoring tools

The Canonical Knowledge Library has its own small command set in `tools/`:

- `ckl_create.py` generates a normalized object template and can write it to the
  correct `framework/canonical_library/objects/...` path.
- `ckl_validate.py` validates either one object file or the full CKL library.
- `ckl_manifest.py` rebuilds `manifest.json` from the current object inventory.
- `ckl_report.py` prints a status snapshot with counts and validation issues.
  Add `--deep` for the Phase 1 quality report (field coverage, depth averages,
  graph integrity, governance, duplicate/template signals, retrieval gaps, and
  source integrity). Add `--json` for machine-readable output and `--output`
  to persist either format.
- `ckl_expansion_backlog.py` ranks people, places, and things that need
  expansion or review attention.
- `ckl_graph_audit.py` reports relationship graph coverage, including orphaned
  objects, unknown targets, and missing reverse-edge suggestions.
- `ckl_migrate.py` normalizes legacy object JSON into the current schema shape.

Run these from the repository root so relative paths resolve correctly.

```bash
python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep

python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep \
  --json \
  --output docs/ckl-quality-report.json
```

## `import_lexicons.py`, `lexicon_onboard.py`, and `lexicon_smoke.py`

`import_lexicons.py` imports inspected local lexical data into the generated CKL
SQLite database. It accepts either normalized JSON fixtures or a local source
manifest. It does not download source repositories or parse raw upstream files
during application startup.

```bash
python -m framework.canonical_library build-db
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --normalized-json tests/fixtures/lexicon_phase1.json \
  --rebuild
```

For local source manifests:

```bash
python tools/import_lexicons.py \
  --output .bhf/ckl.sqlite \
  --source-manifest data_sources/lexicons/lexicon-sources.json \
  --rebuild
```

`lexicon_onboard.py` validates the source manifest and checks runtime coverage
for key word-study fixtures.

```bash
python tools/lexicon_onboard.py \
  --manifest data_sources/lexicons/lexicon-sources.json \
  --database .bhf/ckl.sqlite
```

`lexicon_smoke.py` checks the actual deterministic Word Study action path used
by the reader context menu.

```bash
python tools/lexicon_smoke.py \
  --database .bhf/ckl.sqlite \
  --coverage-json examples/lexicon-coverage.example.json
```

Raw source checkouts for future Open Scriptures, morphhb, MorphGNT, and
Abbott-Smith importers should live under ignored `data_sources/lexicons/`
directories, with licenses and pinned revisions documented in
[`../docs/lexicon-sources.md`](../docs/lexicon-sources.md).

## Code style

Python follows PEP 8 with a 88-column line limit (the common `black` default;
PEP 8 explicitly permits longer lines than 79). To check before opening a PR:

```bash
pip install pycodestyle
pycodestyle --max-line-length=88 tools/*.py
```
