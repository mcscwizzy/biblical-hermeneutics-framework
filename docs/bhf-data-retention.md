# BHF data retention

This policy distinguishes reviewed research source from generated application
data and historical development output. CKL is the authoritative research
source; Narrative Explorer uses its reviewed content and read-only curation
registries.

## Retained source and provenance

- Keep CKL objects, source records, claims, evidence, schema, manifest,
  fingerprints, source locks, and source attribution. The current validated
  baseline is 687 objects unless a later authoritative master establishes and
  validates a different inventory.
- Keep NE-9C relationship curation and NE-10 passage bridge registries,
  accepted records, held-candidate data, acceptance reports, and provenance.
  These are source inputs, not disposable generated content.
- Keep the Genesis G0 through G6C evidence-expansion workspaces and associated
  attestations. Their ledgers and reports document evidence review, protected
  object identity, source ownership, uncertainty, and acceptance decisions.
- Keep the exact Sol renderer qualification `chatgpt-handoff` subtree because
  `.github/workflows/export-sol-qualification-artifact.yml` packages those
  inputs. Remote branch state was not verifiable during this cleanup, so the
  workflow and subtree remain an explicit unresolved retention dependency.
- Keep the locked CKL geography pilot source-lock file and frozen candidate
  queue. The production-apply design binds those exact bytes as inputs for
  replaying reviewed candidate decisions. The queue's historical Commentary
  preview field is not runtime data and is no longer emitted by the maintained
  dry-run tool.
- Keep Bible translation JSON, packaged lexical data, lexical schema,
  licenses, attribution, pinned revisions, and importer/build resources.
- Keep the Tyndale Open Study Notes service and its source attribution. Its
  database is generated from the checksum-pinned upstream archive for Docker
  and Vercel deployment; private/local copies belong in ignored state.
- Keep release tags and immutable historical refs that establish provenance
  or allow old release verification. Git history is the archive for retired
  generated Commentary implementation and artifacts.

## `.bhf-data` policy after NE7R3

Generated BHF Commentary was retired in NE7R3. Its runtime release trees,
candidate batches, prompts, generated prose, intermediate ledgers, exports,
and retired pipeline reports are no longer current runtime inputs and have
been removed from the working tree. The current repository retains the CKL
Genesis evidence and unresolved Sol handoff described above. The local
`.bhf-data/` directory is excluded from Docker and Vercel bundles.

Future additions to `.bhf-data` must be reviewed as individual provenance or
runtime inputs. Do not commit local databases, generated test outputs,
temporary research, duplicate snapshots, or new Commentary generation output.
The `.gitignore` allowlist names the retained historical evidence trees and
handoff path; update it only when a reviewed source-retention decision requires
another input.

The Narrative Explorer relationship inventory at
`docs/narrative-explorer/connection-audit/03-relationship-inventory.csv` was
removed after deterministic regeneration from CKL. Recreate it with:

```bash
python scripts/audit_ckl_connection_coverage.py \
  --output /tmp/ne9a-relationship-inventory.csv
```

The exporter reads current CKL JSON objects and writes the CSV with a stable
row order. Verify it with:

```bash
sha256sum /tmp/ne9a-relationship-inventory.csv
wc -l /tmp/ne9a-relationship-inventory.csv
python -m framework.canonical_library verify-db --database .bhf/ckl.sqlite
```

For the source baseline used in this cleanup, the CSV had 53,097 rows plus its
header and SHA-256
`b03b5ce267e415b997e6d1cfbe8fe69049731b3a4b10262f1e77d8e395aedef4`. The
CKL contained 687 objects with inventory fingerprint
`90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`, source
manifest SHA-256
`334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4`, and
CKL object-tree fingerprint
`e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`.

## Historical and generated artifacts

Retired Commentary releases and generation experiments are preserved through
their immutable Git history and release tags, not copied into a new tracked
archive directory. Their old validation results do not make the generator a
current runtime dependency. The 410 compatibility routes and retirement
regression tests remain active.

The local `.bhf/` directory contains generated databases and private or
installation-specific state. Do not commit it. Rebuild only the exact database
that is stale or missing, and preserve any private study records before
removing local state.

See [the repository cleanup report](maintenance/repository-cleanup-report.md)
for the file and byte totals and the retained-artifact review.
