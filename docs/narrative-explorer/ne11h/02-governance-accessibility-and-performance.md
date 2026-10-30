# NE-11H — Governance, Accessibility, and Performance

## Governance disclosure — local browser observations

The Preview UI was not reachable through the test browser because its active
Vercel SSO protection redirected the session to Vercel Login. The following
record-level results are from local Chromium, using the same repository tree.

For each chapter, the test selected the passage, inspected the actual
Companion context ID, opened Canonical Context, and checked the card and its
detail. In all five cases the object remained `draft` / `in_review` with
`human_review_required: true`; the full title and CKL summary were displayed.
The notice **“Draft evidence — awaiting human review”** was visible and part
of the card's accessible name. Each card opened its title-matching details,
and the selected chapter remained selected.

| Passage | CKL record ID | Displayed title | Notice and accessible name | Follow-on source detail |
|---|---|---|---|---|
| Genesis 6 | `genesis-flood-postflood-context` | Genesis Flood and Post-Flood Context | Pass | Canonical Browser opened this exact title; 29 source cards were visible. |
| Genesis 10 | `genesis-nations-babel-context` | Genesis Nations and Babel Context | Pass | Canonical Browser opened this exact title; 20 source cards were visible. |
| Genesis 12 | `genesis-abraham-call-covenant-context` | Genesis Abraham Call and Covenant Context | Pass | Exact-ID search opened **Abraham** (`canonical_id: abraham`, “Direct object lookup”), not the target record. Its source cards cannot be attributed to the Genesis 12 record. Target-record source evidence was not verified in that UI path. |
| Genesis 18 | `genesis-abraham-late-cycle-context` | Genesis Abraham Late Cycle Context | Pass | Canonical Browser opened this exact title; 5 source cards were visible. |
| Genesis 26 | `genesis-isaac-jacob-transition-context` | Genesis Isaac–Jacob Transition Context | Pass | Canonical Browser opened this exact title; 12 source cards were visible. |

The detail rendered directly inside the Companion showed no source cards for
any of the five records. For Genesis 6, 10, 18, and 26, the separate
Canonical Browser follow-on resolved the exact record and exposed source
cards. For Genesis 12, the follow-on resolved a related Abraham entity, so
the visible source cards were not evidence for the selected context record.
The local test screenshot documenting the Genesis 12 result is retained only
under `/tmp/ne11h-browser-artifacts`.

This is a UI evidence-access gap for Genesis 12, not a finding that its CKL
source material is absent. No CKL content was changed. The local source-path
acceptance **fails for Genesis 12**; the deployed Preview result remains
unexecuted. The governance gate is therefore a release blocker until the
exact record's source evidence is accessible and verified in the Preview.

Reproduction in the local browser: select Genesis 12, open Companion Canonical
Context, open the card with ID `genesis-abraham-call-covenant-context`, choose
“Open Canonical Knowledge,” and search for that exact ID. The result detail
shows title “Abraham” and canonical ID `abraham`, not the selected context
record. Do not count those Abraham sources as the context record's evidence.

### Governance-field negative controls

`node --test tests/frontend/resource-router.test.js` passed. Its draft case
uses a generic record ID and shows that the notice depends on all three fields:

- `content_status = draft`
- `review_status = in_review`
- `human_review_required = true`

The approved/non-draft case receives no draft notice. The missing-metadata
case receives neither a draft notice nor an approval label. This confirms the
rule is field-based and does not depend on a Genesis-specific ID. The
five-record browser cases also verified that the exact CKL IDs and draft
governance values were returned for their selected chapters.

The proposed policy is consistent with the observed disclosure behavior:
draft evidence may be displayed with an accurate editorial-status notice, but
must not be described as human-reviewed or approved until that review is
recorded. Formal authorization to use these records in production has not
been provided in this task and remains an explicit governance decision.
All five records remain `generated_by: []` and `reviewed_by: []`; no review
or approval is inferred.

## Automated keyboard accessibility

Local Selenium checks exercised Tab and Shift+Tab, Space and Enter, the
route-heading focus target, route activation, Escape, and focus restoration.
The route's polite status text announced the selected reference in the DOM,
and the returning focus target was the original “Explore this connection”
button. These are browser and accessibility-tree checks only; they do not
establish what a screen reader actually speaks. See report 01 for the
four-width keyboard and history measurements.

## Spoken screen-reader acceptance

**MANUAL / NOT EXECUTED.** The available browser was headless Chromium. No
supported VoiceOver/Safari, NVDA/browser, or Orca/graphical-browser session was
available. No spoken output is inferred from DOM text or ARIA attributes.

Reproducible spoken review when an authorized Preview session and supported
screen-reader workstation are available:

1. Open the Preview and select Genesis 1:1–5. Navigate headings and listen for
   the Reader heading and selected Scripture announcement.
2. Open Study Companion. Confirm the Companion heading and passage are spoken.
3. Reach a discovery and verify “Explore this connection” is announced as the
   control name.
4. Activate it. Confirm the Narrative Explorer heading and route relationship
   are announced, then open the evidence/source disclosure and listen for the
   exact record and source identities.
5. Navigate to the related passage and confirm the selected reference is
   announced. Return to the origin and verify the Scripture and focus return
   to the originating action.
6. Select Genesis 6, open Canonical Context, and confirm the draft notice is
   spoken with the record card. Repeat source disclosure for Genesis 10, 12,
   18, and 26, checking that no review or approval is announced.

Record the spoken output verbatim in a private review log; do not place
personal screen-reader settings or user information in the Git report.

## Browser performance

**Live Preview performance: NOT MEASURED; release decision NEEDS DECISION.**
The authentication redirect prevented the app document from loading. No
Preview `PerformanceNavigationTiming`, `PerformanceResourceTiming`, request
counts, response sizes, cache state, or user-visible interaction times could
be collected. No connector round-trip timings or local timings are substituted
for live browser measurements.

No performance threshold was specified before this run. The release operator
must collect at least three comparable authenticated Preview samples for
initial load, Genesis projection, Jonah context, opening a discovery, opening
a route, related-passage navigation, and return. Report the median, minimum,
maximum, request count, available payload sizes, cache behavior, failed or
duplicate requests, and browser/OS/network conditions, then accept or reject
the observed values without retroactively inventing a threshold.

## Session-scoped recovery — local browser

These tests used one-off browser `fetch` interception or Chrome DevTools
network emulation in the disposable Selenium session. No shared Vercel
configuration or real study database was involved.

| Scenario | Local result |
|---|---|
| Delayed Narrative Explorer projection, then chapter change | Pass. Pending request was aborted; releasing its HTTP 200 response did not add the old route or trail to the newer Jonah 2 selection. |
| Delayed Companion context, then newer passage selection | Pass. The late John 1:3 context did not replace John 1:14. |
| Failed Companion request | Pass. The injected `Failed to fetch` response produced a visible `role=alert`; John 1:13 Scripture remained readable and selected. Restoring fetch and selecting John 1:14 returned the Companion to `ready`. |
| Browser Back during loading | Pass. `/api/maps/catalog` was held after response receipt while the UI showed “Loading map data...”. Browser Back returned to the study overview with John 1:1 selected; releasing the response did not overwrite that state. |
| Missing eligible route / empty projection | Pass. No verified discovery or actionable related passage was fabricated; the safe empty state showed no linked route. Refresh restored the normal eligible Jonah route. |
| Temporary offline and reconnect | Pass. While Chrome was offline, no Jonah route was shown, while cached Jonah Scripture remained readable. After reconnect and reload, the eligible Jonah route opened normally. |

**Live Preview recovery: NOT EXECUTED.** Local recovery evidence cannot
substitute for the requested authenticated Preview failure-injection run.
