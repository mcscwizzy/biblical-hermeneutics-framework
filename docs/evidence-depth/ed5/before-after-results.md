# ED-5 before/after results

| Reader outcome | Before | After | Measure and limit |
|---|---|---|---|
| Completed passage with no eligible CKL evidence | Category cards said no linked records; overview lacked a plain statement of what empty coverage means. | Overview says no eligible BHF research is currently available, distinguishes coverage from historical significance, and points to existing broader context. | Frontend regression checks exact completed-empty condition and language. No browser click or comprehension measure available. |
| Unfamiliar scholarly terms | No shared Narrative Explorer quick guide. | Collapsed native disclosure includes 14 terms and qualifications. | Frontend regression confirms collapsed initial state and key definitions. Comprehension is unmeasured. |
| Exact evidence discovery | ED-4 had selected coverage and reader acceptance cases. | A reusable 12-journey suite verifies exact IDs/anchors/sources, ordinary-language ranking, one empty case, and Jonah route direction. | 12/12 scripted cases pass. There is no equivalent ED-4 12-case denominator, so this is a new acceptance baseline rather than a percentage improvement. |
| Verified Jonah/Matthew connection | ED-4 tested both endpoints and route projection. | Same exact route and support pass the reusable suite; no governance change. | One route on each endpoint in data; browser history/focus not remeasured. |
| Source navigation and responsive display | ED-4 browser evidence covered source details, long locators, 320/390px, and navigation history. | Source renderer untouched; no ED-5 browser run. | No new measured before/after click count. Existing evidence is not represented as a new pass. |
| Review portability | Local append-only hash chain and exports; no versioned backup/restore workflow. | Versioned no-overwrite mode-0600 snapshot, optional external digest verification, explicit suffix restore, and queue reconciliation. | Synthetic isolation tests pass. Real ledger absent; no real events imported or created. |

No interaction-count reduction is claimed. Current browser execution was
unavailable, and scripted checks cannot establish that people understood the
presentation better.
