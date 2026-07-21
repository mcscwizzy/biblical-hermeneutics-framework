# BHF Tooling

Light, optional Python tooling (MIT-licensed). The Markdown modules are the
product; these scripts just validate and assemble them. Python 3.9+.

```bash
pip install -r tools/requirements.txt
```

On macOS/Linux with a system-managed Python you may hit a PEP 668
"externally-managed-environment" error. Use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

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
- `ckl_migrate.py` normalizes legacy object JSON into the current schema shape.

Run these from the repository root so relative paths resolve correctly.

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
