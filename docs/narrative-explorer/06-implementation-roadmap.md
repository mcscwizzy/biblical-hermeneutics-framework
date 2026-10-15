# Narrative Explorer: Implementation Roadmap

## Constraints for every transaction

- Keep CKL and source records authoritative. Any UI/API projection is read-only; never write presentation summaries back into CKL.
- Preserve BHF's mission: “Teach AI how to interpret Scripture responsibly, not what to believe.”
- Preserve Ask BHF prompts, interpretive principles, model handoff, and current manual copy/open behavior.
- Do not generate exact coordinates for unidentified places or turn cosmic geography into physical maps.
- Keep original passage evidence, ancient comparison, textual witnesses, later reception, and interpretation distinct.
- Do not use paid AI rendering for the reader's evidence projection.
- Keep Tyndale notes, personal notes/highlights/saved studies, lexicon, translation comparison, maps, archaeology, and offline behavior.
- Do not edit, regenerate, delete, or promote frozen Commentary releases in a Narrative Explorer transaction.

## Suggested transaction sequence

### NE-2 — Projection adapter and contract tests

**Goal:** Define a pure projection adapter over CompanionContextService, CKL, evidence bundles, map records, and archaeology records.

**Acceptance criteria**

- A typed response contract is versioned 1.0 and keeps original IDs, passage anchors, claim/evidence/source links, review and dispute status, temporal relation, and geography kind.
- Claim and evidence IDs are parent-qualified; no second database or write path is introduced.
- Query failure, not represented, unknown, not established, disputed, and partial have distinct response states.
- Broad parents project only passage-overlapping nested claims/notes/evidence; parent-only cross-reference strings do not leak into chapter trails.
- A completed empty domain lookup is distinct from a subsystem failure.
- Contract tests cover Genesis 6 and Psalm 82, where the CKL record is present but the legacy theme type bucket is empty.

**Rollback:** Keep the adapter unregistered if shape or provenance validation fails. Existing routes and payloads are untouched.

### NE-3 — Read-only versioned passage endpoint

**Goal:** Expose the adapter through /api/narrative-explorer/v1/passages/{book}/{chapter} without replacing existing routes.

**Acceptance criteria**

- Chapter and verse-range requests use current normalization and eligibility rules.
- Output sections link only to records existing APIs can resolve.
- Source details, link types, reverse-link availability, and per-domain coverage are validated against actual route/object schemas.
- GET requests do not change CKL, source, map, archaeology, Commentary, or personal-study storage.
- API checks verify partial, empty, unknown, disputed, unsupported, and unavailable-source states.

**Rollback:** Remove or disable the new route; no migrations or existing response changes are needed.

### NE-4 — Companion overview and feature-flagged entry

**Goal:** Add a default-off Explore the Narrative overview inside the existing Study Companion.

**Acceptance criteria**

- Existing passage selection, responsive sheet/dock, loading states, browser history, and focus restoration are reused.
- Overview cards show actual evidence category, count/state, and one concise source-grounded highlight.
- Card state distinguishes available, partial, not represented, and unknown.
- BHF Context remains visible and Ask BHF is unchanged.
- Existing note, highlight, save, Tyndale, lexicon, translation-comparison, and map actions remain reachable.
- Frontend checks cover desktop and mobile entry, status announcements, keyboard path, empty data, offline cache hit, and offline miss.

**Rollback:** Turn off the flag and return to the existing Companion overview.

### NE-5 — Evidence detail, source view, and connection trails

**Goal:** Add expandable evidence details, bibliography views, typed connections, and nested passage/subject navigation.

**Acceptance criteria**

- Every claim opens its actual CKL/evidence/source record or states which identifier is unresolved.
- Relation label and basis appear before navigation. Unsupported or legacy free-text links stay uncategorized.
- A reverse action appears only when the underlying record or stable graph edge supports it.
- Original-passage observation, comparative background, later reception, and interpretation are separately labeled.
- Breadcrumb/back/return-to-chapter behavior works through nested record and passage links.
- Checks cover duplicate local evidence IDs under different CKL parent objects and one-way relationships.

**Rollback:** Disable nested trail rendering while retaining overview and current resource pages.

### NE-6 — Physical geography and cosmic-geography safeguards

**Goal:** Integrate existing place, period, territory, route, and map references with a separate text/concept view for cosmic geography.

**Acceptance criteria**

- Only stored map IDs/coordinates are used; no geocoder or generated-coordinate path is added.
- Place name, coordinates, and identification confidence are separate fields.
- Unidentified or materially disputed places do not render a precise point as an established biblical location.
- Cosmic/sacred-space records remain textual/conceptual and never create point markers by default.
- Genesis 2–3 Eden/rivers and Exodus 3 Horeb/Sinai pass review with source and uncertainty visible.
- Map details preserve periods, linked passages, source references, and broad-versus-verse-specific scope.

**Rollback:** Suppress map geometry for uncertain records; keep linked textual place detail.

### NE-7 — Six-passage pilot and accessibility/offline acceptance

**Goal:** Validate real coverage before changing the default reader feature.

**Acceptance criteria**

- Census all six pilots with the read-only adapter and compare every displayed item to CKL/map/archaeology source IDs.
- Genesis 6 and Psalm 82 expose existing evidence even though legacy theme entities are zero.
- The Genesis 6 cross-reference contamination is absent from passage-specific trails.
- Empty archaeology-service sections do not suppress separate manuscript or ancient-text evidence in CKL.
- Verify touch, keyboard, screen-reader, back/forward, cache invalidation, offline pack, and offline-miss behavior.
- Record remaining verified gaps without filling them with speculative objects.

**Rollback:** Keep the feature flag off; return pilot feedback to adapter/UI transactions without changing source data.

### NE-8 — Default transition after approval

**Goal:** Make Narrative Explorer the primary selected-passage experience only after the six-passage pilot is accepted.

**Acceptance criteria**

- A reviewed release checklist confirms source traceability, uncertainty, accessibility, offline support, and no Ask BHF behavior change.
- A feature flag controls the default and a tested rollback returns to the former experience.
- Existing BHF-generated Commentary remains behind an Archived chapter Commentary path.
- Tyndale Companion remains in its current notes workflow.
- No commentary artifact, manifest, checksum, or API is removed in this transaction.

**Rollback:** Flip the default flag back. Keep both views available while diagnosing the issue.

### NE-9 — Optional Ask BHF evidence context (separate design first)

**Goal:** Let a reader explicitly include selected evidence context in a future Ask BHF question.

**Acceptance criteria**

- A separate interface design is reviewed before implementation.
- Proposed inputs are selected passage, chosen CKL topic/theme, chosen evidence IDs, source/provenance references, and the user's typed question.
- The reader sees and can remove included evidence before opening the external assistant.
- No private notes, highlights, saved-study text, or personal history are included automatically.
- Implementation does not assume a future plugin supports this interface; manual copy/open remains available.

**Rollback:** Retain current handoff text and remove optional evidence preparation.

### NE-10 — Renderer decommission review (separate authorization)

Inventory use after migration and decide whether any BHF Commentary renderer code or endpoint remains necessary. This transaction requires separate authorization. Frozen v1.1/v1.2 release content, manifests, checksums, and Tyndale notes remain preserved unless a distinct release transaction authorizes other changes.

**Acceptance criteria:** enumerate all runtime/API/offline/test/archive consumers; retain immutable artifacts; document reader path and rollback before any removal.

## Recommended first implementation transaction

Start with NE-2, the pure projection adapter and contract tests, then expose it through NE-3. Genesis 6 and Psalm 82 are strong initial contract fixtures because they prove passage-anchored claims and sources can be exposed even when the legacy theme bucket is empty. The adapter also provides the earliest check that inherited cross-references are filtered at claim/evidence scope. No UI or Commentary change is needed to validate those boundaries.

## Verification boundaries

NE-1 itself is documentation-only. It does not run future implementation transactions, tests requiring code changes, paid rendering, Commentary regeneration, CKL edits, production deployment, feature-flag changes, or release promotion.
