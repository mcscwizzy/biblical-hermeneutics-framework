# CKL Explanation Enrichment Progress

This directory tracks the library-wide explanation review requested for the
CKL. The machine-readable inventory in `progress.json` has one row for every
CKL object. Rows remain `pending_review` until all applicable explanatory fields
in that object have been examined. `in_progress` marks a record with a reviewed
and validated field batch but unfinished object-level coverage. It is not
counted as a fully enriched, unchanged, or skipped object.

## Baseline

- Branch: `feat/ckl-explanation-enrichment`
- Base: `origin/master` at `0c9c78afeccc210d7e81f55e32a980c1c4673df4`
- Inventory: 687 objects
- CKL validation: 687 valid, 0 errors, 14 pre-existing warnings
- Protected-field hashes are compared with the fetched base revision.
- ED-7 currently classifies 71 evidence records as withheld from reader
  promotion. Those classifications, NE-9C curations, NE-10 bridges, and held
  candidates remain protected inputs.

## Current checkpoint

At this checkpoint, **0 objects are fully audited**, **1 is in progress**, and
**686 remain pending review**. No object has yet been classified as fully
unchanged or skipped for insufficient support. The partial change count is
four claim rationales in the Genesis object.

Batch 001 expands four existing Genesis 5 claim rationales. It clarifies the
genealogy's repeated pattern, the mortality refrain, Enoch's distinct ending,
and the transition from the creation account toward Noah. The claims, evidence,
IDs, Scripture anchors, sources, statuses, and relationships were not changed.
The Genesis object remains `in_progress` because the rest of its explanatory
fields have not yet been audited.

The Genesis object passes its schema validation, and the full CKL validator
still reports 687 valid objects, no errors, and the same 14 warnings. The CKL
test folder has one collection blocker in `test_evidence_graph_expansion.py`:
the environment lacks the `fastapi` dependency. The NE-9C/NE-10 projection and
curation regression subset passed 73 tests. Remaining validation for this
batch is recorded in `progress.json`.

## Reader reachability

Canonical object detail responses serialize summaries and evidence items.
Retrieval indexes evidence title, description, primary observation, scholarly
interpretation, passage relevance, and confidence rationale. Claim rationales
are serialized in canonical object detail, but the standard canonical browser
modal does not render them, and retrieval indexes claim text rather than
rationale. This batch improves the CKL research layer without claiming direct
reader display. Evidence presentation depends on the Narrative Explorer
evidence packet.

## Resume and validation

Refresh the inventory while preserving existing progress, then validate it:

```sh
python3 tools/ckl_enrichment_progress.py --sync
python3 tools/ckl_enrichment_progress.py --check
```

Validate the full CKL after each content batch:

```sh
python3 tools/ckl_validate.py
```

The next work unit is to finish the Genesis object audit, then continue through
the remaining categories in stable path order. Record field paths, actual
outcomes, validation evidence, and checkpoint commit IDs in `progress.json`.
