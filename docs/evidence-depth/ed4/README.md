# ED-4 — Research Retrieval, Scholarly Review Operations, and Reader Quality

ED-4 makes BHF's existing research easier to find, verify, and maintain. It
does not open a new evidence-generation wave. Retrieval uses the existing
deterministic CKL index; the human-review workflow is local to repository
maintainers and never converts machine validation into scholarly approval.

## Status

The work is on `feat/ed4-research-quality-and-review`, based on the verified
ED-3 merge at `31832793a155b16b6d694b1e84202bac1ee47c38`. No merge or deployment
is part of the assignment. Phase status, unresolved issues, and validated
commit SHAs are in [progress.json](progress.json).

## Reports

- [Design](design.md) and [execution plan](execution-plan.md)
- [Baseline and repository inventory](baseline.md)
- [Retrieval cause analysis](retrieval-analysis.md)
- [Retrieval before/after evaluation](retrieval-before-after.md)
- [Progress ledger](progress.json)

Phase reports will be linked here as their investigations and validation
complete.

## Authority and review status

The ED-3 queue remains the immutable input for the 99 pending ED-2 records.
Every review decision must be entered by an identifiable human reviewer with
their own rationale and source inspection history. BHF validation and this
program's machine checks cannot approve a record. The human review ledger is
local, append-only by default, and ignored by Git; no human decision is recorded
by ED-4 itself.

The guiding order remains: context before tradition, original audience before
modern application, and evidence before interpretation.
