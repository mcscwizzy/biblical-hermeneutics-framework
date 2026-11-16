# ED-6 Baseline

## Repository and merge state

- Fetched `origin/master` on 2026-11-14: `f7851bf5da777924b5dd48bc547e0a73685c708c`.
- PR [#80 — ED-5 discovery experience](https://github.com/mcscwizzy/biblical-hermeneutics-framework/pull/80)
  is merged at `6e33d16e891614f6527fd9ede943cb1a7c5c1913`.
- PR [#81 — ED-5 mobile acceptance](https://github.com/mcscwizzy/biblical-hermeneutics-framework/pull/81)
  is merged at the fetched baseline commit above.
- The requested branch, `feat/ed6-reader-discovery-pilot`, was created from
  that commit with a clean worktree.

## Current CKL and passage census

These values were reproduced from the current checkout, not copied forward as
assumptions. Generated audit output was written under `/tmp/ed6-baseline-ed1a/`.

| Measure | Current baseline |
|---|---:|
| CKL objects / valid objects | 687 / 687 |
| Claims | 2,329 |
| Typed evidence records | 1,408 |
| Interpretive notes | 3,691 |
| Canonical chapters / unmapped projected identities | 1,189 / 0 |
| Passage-specific / contextual-only chapters | 1,090 / 56 |
| Entity-only / no-eligible-material chapters | 2 / 41 |
| Incomplete or unknown chapter classifications | 0 |
| Strict CKL errors / inherited warnings | 0 / 14 |
| Source identities / source-record occurrences | 2,897 / 5,348 |
| Child source references resolved / unresolved | 17,721 / 0 |
| ED-1A sample checks / targeted service builds | 19 / 16 |

The current ED-1A CKL inventory fingerprint is
`f5a1dfffe97634dd1014e531a5a1cf1e1b2d15c65b1d96d656dde8aca4ec0b29`.
The no-eligible chapter set still includes 1 Kings 2, and ED-5's scripted
negative case reports a completed lookup with zero eligible CKL items.

## Protected relationships and human review

The read-only NE-9C/NE-10 compatibility validator reports 3,925 reviewed
relationship identities, 433 runtime curation records (431 object records and
2 evidence records), 44 verified bridges, and 7 held bridge candidates. The
protected NE-10 bridge registry hash is
`8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b`; the
held-candidate registry hash is
`15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3`.

The ED-3 human-review queue contains 99 records. The live ED-4 workbench
reported 0 review events and 99 pending records; it recorded no approval or
decision. ED-5's reviewer pilot index has 12 packets. The `.bhf-data/ed6-reader-pilot/`
input directory was absent at baseline, so there are no authorized ED-6 reader
records to import or analyze.

The frozen NE-9C historical CKL fingerprint does not match the post-ED-2 CKL
inventory. The current-state compatibility validator passes while preserving
that documented historical difference. ED-6 does not refresh the checkpoint
or alter protected curation decisions.

## Reader baseline

ED-5 adds a completed-empty coverage notice, a plain-language terminology
guide, a 12-case scripted journey evaluator, review-history portability, and a
12-packet reviewer pilot index. The 12 scripted cases pass in the current
checkout; all 10 cases with projected CKL records match their exact stable
IDs. This is deterministic projection and retrieval evidence, not participant
comprehension, satisfaction, or click-count data.

The existing browser suite covers the exact Genesis 12 source disclosure,
Genesis draft-review notice, 390px mobile and keyboard disclosure operation,
1 Kings 2 completed-empty state, Jonah-to-Matthew direction and return, Psalm
145:13 provenance, and 1 Corinthians 11:3 lexical uncertainty. Psalm 82 and
Deuteronomy 32 passage-specific provenance also have existing reader journey
coverage. ED-6 reruns a bounded current Chromium subset; inherited test results
are not counted as new ED-6 runs.

The browser's broad Canonical Knowledge Library search and ED-5's targeted
scripted retrieval evaluator use different search paths. In the current
Chromium check, the evaluator's original question, “What if our heart condemns
us?”, does not surface 1 John in the browser result list. The ED-6 live task
therefore uses the passage-grounded natural-language question, “What does 1
John 3:19–24 say about a condemning heart?”, which the current browser search
returns under 1 John. This task wording adjustment is documented readiness
work, not participant feedback and not a production search change.

## Reproduction commands

Run from the repository root:

```bash
.venv/bin/python tools/ckl_validate.py --root framework/canonical_library
.venv/bin/python tools/validate_ne9c_current_compatibility.py
.venv/bin/python scripts/audit_ed1a_evidence_depth.py \
  --output-dir /tmp/ed6-baseline-ed1a --study-db .bhf-data/study.sqlite
.venv/bin/python scripts/ed5_reader_evaluation.py \
  --output /tmp/ed6-ed5-reader-evaluation.json
.venv/bin/python tools/ed4_review_workbench.py status
```

The audit reads the local study database if present; it does not place study
data or generated reports in Git.
