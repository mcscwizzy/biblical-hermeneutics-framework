# NE-8A Narrative Explorer reader experience results

## Scope and baseline

NE-8A starts from `origin/master` at `5d227a4467afef8d8bfd6765c5760a29dd09899d` on `feat/narrative-explorer-ne8a-reader-experience`. The review covered the product and evidence contracts, NE-7 acceptance reports, NE7R3 Commentary retirement, and the current Vercel packaging report.

NE-7 established that the Explorer remains default-off and that local functional checks passed, while release readiness still depended on hosted packaging verification, screen-reader review, narrow mobile review, and other hosted checks. NE7R3 removed generated Commentary and its coverage UI while retaining Tyndale Study Notes, Maps, translation comparison, personal Notes/Highlights, and offline support.

The latest packaging work excludes generated build and retired Commentary candidate files, keeps the packaged CKL database, provisions Tyndale Study Notes during the Vercel build, and includes a retry change for archive requests. The reported local staging size fell from 349.57 MB to 201.65 MB. The latest preview failed before Tyndale provisioning because `BHF_TYNDALE_ARCHIVE_URL` was unset. This task made no Vercel or deployment changes.

## Reader-journey findings

| Journey | Findings before NE-8A | Current path and guardrails |
| --- | --- | --- |
| Genesis 6:1–4 | The passage-first entry is available after selecting the passage and opening “Explore the Narrative.” The overview used implementation-facing count language and previews exposed raw values such as `worldview-concept` and `literary-convention`. Detail records separate the textual wording, disputed readings, Nephilim syntax limits, and Second Temple reception; each can be inspected with its passage anchors and source references. | Preview labels now distinguish disputed interpretation, literary interpretation, and later reception. “Inspect evidence and connections” opens recorded observations, scholarly interpretation, uncertainty, scripture anchors, and bibliography. The trail returns to the originating passage. The Watchers record’s authored text calls it later reception, while its stored `temporal_relation` says `contemporary`; that metadata conflict remains visible in provenance and needs CKL-owner review. |
| Psalm 82 | The overview can surface the poem’s assembly language and Ugaritic council comparison, but raw category metadata was not a reader-facing explanation. The records state that the identity of the judged figures and the history behind the imagery remain disputed; comparison does not establish borrowing or Israelite doctrine. | Cards distinguish “Original biblical text · worldview language” from “Ancient comparative literature.” The detail and bibliography expose the Hebrew-text and Ugaritic source records, their anchors, and the recorded limits on historical inference. “Return to Psalms 82” restores the originating passage. A same-passage Scripture anchor stored as “Psalm 82:1–8” is currently marked unavailable because the reader’s canonical book list uses “Psalms”; cross-reference navigation therefore has an alias gap even though returning to the origin works. |
| Genesis 2 | Garden/sacred-space discussion and river geography are available from the passage. Geography labels could imply all such records were original-text claims even when their assertion type was secondary evidence. The record says Pishon and Gihon remain unidentified and Genesis supplies no coordinates. | The overview uses the neutral “Geography and place identification” label. Detail retains the explicit planting and river observations separately from sacred-space interpretation, and states that the text does not establish a recoverable garden location. The map projection continues to withhold display coordinates when physical identification is unestablished; the cosmic/geographic caution remains intact. |

Across the three journeys, “Evidence and source details” provides the stored evidence category, passage relationship, IDs, and source IDs. Detail views show source bibliography and uncertainty. Connection trails retain the recorded relationship label, direction, and supporting rationale; authored descriptive associations remain distinguishable from established relationships. “Return to …” restores the originating passage. Ask BHF remains in the existing Study Companion flow; NE-8A does not change its handoff.

Discoverability still depends on the feature flag. NE-8A leaves the default flag unchanged, so the ordinary default reader does not gain a new entry point.

## Focused change

Before, the overview said “Counts separate parent records, claims, and evidence entries” and described projections as discoveries. Preview badges also concatenated raw evidence categories, claim types, assertion types, and domains.

Now, the intro explains that the reader can follow a passage into sources, check passage links and uncertainty, and treat linked-record coverage as partial rather than complete. Section counts use one reader-facing phrase, “N linked records,” and distinguish completed empty lookups, partial results, and lookups that did not complete. Preview cards show a reader-facing evidence layer; CKL’s original category, assertion type, and source identities remain in expandable provenance. The details view uses “Geography and place identification” for geography records, without labeling secondary interpretation as original biblical text.

No CKL/database records, API projection contracts, feature defaults, Commentary assets, Ask BHF behavior, or deployment settings were changed.

## Verification

- Frontend: `npm test` — 12 test files passed, including the new three-journey fixture assertions, Ask BHF handoff, Commentary retirement, and offline/service-worker checks.
- Python: focused Narrative Explorer projection/API, UI configuration, Vercel packaging, and Commentary retirement suite — 84 passed. This includes Genesis 2 coordinate withholding and Genesis 6/Psalm 82 passage scoping.
- Python: Tyndale commentary, evidence, and Vercel provisioning suite — 27 passed.
- Browser: Firefox three-passage journey plus existing desktop/mobile Explorer dock and sheet smoke — 2 passed in 104.02 seconds. It opened CKL records, expanded rationale and bibliography, checked source IDs and uncertainty, and returned to each origin; the layout smoke covered 390 px and desktop width.
- Browser: Ask BHF and Compare Translations — 1 passed. Ask BHF opened with the selected `John 1:1` reference; comparison showed multiple translations and retained the selection.
- Browser: existing offline study-pack/Notes/Highlights preservation — 1 passed. Maps/offline fallback and geography safeguards — 1 passed after the evidence-role label was retained.
- CKL: `python -m framework.canonical_library --root framework/canonical_library --json` loaded all 687 CKL objects with inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. Read-only `PRAGMA integrity_check` on `.bhf-data/study.sqlite` returned `ok`. No CKL source records or protected database were edited.

The worktree does not contain `.bhf/commentary.sqlite`, so the existing browser test that reads a local Tyndale database will skip here. Template, API-contract, and parser tests still cover the retained Tyndale surface and data path.

## Remaining concerns and readiness

The explicit temporal metadata conflict on the Genesis 6 Watchers record should be resolved by the CKL owner before enabling the feature by default; NE-8A does not edit CKL. Psalm anchors use “Psalm” while the reader recognizes “Psalms,” so those cross-reference buttons remain unavailable. The default-off feature also still needs the outstanding screen-reader and hosted-package validation called out by NE-7. The latest packaging attempt needs the authorized Tyndale archive variable in its environment before a hosted preview can verify that path.

**Recommendation:** NE-8A is a suitable local reader-experience improvement for continued gated review. Keep the feature default-off and do not treat this local validation as a release or rollout sign-off.
