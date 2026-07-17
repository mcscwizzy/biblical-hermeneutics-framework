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

## Code style

Python follows PEP 8 with a 88-column line limit (the common `black` default;
PEP 8 explicitly permits longer lines than 79). To check before opening a PR:

```bash
pip install pycodestyle
pycodestyle --max-line-length=88 tools/*.py
```
