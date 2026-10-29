# NE-11G — Reader Governance Disclosure Correction

## Scope and baseline

This change corrects the compact Companion card disclosure gap recorded in
`docs/narrative-explorer/ne11f/05-governance-and-integrity.md` and
`docs/narrative-explorer/ne11f/07-final-production-release-decision.md`, read
from `release/ne11f-final-verification` at
`149b5200777e1a80652fc95341cd5f56b3638d8c`. Those reports were not
cherry-picked. Work started from fetched `origin/master` at
`d0a7b7cafb3b36f3ac461ecbc425181369374958`.

No CKL research, object, curation, source lock, provenance, or production
deployment was changed.

## Original disclosure gap

The Companion canonical-summary projection exposed each record's ID, title,
type, and summary, but omitted `content_status`, `review_status`, and
`human_review_required`. Its compact card therefore showed the five Genesis
records without their editorial review state. Narrative Explorer projections
already carried governance state in relevant detail views; the compact
Companion summary did not.

This is an editorial-state disclosure. Draft status does not claim that the
underlying Scripture or its cited sources are unreliable.

## Changed API and card behavior

The Companion API now passes the three CKL governance fields through unchanged
on canonical summaries. Missing metadata is serialized as `null`; it is never
filled with `approved`. Existing title, summary, type/evidence classification,
source handling, and card actions remain intact.

A card shows **“Draft evidence — awaiting human review”** only when the record
has all three of these values:

- `content_status = draft`
- `review_status = in_review`
- `human_review_required = true`

The notice is readable card text and is also included in the card's accessible
name. The rule uses record state and does not depend on a Genesis ID. The
existing metadata presentation is retained, with sentence casing for this
notice.

### Before and after

Before, the API summary and card contained only:

```json
{
  "id": "<CKL record>",
  "title": "<existing title>",
  "type": "<existing type>",
  "summary": "<existing summary>"
}
```

After, the API carries the actual editorial state:

```json
{
  "id": "<CKL record>",
  "title": "<existing title>",
  "type": "<existing type>",
  "summary": "<existing summary>",
  "content_status": "draft",
  "review_status": "in_review",
  "human_review_required": true
}
```

The card keeps its same title, type, and summary, then adds:

> Draft evidence — awaiting human review

Its accessible name includes the same notice after the existing “View …
details” label.

## Governance recommendation

These are four separate decisions:

1. **Validated CKL evidence:** evidence that passes the schema, evidence,
   source, manifest, and integrity gates is validated with respect to those
   gates. Passing them is not a human editorial review.
2. **Awaiting human editorial review:** the record's actual state is
   `draft` / `in_review` / `human_review_required: true`. The five protected
   Genesis objects remain in this state.
3. **Permission to display draft evidence with disclosure:** this is a reader
   policy decision separate from both validation and review. This code change
   makes the state visible; it does not grant that permission or promote a
   draft.
4. **Formal human review and publication approval:** this requires an actual
   human review and CKL metadata that records the resulting decision. No
   generator identity, reviewer, or approval is inferred here.

**Recommended default:** expose the record's genuine editorial status wherever
the record is shown. If governance metadata is absent, make no approval claim.
Permit draft display only under an explicit governance policy requiring the
disclosure, and keep publication approval tied to recorded human review. This
disclosure correction does not promote any of the five drafts.

## Protected CKL and identity check

The CKL inventory fingerprint was `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`
before and after this application change; the inventory remains 687 objects.
The five hash-pinned Genesis exceptions still match the NE-11F values:

| CKL object | SHA-256 |
|---|---|
| `genesis-flood-postflood-context` | `d22862694a5b6a9799074703a36d4a572d14731a51ab4e8ed70a574734e7c44b` |
| `genesis-nations-babel-context` | `ee22202a8bfc1be62469d1e710ae2383149ecad445dc4d721008a18d42a22f23` |
| `genesis-abraham-call-covenant-context` | `02aeceb005539c7175afa4631cffc808ef377b73185b760f582e48119fb38aa9` |
| `genesis-abraham-late-cycle-context` | `95413e73224c3242589c0d9891444f3c7b438bd562d70cdb6ae239d7fd5d7408` |
| `genesis-isaac-jacob-transition-context` | `22f8d2d0b6c7625b1267193ab1fb4e500981ad95713f702b83466b031bcb28cb` |

All five remain `content_status: draft`, `review_status: in_review`,
`human_review_required: true`, `generated_by: []`, and `reviewed_by: []`, as
recorded in NE-11F.

Git comparison against `origin/master` found no changes to these five object
files or to either the NE-9C and NE-10 curation trees. The NE-11F inventory
records 3,925 reviewed NE-9C dispositions and 44 verified / 7 held NE-10
bridges; these identities remain byte-for-byte at the fetched baseline. No
generator metadata, review fields, source locks, or historical transaction
records were edited.

## Vercel production-event investigation

The investigation was read-only. It inspected the two deployment records, the
Vercel project details, and Vercel user activity for October 28, 2026 around
22:19:15 UTC. The two activity entries are separate:

| Target | Deployment | Source | Activity record |
|---|---|---|---|
| Production | `dpl_GML45cp2x7Rk3XTC9cMyH8rZU9nm` | `master`, SHA `d0a7b7cafb3b36f3ac461ecbc425181369374958` | `uev_OeTfSgIVO7bPfELXMrYwLQKZ`, 22:19:15.034 UTC; production deployment event, with no `via` initiator field |
| Preview | `dpl_4QyBXYpQZMpReUjfMRaayd98fPsf` | `release/ne11f-final-verification`, same SHA | `uev_mnLO9ytP18Pyja0uiYPz6UAm`, 22:19:15.910 UTC; event explicitly says “via ChatGPT” |

The production deployment metadata shows `source: git`, `target: production`,
and branch `master`; the activity event records the account actor but does not
identify an initiating mechanism equivalent to the Preview's `via: ChatGPT`
field. The Vercel project-details response did not expose Git deployment trigger
settings. The fetched source's `vercel.json` has
`git.deploymentEnabled.master: false`, but that repository setting does not
establish the production event's cause or the live project setting. Read-only
trace lookups for the two activity request IDs returned `trace_not_found`.

**Finding:** the available project details, deployment metadata, and approved
activity evidence do not establish what triggered the Production deployment.
The neighboring timestamps are recorded separately and are not used to infer
causation. No deployment, promotion, rollback, alias, feature-flag, or project
configuration action was performed.

## Verification results

| Check | Result |
|---|---|
| `npm test` | 14 frontend test files passed; 0 failed, 0 skipped. Includes `tests/frontend/companion-discoveries.test.js` (evidence/source and Jonah handoff cases) and `tests/frontend/resource-router.test.js` (card and route behavior). |
| `pytest tests/test_companion_context.py -q` | 24 passed; 8 skipped; 3 subtests passed; 0 failed |
| `pytest tests/canonical_library/test_genesis_exodus_records.py tests/canonical_library/test_jonah_record.py -q` | 16 passed; 132 subtests passed; 0 failed |
| `pytest tests/gui/ne11g/test_governance_disclosure_mobile.py -q -rs` | 2 local Chromium viewport cases passed (320px and 390px); 0 failed |
| `tests/gui/ne11d1/test_real_ckl_handoff.py::test_real_ckl_jonah_and_matthew_handoffs_preserve_direction_and_return` and `tests/gui/ne11d1/test_real_ckl_handoff.py::test_real_ckl_genesis_john_handoff_is_unchanged` | 2 exact Jonah/Genesis browser regressions passed; 0 failed |
| CKL inventory and protected object comparison | Fingerprint unchanged; 5/5 object hashes match; NE-9C and NE-10 trees unchanged |
| `git diff --check` | Passed |

## Outstanding acceptance

- **Live Vercel browser verification:** **NOT EXECUTED.** No deployment was
  created or changed for this branch. The local Chromium tests above exercised
  the rendered cards at 320px and 390px.
- **Spoken screen-reader acceptance:** **NOT EXECUTED.** Automated coverage
  checks the readable notice and accessible card name; no manual spoken session
  was performed.
- **Performance acceptance:** **NOT EXECUTED.** No live browser latency,
  cache, or operator performance assessment was performed.

The outstanding live browser, spoken accessibility, and performance decisions
remain release acceptance items. This branch is ready for manual review only;
it is not a production release decision.
