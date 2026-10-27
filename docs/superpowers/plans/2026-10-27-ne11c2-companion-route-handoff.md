# NE-11C2 implementation plan

**Design:** [Verified Evidence-to-Connection Handoff](../specs/2026-10-27-ne11c2-companion-route-handoff-design.md)

## Task 1: Expose exact Companion evidence identity

- Add a backward-compatible `ckl_record_identity` object to compact
  `presentation_evidence` entries only when their existing relevance metadata
  identifies a structured CKL claim or evidence item and its parent object.
- Keep legacy fields, source IDs, and notes without standalone local IDs
  unmapped.
- Add Python tests for claim/evidence identity and for absent/invalid identity.
- Run the targeted Companion context tests and verify existing source display.

## Task 2: Match identities to verified routes

- Add a small pure matcher in `companion-discoveries.js` that compares the full
  `(object_id, record_kind, record_id)` key with the confirmed bridge support
  records and stable support keys on authored routes.
- Require complete projection route coverage and exact cited evidence IDs.
- Deduplicate a route reached through multiple cited records; return separate
  route choices when multiple verified route IDs match.
- Add red/green frontend unit coverage for exact matches and wrong parent,
  wrong kind, wrong local ID, source-only, topic-only, held, ambiguous, and
  partial/failed responses.

## Task 3: Load route projection safely from Study Companion

- When Narrative Explorer is enabled and a visible discovery cites a mapped
  record, load the existing projection for the exact selected verse scope.
- Use an abort controller and request sequence/key guard. Clear stale state on
  chapter changes and resource transitions; ignore late results.
- Render direct actions only after a complete projection confirms exact route
  support. Keep generic cross-reference actions and the existing three-card,
  Walk the Land, Locations, and Dig In behavior.
- Add tests for feature-flag off, failed/partial projection, rapid selection
  changes, and preserving the original card/evidence.

## Task 4: Revalidate and focus the selected route in the resource router

- Carry the stable route ID and exact support key through the existing
  `openResource` and `resource-router.open` contracts.
- Revalidate after the activation-time projection load. Defer trail/history
  creation until verification succeeds; return a fallback result otherwise.
- Preserve selected passage and verse scope. Reuse existing follow and return
  navigation for the destination.
- Expand the route list through any needed "show more" pages; select, scroll to,
  and keyboard-focus the selected route heading. Keep the route explanation,
  category, evidence layer, direction, sources, and uncertainty visible.
- Avoid duplicate category/evidence labels where their display strings match.
- Add focused tests for stale activation, hidden route expansion, focus,
  history, route following, return to origin, and fallback without an empty
  trail.

## Task 5: Acceptance and integrity review

- Verify Genesis 1 / John 1 and eligible Jonah / Matthew routes, their exact
  support identities, classifications, direction, sources, and uncertainty.
- Exercise negative controls: Psalm 22 / Mark 15, held Deuteronomy 32 / Psalm
  82, Psalm 110 / Acts 2, no-route passages, mismatched identities, source/topic
  matches, partial/failed projections, and rapid chapter changes.
- Run Companion, Narrative Explorer, NE-9C/NE-10, CKL, packaging, and frontend
  test suites, plus browser/keyboard acceptance where the local browser setup
  permits it. Record the six clean-master presentation structured-output
  failures separately and do not repair unrelated failures.
- Compare CKL object/source fingerprints, all 44 bridge identities, all seven
  held candidate identities, and NE-9C state with the baseline.
- Review `git diff --check`, complete diff, generated files, and final commit;
  commit and push the feature branch without merging or deploying.
