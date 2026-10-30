# NE-11I — Exact Canonical Record Source Disclosure

## Scope and decision

This correction adds source and evidence inspection to the existing Study
Companion canonical detail view. It changes no CKL records, retrieval ranking,
source locks, curation, or deployment configuration. The branch was based on
`origin/master` at `45b78d6d`, after review of the [NE-11H governance report](../ne11h/02-governance-accessibility-and-performance.md)
and [final release decision](../ne11h/03-final-release-decision.md).

## Confirmed root cause

The two Canonical API routes have distinct behavior:

- `GET /api/canonical/objects/genesis-abraham-call-covenant-context` is a
  direct lookup by normalized object ID. It returned the exact ID and title,
  `17` source records, and `46` evidence items, with reason `Direct object
  lookup.`
- `GET /api/canonical/search?q=genesis-abraham-call-covenant-context` is
  relevance-ranked discovery. The observed result list contained `abraham`
  first and also contained the requested context object later in the list.
  This search result order is not an exact identity contract.

The Study Companion card already retained the exact context ID and its title,
summary, and draft notice. Its card detail workflow called the direct object
route, but `renderCanonicalDetail()` displayed narrative fields and Scripture
references only; it omitted the API's `detail.sources` and
`detail.evidence_items`. The baseline Genesis 12 browser test confirmed the
gap: the exact detail opened, the passage stayed selected, and the detail had
zero source cards. The separate “Open Canonical Knowledge →” action enters the
general Canonical Browser and remains labeled and routed for that purpose.

## Correction and behavior

The Companion detail path continues to request the selected object's direct
`/api/canonical/objects/{id}` endpoint. It now checks that the response ID
matches the selected ID and renders an error without showing a mismatched
object's sources if that check fails.

The detail view now provides keyboard-operable native disclosure controls for
the selected object's source records and evidence items. Expanding a source
shows its available title, author, publisher, year, locator, type, ID, URL,
notes, and recorded evidence links. Evidence items show their own recorded
source IDs and resolved source titles. These mappings remain attached to the
corresponding evidence item; the UI does not present every object source as
support for every statement. Missing source arrays and partial metadata use
safe empty or field-level fallbacks and do not create attribution or approval
values.

The draft notice remains visible in detail when the record has the existing
`draft` / `in_review` / `human_review_required: true` combination. The
Genesis 12 passage remains selected while disclosures open and close. “Back
to results” restores focus to the exact card that opened the detail. Browser
Back and Forward behavior remains intact, and disclosure toggles do not add
history entries.

## Exact record and source verification

The five governed Genesis object IDs, titles, source counts, and evidence
counts were verified against each object's direct API response and the
Companion UI. The UI's displayed source IDs matched the selected object's
API source IDs in every case. The Genesis 12 source IDs also excluded IDs
belonging only to the separate `abraham` object.

| Passage | Exact CKL object ID | Source records | Evidence items |
|---|---|---:|---:|
| Genesis 6 | `genesis-flood-postflood-context` | 29 | 25 |
| Genesis 10 | `genesis-nations-babel-context` | 20 | 29 |
| Genesis 12 | `genesis-abraham-call-covenant-context` | 17 | 46 |
| Genesis 18 | `genesis-abraham-late-cycle-context` | 11 | 71 |
| Genesis 26 | `genesis-isaac-jacob-transition-context` | 12 | 51 |

The reviewed/non-draft UI control used the CKL `shechem` object. Its content
status is `complete` and review status is `in_review`, so it receives no draft
notice. The current CKL inventory has no `approved` records; no approval was
inferred for this control.

## Changed files

- `bhf_web/static/resource-router.js` — exact ID response guard; source and
  evidence disclosures; attribution and support links; draft notice in
  detail; exact trigger focus restoration.
- `bhf_web/static/styles/companion.css` — disclosure layout, keyboard focus,
  and narrow-screen wrapping.
- `tests/frontend/resource-router.test.js` — exact direct lookup, source and
  evidence mappings, empty/partial records, mismatched IDs, failure, and
  delayed response coverage.
- `tests/test_web_app.py` — exact object API versus general search contract,
  including the 17/46 response counts.
- `tests/gui/ne11h/test_genesis_draft_record_acceptance.py` — five-object
  browser acceptance, exact source identity, governance, keyboard, focus,
  mobile-width, non-draft, and Back/Forward checks.
- `tests/gui/test_canonical_browser.py` — confirms an ID query remains general
  relevance search and can include both `abraham` and the target.
- `docs/narrative-explorer/ne11i/01-exact-canonical-source-disclosure.md` —
  this report.

## Tests, failures, and skips

Final verification results:

| Check | Result |
|---|---|
| `npm test` | 14 test files passed; 0 failures. |
| Canonical API route tests in `tests/test_web_app.py` | 3 passed, including 4 subtests for authored relationships and missing-object 404 behavior. |
| Five governed Genesis Companion browser cases | 5 passed. Exact source IDs and expected evidence counts matched the API. |
| Non-draft, Back/Forward, and Canonical Browser search controls | 3 passed. |
| Jonah/Matthew and Genesis/John browser handoff regressions | 3 passed. |
| CKL inventory command | Exit 0; 687 objects and the required inventory fingerprint. |
| CKL validator | Exit 0; 0 errors and 14 warnings. |
| `git diff --exit-code origin/master -- framework/canonical_library` | Passed; no CKL tree changes. |

The baseline UI reproduction showed zero source records in the Companion
detail. The new renderer regression failed against that behavior before the
renderer change and passed afterward. During test development, the browser
search helper was adjusted to inspect result IDs rather than expect the query
string in rendered card text, and the direct API comparison was moved out of a
time-limited Selenium async script. The first focus check also exposed focus
returning to the first card; focus restoration now returns to the exact
triggering Genesis 12 card. These test-run issues were resolved. There were no
skips in the final named test runs.

## CKL protection

The required inventory fingerprint remains:

`90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`

The five protected Genesis object file hashes are unchanged from
`origin/master`:

| CKL object | SHA-256 |
|---|---|
| `genesis-flood-postflood-context` | `d22862694a5b6a9799074703a36d4a572d14731a51ab4e8ed70a574734e7c44b` |
| `genesis-nations-babel-context` | `ee22202a8bfc1be62469d1e710ae2383149ecad445dc4d721008a18d42a22f23` |
| `genesis-abraham-call-covenant-context` | `02aeceb005539c7175afa4631cffc808ef377b73185b760f582e48119fb38aa9` |
| `genesis-abraham-late-cycle-context` | `95413e73224c3242589c0d9891444f3c7b438bd562d70cdb6ae239d7fd5d7408` |
| `genesis-isaac-jacob-transition-context` | `22f8d2d0b6c7625b1267193ab1fb4e500981ad95713f702b83466b031bcb28cb` |

No CKL object, NE-9C curation, NE-10 bridge, held-candidate, source-lock, or
provenance file changed. The NE-10 registry still has 44 bridge records and 7
held candidates. No scholarly promotion was made.

## Remaining acceptance requirements

No Preview or production deployment was created or changed. The NE-11H Preview
SSO browser blocker remains an independent acceptance requirement. This local
correction does not establish live Vercel browser acceptance, spoken
screen-reader acceptance, or live performance acceptance. Formal policy
authorization for draft records remains separate from showing the existing
draft notice. Production aliases, protection, settings, and deployment
triggers were not changed.
