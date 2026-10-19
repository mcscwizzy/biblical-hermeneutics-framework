# NE-8A Narrative Explorer reader experience results

## Scope and baseline

NE-8A starts from `origin/master` at `5d227a4467afef8d8bfd6765c5760a29dd09899d` on `feat/narrative-explorer-ne8a-reader-experience`. The review covered the product and evidence contracts, NE-7 acceptance reports, NE7R3 Commentary retirement, and the current Vercel packaging report.

NE-7 established that the Explorer remains default-off and that local functional checks passed, while release readiness still depended on hosted packaging verification, screen-reader review, narrow mobile review, and other hosted checks. NE7R3 removed generated Commentary and its coverage UI while retaining Tyndale Study Notes, Maps, translation comparison, personal Notes/Highlights, and offline support.

The latest packaging work excludes generated build and retired Commentary candidate files, keeps the packaged CKL database, provisions Tyndale Study Notes during the Vercel build, and includes a retry change for archive requests. The reported local staging size fell from 349.57 MB to 201.65 MB. The latest preview failed before Tyndale provisioning because `BHF_TYNDALE_ARCHIVE_URL` was unset. This task made no Vercel or deployment changes.

## Reader-journey findings

| Journey | Findings before NE-8A | Current path and guardrails |
| --- | --- | --- |
| Genesis 6:1–4 | The passage-first entry is available after selecting the passage and opening “Explore the Narrative.” The overview used implementation-facing count language and previews exposed raw values such as `worldview-concept` and `literary-convention`. Detail records separate the textual wording, disputed readings, Nephilim syntax limits, and Second Temple reception; each can be inspected with its passage anchors and source references. | Preview labels now distinguish disputed interpretation, literary interpretation, and later reception. “Inspect evidence and connections” opens recorded observations, scholarly interpretation, uncertainty, scripture anchors, and bibliography. The trail returns to the originating passage. NE-8A.1 adds a detail-level caution that distinguishes later reception from Genesis 6’s original meaning and calls out the record’s `contemporary` temporal label for review; the CKL source itself remains unchanged. |
| Psalm 82 | The overview can surface the poem’s assembly language and Ugaritic council comparison, but raw category metadata was not a reader-facing explanation. The records state that the identity of the judged figures and the history behind the imagery remain disputed; comparison does not establish borrowing or Israelite doctrine. | Cards distinguish “Original biblical text · worldview language” from “Ancient comparative literature.” The detail and bibliography expose the Hebrew-text and Ugaritic source records, their anchors, and the recorded limits on historical inference. “Return to Psalms 82” restores the originating passage. NE-8A.1 resolves `Psalm` as the reader’s canonical `Psalms` name at the navigation boundary: CKL anchor/display text stays `Psalm 82:1–8`, while the reader target and trail use `Psalms 82:1–8`. |
| Genesis 2 | Garden/sacred-space discussion and river geography are available from the passage. Geography labels could imply all such records were original-text claims even when their assertion type was secondary evidence. The record says Pishon and Gihon remain unidentified and Genesis supplies no coordinates. | The overview uses the neutral “Geography and place identification” label. Detail retains the explicit planting and river observations separately from sacred-space interpretation, and states that the text does not establish a recoverable garden location. The map projection continues to withhold display coordinates when physical identification is unestablished; the cosmic/geographic caution remains intact. |

Across the three journeys, “Evidence and source details” provides the stored evidence category, passage relationship, IDs, and source IDs. Detail views show source bibliography and uncertainty. Connection trails retain the recorded relationship label, direction, and supporting rationale; authored descriptive associations remain distinguishable from established relationships. “Return to …” restores the originating passage. Ask BHF remains in the existing Study Companion flow; NE-8A.1 does not change its handoff.

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

## NE-8A.1 findings and acceptance

### Psalm/Psalms navigation

The reader book selector exposes canonical `Psalms`. `validateScriptureReference` previously compared normalized book names literally, so an evidence anchor beginning `Psalm` failed the allowlist check before the reader navigation callback ran. The fix accepts the singular/plural Psalm aliases when either canonical option is present, prefers an exact reader option, and returns the reader’s canonical book value. It does not rewrite the CKL reference, evidence identity, verse range, or displayed source text.

Firefox verification opened the `Psalm 82:1–8` anchor as `Psalms 82:1–8`, selected verses 1–8, retained the original anchor in trail history, survived browser Back/Forward, and returned to the originating `Psalms 82:1` selection. Compare Translations displayed multiple translations without changing that selection. The frontend regression covers both input spellings and checks that the callback receives canonical navigation text while the stored/displayed reference remains singular.

### Watchers temporal metadata

The CKL record is `framework/canonical_library/objects/cultural_background/genesis-flood-postflood-context.json`, parent object `genesis-flood-postflood-context`, evidence ID `g6-second-temple-watchers-reception`, source passage Genesis 6:1–4, and no claim ID (`claim_ids: []`). Its Scripture-link metadata is `relationship: direct`, `temporal_relation: contemporary`, with a rationale that says the Genesis passage contains the wording or event and that no later passage is indexed. Its temporal scope is empty. The evidence description, primary observation, scholarly interpretation, notes, and title instead explicitly distinguish Genesis wording from later Watchers reception.

The supporting source IDs are `g2r2-local-genesis-1-50` (Genesis text), `g2-doedens-sons-god` (Doedens, 2019), `g2-1-enoch-6` (1 Enoch 6–16, source year -200), and `g2-jubilees-5` (Jubilees 5:1–11, source year -150). The 1 Enoch and Jubilees source notes call them later reception and state they are not evidence for Genesis 6’s immediate wording. There is no separate claim dividing the record’s textual observation from its later-reception material.

The CKL evidence-link contract defines `temporal_relation` as the evidence’s historical relation to its Scripture passage, separate from source-composition or surviving-copy dates. Here, `contemporary` is attached to the Genesis 6:1–4 link; it is not a date for 1 Enoch or Jubilees. The projection passes the stored value through unchanged, so this is not a projection rewrite. The source record combines a direct observation about Genesis with later reception under one evidence ID, making the temporal label ambiguous at item level. Before NE-8A.1 the UI labeled the card “Later reception” from its authored text but also displayed “Temporal relation: contemporary” without explaining the conflict. The detail view now retains that raw provenance and adds a caution: later reception does not establish Genesis 6’s original meaning, and the CKL temporal metadata needs review.

No CKL change was made. Proposed CKL-owner change for separate approval, if the item is confirmed to represent the later-reception evidence described by its title and sources:

```text
evidence_items[id="g6-second-temple-watchers-reception"]
  scripture_references[reference="Genesis 6:1-4"].temporal_relation:
    "contemporary" -> "later-comparative"
  scripture_references[reference="Genesis 6:1-4"].relevance_rationale:
    "This item records Second Temple reception of Genesis 6:1-4; the Watchers interpretation belongs to later reception and does not establish the passage's original meaning."
```

Keep the Scripture relationship, all four source IDs, source years, evidence ID, and source records unchanged. If CKL owners intend `contemporary` to describe only the item's separate Genesis wording observation, split or otherwise distinguish that observation from later reception before changing the temporal relation; the current single evidence record cannot express both layers clearly.

### NE-8A.1 verification

- Frontend: `npm test` — 12/12 test files passed. The Narrative Explorer tests now cover both Psalm spellings, canonical navigation output, preserved CKL anchor text, and the Watchers caveat.
- Python: focused Narrative Explorer projection/API, UI configuration, packaging, and Commentary-retirement suite — 84 passed.
- Python: Tyndale commentary, evidence, and Vercel-provisioning suite — 27 passed.
- Firefox: Psalm alias navigation, selected verses, history Back/Forward, return to origin, and Compare Translations — 1 passed.
- Firefox: Genesis 6, Psalm 82, and Genesis 2 reader journeys, including the Watchers source/caution; Ask BHF and Compare Translations handoff — 3 passed across the focused runs.
- Firefox: existing Notes/Highlights study-pack and offline behavior, plus Maps fallback, mobile navigation, and geography safeguards — 2 passed.
- The local `.bhf/commentary.sqlite` Tyndale fixture is absent, so its browser-backed data test is unavailable separately; the retained Tyndale Python checks passed. No Vercel environment or deployment was changed.

**NE-8A.1 acceptance:** PASS for the Psalm navigation and reader-presentation findings. The temporal metadata source correction remains pending CKL-owner review and was not applied. Keep the feature flag default-off.

## Remaining concerns and readiness

The CKL owner should review the mixed-layer Genesis 6 Watchers record and proposed temporal metadata correction before enabling the feature by default. The default-off feature also still needs the outstanding screen-reader and hosted-package validation called out by NE-7. The latest packaging attempt needs the authorized Tyndale archive variable in its environment before a hosted preview can verify that path.

**Recommendation:** Open a PR for the narrowly scoped reader changes and tests. Keep the feature default-off; include the CKL-owner correction proposal for separate review, and do not treat this local validation as a release or rollout sign-off.
