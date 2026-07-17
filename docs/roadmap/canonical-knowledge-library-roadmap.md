# Canonical Knowledge Library - Phase Roadmap

> Resume aid for CKL work. Saved in-repo so the next conversation can pick up
> from the latest completed phase.
>
> Last completed phase: Phase 18 - Packaging, Versioning, and Release.
>
> Current phase: Phase 10 - Core Content Population (wave 4 complete; no remaining phase-10 work).

## Current State

- The CKL foundation is in place.
- The runtime now consumes CKL during startup, retrieval, prompt construction, cache reuse, and debug output.
- The authoring, manifest, reporting, and validation tools are in place.
- The stable CKL packaging and release line is complete.
- The Wave 2 Bible-book records are now populated with authorship, dating, audience, setting, genre, structure, themes, placement, key entities, disputes, and source anchors.
- The Wave 3 people, places, events, and institutions are now populated with deterministic profile-based content and explicit relationship links.
- The remaining live work from the original roadmap is complete; only future refinement and new backlog items remain.

## Update Protocol

- After each phase, update the execution log and advance the current phase marker.
- Stop at the end of each phase and save a clean handoff note.
- If a new conversation starts, read this file first and continue from the current phase marker.

## Phase 8 - Runtime Integration

Goal: Make the BHF agent actually use the CKL.

- Add a CKL config section to the agent config.
- Load `CanonicalLibrary` once during agent startup.
- Detect relevant canonical objects from the user's question, detected Scripture references, detected Bible books, and selected reader text.
- Retrieve CKL objects before composing the final prompt.
- Insert CKL context between framework instructions and user material.
- Add config switches: `canonical_library.enabled`, `canonical_library.max_results`, `canonical_library.max_context_tokens`, `canonical_library.include_placeholders`, `canonical_library.allowed_statuses`.
- Exclude placeholder and unapproved material from production answers by default.
- Show retrieved object IDs in debug mode.

Exit criteria: Asking about Shechem, covenant, Abraham, or Joshua retrieves and injects the appropriate canonical records automatically.

Status: in progress.

## Phase 9 - Content Authoring Pipeline

Goal: Stop hand-editing hundreds of JSON files without guardrails.

- Create `tools/ckl_create.py`, `tools/ckl_validate.py`, `tools/ckl_manifest.py`, `tools/ckl_report.py`, and `tools/ckl_migrate.py`.
- Support new-object templates, single-object validation, full-library validation, manifest regeneration, duplicate alias detection, duplicate ID detection, unresolved relationship detection, broken Scripture reference detection, missing required content detection, content and review status reporting, safe schema migration, and consistent JSON formatting.

Exit criteria: A contributor can create, validate, link, and submit an object without understanding the Python internals.

Status: complete.

## Phase 10 - Core Content Population

Goal: Populate the highest-value material first instead of trying to finish all 610 objects at once.

- Wave 1: Biblical backbone. Start with roughly 40 to 60 objects, centered on Genesis, Exodus, Deuteronomy, Joshua, Psalms, Isaiah, Matthew, John, Acts, Romans, Hebrews, Revelation, Abraham, Moses, David, Jesus, Paul, Jerusalem, Shechem, Egypt, Sinai, Babylon, Covenant, Kingdom of God, Temple, Exile, Creation, Fall, Passover, Crucifixion, Resurrection, Holy Spirit, Torah, Messiah, Sacrifice, Priesthood, Second Temple, and Ancient Near East.
- Populate, at minimum, summary, primary Scripture references, historical context, literary context, related objects, sources, common questions, interpretive cautions, and content and review status.
- Wave 2: Complete all 66 Bible-book records with authorship positions, likely date ranges, original audience, historical setting, genre, structure, major themes, canonical placement, key people, key places, key events, major interpretive disputes, and primary sources.
- Wave 3: People, places, events, and institutions.
- Wave 4: Theology, themes, prophecy, word studies, archaeology, and FAQ.

Status: complete. Wave 1 now contains 113 curated objects covering the core biblical backbone and FAQ bridge layer: Abraham, Moses, Joshua son of Nun, David, Jesus, Paul, Genesis, Exodus, Deuteronomy, Joshua, Psalms, Isaiah, Matthew, John, Acts, Romans, Hebrews, Revelation, Jerusalem, Shechem, Egypt, Mount Sinai, Babylon, covenant, kingdom, temple, exile, creation, fall, Passover, crucifixion, resurrection, Holy Spirit, Torah, Messiah, sacrifice, priesthood, tabernacle, second temple, new covenant, and the bridge FAQ anchors. Wave 2 Bible-book records are complete. Wave 3 covers the curated people, places, events, and institutions layer. Wave 4 now populates theology, themes, prophecy, word studies, archaeology, and FAQ.

Exit criteria: The most common BHF questions return genuinely useful curated context without relying on model memory.

## Phase 11 - Sources and Scholarly Governance

Goal: Ensure CKL does not become an AI-generated fact pile.

- Treat Scripture references as primary anchors.
- Require reputable academic sources for historical claims.
- Require excavation reports, museums, or recognized academic publications for archaeological claims.
- Require lexicons or grammars for language claims.
- Label disputed claims as disputed.
- Keep confessional conclusions from masquerading as scholarly consensus.
- Avoid relying on unsourced websites as authoritative references.
- Enforce governance rules for `placeholder`, `draft`, `complete`, `approved`, and `deprecated` states.
- Require at least one reviewer for basic factual objects and two reviewers for contested theological or historical objects.
- Require a review date, a confidence rating, and documented source support.

Exit criteria: Production retrieval only returns content meeting an explicit review policy.

## Phase 12 - Relationship Graph and Scripture Index

Goal: Turn isolated objects into an interconnected biblical knowledge graph.

- Audit bidirectional relationships and surface one-way links for review.
- Support relationship types such as `person-in-event`, `event-at-place`, `covenant-member`, `quotation-of`, `allusion-to`, `fulfills`, `contrasts-with`, `typological-connection`, and `historical-background`.
- Parse Scripture references and normalize book, chapter, and verse forms.
- Support reverse Scripture lookup such as "Which objects relate to Joshua 24?".
- Traverse the graph from one object to another, including chains such as Shechem -> Abraham -> covenant -> Joshua covenant renewal.
- Expand related objects with depth and token limits.
- Protect against circular references.

Exit criteria: A question about Joshua 24 can retrieve Joshua, Shechem, covenant renewal, Abraham, Joseph's burial, and relevant institutional context through relationships rather than keyword coincidence.

Status: complete.

## Phase 13 - Better Retrieval

Goal: Move beyond exact keyword overlap while remaining deterministic and local-first.

- Implement retrieval in this order: Scripture-reference retrieval, category-aware retrieval, phrase matching, fuzzy alias matching, relationship expansion, BM25 or full-text retrieval, optional local embeddings, and hybrid ranking.
- Combine scores from exact match, Scripture match, weighted keyword score, relationship relevance, semantic similarity, importance, and review or confidence modifier.
- Keep embedding support optional so CKL continues working completely offline without a vector database.
- Allow later backends such as SQLite FTS5, a small local embedding model, NumPy or SQLite vector storage, and optional external vector backends.

Status: complete.

Exit criteria: Questions such as "Why did Israel renew the covenant where Abraham first entered the land?" retrieve Shechem and Joshua 24 even when the exact title is never mentioned.

## Phase 14 - Token Budgeting and Context Compression

Goal: Deliver useful knowledge without replacing one form of prompt bloat with another.

- Track per-object estimated token counts.
- Assign field-level inclusion priorities.
- Add answer-mode-aware context for concise, study, teaching, and scholar modes.
- Make relationship expansion token-aware.
- Remove duplicate facts.
- Compact sources.
- Build progressive context tiers.

Exit criteria: Small models receive compact factual context, while scholar mode receives deeper material from the same objects.

## Phase 15 - Evaluation and Regression Testing

Goal: Prove that CKL improves answers instead of assuming it does.

- Build retrieval fixtures for exact IDs, aliases, alternate spellings, ambiguous people, ambiguous places, Scripture references, theological themes, multi-object questions, relationship expansion, empty queries, malformed queries, status filtering, and token-budget truncation.
- Compare answers from BHF without CKL, BHF with placeholder-only CKL, BHF with curated CKL, and large models versus local small models.
- Measure retrieval precision, retrieval recall, unsupported factual claims, source utilization, token count, latency, local-model answer quality, and answer consistency across repeated runs.
- Add tests to ensure CKL does not dictate theology or flatten interpretive disagreements.

Exit criteria: A repeatable evaluation demonstrates lower hallucination rates and better historical and contextual accuracy.

Status: complete.

## Phase 16 - Public Answer Cache

Goal: Reuse reviewed answers for common questions without bypassing the framework.

- Use normalized question keys.
- Track answer-mode variations.
- Store CKL version fingerprint and framework version fingerprint.
- Store object dependency lists.
- Track review and approval state.
- Add expiration and invalidation.
- Record quality score and usage count.
- Detect stale answers when source objects change.

Exit criteria: Frequently asked, reviewed questions can bypass most generation while still remaining traceable to CKL objects and versions.

Status: complete.

## Phase 17 - Web and Reader Integration

Goal: Make the library visible and useful in the existing study interface.

- Add a Canonical Context panel.
- Show retrieved-object badges.
- Surface related people, places, events, and themes.
- Make Scripture references clickable.
- Add a source viewer.
- Show confidence and review indicators.
- Explain why an object was retrieved.
- Add an object browser and search interface.
- Add an admin or editor view for draft objects.
- Link study notes to canonical object IDs.

Exit criteria: The local reader becomes a browsable biblical knowledge system, not merely a chat interface.

## Phase 18 - Packaging, Versioning, and Release

Goal: Make CKL a stable framework component.

- Package data so JSON ships with Python distributions.
- Add a CKL version command.
- Generate manifests during release.
- Define a schema migration policy.
- Add changelog entries.
- Add backward-compatibility tests.
- Add CI validation.
- Update documentation and sample integrations.
- Add release artifact checks.
- Add contributor review documentation.
- Create the initial stable CKL release tag.

Exit criteria: Cloning, installing, or packaging BHF produces the same validated CKL inventory everywhere.

Status: complete. The stable release tag is `v0.2.0`.

## Immediate Next Move

1. Treat this roadmap as the handoff note for future CKL maintenance and retrieval work.
2. Add new backlog items only if later sessions identify missing coverage or quality gaps.
3. Re-run validation and evaluation after any future content changes.

## Execution Log

| Phase | Status | Resume point |
| --- | --- | --- |
| 7 - CKL Retrieval Foundation | complete | CKL package exists, but runtime integration is still pending |
| 8 - Runtime Integration | complete | CKL is wired into agent startup, retrieval, and prompt building |
| 9 - Content Authoring Pipeline | complete | CKL create, validate, manifest, report, and migrate tools are in place |
| 10 - Core Content Population | complete | Wave 1 populated 113 curated objects; Wave 2 book records are complete; Wave 3 people, places, events, and institutions are populated; Wave 4 theology, themes, prophecy, word studies, archaeology, and FAQ are populated and validated |
| 11 - Sources and Scholarly Governance | complete | Safe governance defaults are in place and approved content now requires structured source support |
| 12 - Relationship Graph and Scripture Index | complete | Scripture reverse lookup, graph tracing, and reverse-link audits are wired into CKL context retrieval |
| 13 - Better Retrieval | complete | Add hybrid retrieval and optional semantic search |
| 14 - Token Budgeting and Context Compression | complete | Add tiered, token-aware context assembly |
| 15 - Evaluation and Regression Testing | complete | Metadata-aware regression suite seeded; compare CKL-enabled, filtered, and disabled runs |
| 16 - Public Answer Cache | complete | Cache approved answers with version fingerprints |
| 17 - Web and Reader Integration | complete | Surface canonical context in the UI and add the draft editor view |
| 18 - Packaging, Versioning, and Release | complete | Packaging metadata, version command, CI artifact checks, docs, and the stable release tag are in place |

Reference anchors: `framework/books/genesis.md`, `framework/books/revelation.md`.
