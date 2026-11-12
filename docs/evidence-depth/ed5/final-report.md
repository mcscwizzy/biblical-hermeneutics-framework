# ED-5 final report

## Scope and outcome

ED-5 began at fetched ED-4 merge `528b1593021f24fe98ff60d1533c7720f5755cd0`
on branch `feat/ed5-discovery-experience`. The assignment adds a truthful
completed-empty CKL state, a collapsed terminology guide, a 12-case
deterministic passage suite, versioned review-history portability, a reviewer
pilot index, and reproducible reports. CKL content and governance records were
preserved.

## Reader experience

The reproduced gap was limited but meaningful: completed empty CKL coverage
did not say that it reflected BHF's coverage rather than the passage's
significance, or offer an existing next step. The overview now does. Readers
can also open plain-language explanations for 14 recurring research terms.
The standalone scripted evaluation passes all 12 selected journeys; all 10
projected records match a unique stable evidence ID. No click-count reduction
or human comprehension/satisfaction result is claimed.

## Research and governance

The current census remains 687 CKL objects, 2,329 claims, 1,408 typed evidence
items, 2,897 source IDs, and 1,189 inventoried chapters (1,090 passage
specific, 56 contextual, 2 entity-only, 41 no eligible material, zero
unknown). The compatibility check confirms 3,925 reviewed relationship
identities, 433 accepted identities, 44 verified bridges, and 7 held
candidates. Jonah/Matthew source-to-receiving direction and supporting claim
pass in the scripted suite. The Ezekiel/Revelation temple proposal remains
held.

Review-history snapshot and explicit restore are ready for a maintainer pilot.
The real ledger remains absent and all 99 queue records remain pending. No
human decision was recorded.

## Readiness and limitations

**Technical readiness:** READY WITH CONDITIONS. The selected CKL, governance,
reader, frontend, profile, census, and package gates pass. The bounded full
pytest run stopped at 25 minutes after 54 tests and 907 subtests passed; it is
incomplete. Current desktop/mobile browser acceptance could not run because
the browser service and local driver are unavailable. See
`validation-results.md` for the run log and scope limits.

**Scholarly publication readiness:** HUMAN REVIEW REQUIRED. The 99 ED-3
records require independent qualified review; machine checks and this pilot
index are not approval.

No genuine reader study was available; heuristic assessments are not human
ratings. Browser focus, 1440px desktop, effective 390px and 320px layouts,
touch targets, screen-reader semantics, contrast, and reduced-motion behavior
remain unverified for ED-5 changes. The full-suite limitation and any final
delivery identifiers are recorded separately. No merge or deployment is part
of this work.

## Delivery status

The feature branch is pushed. Pull-request creation was attempted, but the
GitHub integration returned HTTP 403 (`Resource not accessible by
integration`); the local `gh` CLI is unauthenticated and no browser session is
available. No pull request was created. The comparison page is recorded in
`progress.json` so an authorized GitHub session can open the proposed change.
