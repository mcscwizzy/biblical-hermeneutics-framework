# Commentary v1.2 reader integration

Last verified: 2026-09-12

## Release

- Release: `commentary-v1.2`
- Packaging/integration commit: `c5444ade` (`Package and integrate commentary v1.2 release`)
- Packaged population: 75 validated chapters
- Published: 62
- Not published: 13
  - 8 `NOT_RENDERABLE_SOURCE_LIMITED`
  - 3 `MODEL_OUTPUT_REJECTED`
  - 2 `QUALITY_REVIEW_REQUIRED`
- Checksum diagnostics: valid
- Default release: `commentary-v1.1`
- Opt-in release: set `BHF_COMMENTARY_RELEASE=commentary-v1.2`

The reader uses the packaged v1.2 path only when the opt-in release is selected. It does not fall back from v1.2 to v1.1, and candidate directories are not runtime sources.

## Reader behavior

The existing Study Companion commentary card is the integration surface. The v1.2 change is intentionally small:

- published payloads render through the existing read-only card and evidence explorer;
- source-limited chapters explain that supporting evidence is too limited;
- rejected model output is described as unavailable in the current release;
- quality-review chapters are described as still under review;
- chapters outside the validated v1.2 population are identified as not included;
- internal `reason` and `release_state` values are not shown verbatim to readers;
- unavailable states clear commentary, verse references, evidence controls, and prior card content;
- evidence remains restricted to stored commentary citations.

No model call, generation path, CKL mutation, or v1.2-to-v1.1 fallback is part of reader rendering.

## Verification

Focused checks passed:

- Node frontend suites: 2 passed.
- v1.2 reader integration tests: 2 passed.
- Existing release, packaging, production-runtime, canonical-runtime, and release-promotion checks: passed in the focused suite.
- Headless Firefox browser smoke with the opt-in environment: the rendered shell reported `commentary-v1.2`; the card rendered the safe outside-population message for the initial John 1 state; the API returned the expected published, source-limited, rejected, review, and outside-population states; desktop and mobile layouts had no horizontal overflow.
- Browser evidence/API coverage confirmed that only stored cited evidence IDs are returned by the evidence route.

The repository's `agent-browser` executable is not installed in this environment, so the visual smoke used the installed headless Firefox/Selenium fallback. The browser's natural chapter-selection path remained in `loading` for published John 5 during this session, while the same browser's direct `BHFApi.requestJson` resolved and the card's direct published projection rendered correctly. This is retained as a warning for follow-up on the existing offline/cache loading path; it is not attributed to the v1.2 release manifest or evidence projection.

## Known unrelated blocker

The pre-existing synthesis/provenance suite remains blocked by a dirty-worktree identity mismatch for Romans 3. Frozen expected synthesis identity:

`cabe3ffbc864a311d6fba144d0ab5872c45de24779c7ed986dd6e454dea489bc`

Current computed identity:

`a464b95b7aca4f8cdb711e4c1c930ad06a0590598f3f67cb971e2a56b9bfdb53`

Classification: `PRE_EXISTING_DIRTY_WORKTREE_BLOCKER`. No synthesis artifact, model output, CKL record, or unrelated dirty file was repaired or reverted.
