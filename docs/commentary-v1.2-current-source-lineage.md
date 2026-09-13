# Commentary v1.2 current source lineage

The current deterministic source contract is frozen at
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-current-source-lineage-v2/`.
It is a source/ancestry/provenance baseline, not a replacement for historical
renderer prose or raw responses.

It supersedes these immutable historical observations:

- `renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31`
- `commentary-v1.2-scale-pilot-922472547555015a3ced`

Supersession is required because current deterministic semantics include
evidence applicability scope (`5c00d961809dbdfe652af0d5908d53831a05c8ca`)
and the ASV passage-boundary repair
(`3522c0dbf748e2edca2f2ce68d52dcf3ea584833`). Historical namespaces must
never be edited to match this baseline.

The baseline preserves the same 21 qualification and 75 scale-pilot chapter
populations. It freezes reconstructed packets, projections, ancestry envelopes,
provenance bindings, prompts, local audits, and a per-chapter migration receipt.
`migration-report.json` classifies every old-to-current difference. No renderer
or external provider is used to create it.

Create a new baseline only as an explicit operator action:

```bash
.venv/bin/python tools/commentary_v12_rebaseline_lineage.py prepare
```

Verify an existing baseline without writing it:

```bash
.venv/bin/python tools/commentary_v12_rebaseline_lineage.py verify
```

Verification reconstructs the complete 96-chapter source contract and fails if
any current deterministic identity differs from the frozen baseline. It never
updates expected hashes automatically.
