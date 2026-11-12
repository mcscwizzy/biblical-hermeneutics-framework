# ED-5 repository and research baseline

## Branch and commit

- `origin/master` was fetched on 2026-11-11 at
  `528b1593021f24fe98ff60d1533c7720f5755cd0` (ED-4 merge PR #79).
- ED-4 is merged. A clean worktree was used to create
  `feat/ed5-discovery-experience` from that commit.
- No CKL or curation files were modified for ED-5.

## Reproduced CKL and chapter inventory

The read-only ED-1A audit ran against the current branch base. Its files are in
`/tmp/ed5-baseline-ed1a/`.

| Measure | Result |
|---|---:|
| CKL objects / manifest objects | 687 / 687 |
| Claims | 2,329 |
| Typed evidence items | 1,408 |
| Interpretive notes | 3,691 |
| Child source references / unresolved | 17,721 / 0 |
| Source identities / bibliography occurrences | 2,897 / 5,348 |
| CKL inventory fingerprint | `f5a1dfffe97634dd1014e531a5a1cf1e1b2d15c65b1d96d656dde8aca4ec0b29` |
| Canonical chapter rows | 1,189 / 1,189 |
| Passage-specific / contextual-only / entity-only | 1,090 / 56 / 2 |
| No eligible / incomplete-or-unknown | 41 / 0 |
| Unmapped projected record identities | 0 |
| Strict CKL validation | 0 errors, 14 inherited warnings |

The CKL inventory fingerprint and the NE-9C frozen object-tree fingerprint
measure different inputs and are not interchangeable. The current-state
NE-9C/NE-10 compatibility check passes; its historical fingerprint comparison
is intentionally false. The 14 strict warnings concern inherited incomplete
section-status metadata. Deep quality signals are heuristic, not adjudications.

## Governance and review baseline

- ED-3 queue: 99 distinct records; all reviewer identity, date, decision,
  rationale, and correction fields remain blank.
- Existing real local review ledger: absent; ED-5 did not create it.
- Current compatibility: 3,925 reviewed relationship identities, 433 accepted
  curation identities (431 object and 2 evidence), 44 verified bridges, and 7
  held candidates.
- Protected NE-10 hashes: bridge registry
  `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b`;
  held registry
  `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3`.

## Reader baseline

ED-4 had already verified selected reader, source, history, and responsive
journeys, including six overview categories, source disclosures, a 390 CSS-px
Chromium emulation, 320px source wrapping, and focus restoration. ED-5 source
inspection found one bounded discovery gap: a completed empty CKL result had
only category-level “No linked records returned” wording and no passage-level
coverage explanation or next step. Current interactive browser execution was
unavailable in this environment; inherited browser evidence is identified as
such in [usability baseline](usability-baseline.md).

## Reproduction

```bash
python3 scripts/audit_ed1a_evidence_depth.py \
  --output-dir /tmp/ed5-baseline-ed1a \
  --study-db .bhf-data/study.sqlite
.venv/bin/python tools/validate.py framework/
.venv/bin/python tools/validate_ne9c_current_compatibility.py
.venv/bin/python tools/ed4_review_workbench.py status
```
