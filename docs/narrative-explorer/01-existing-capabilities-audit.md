# Narrative Explorer: Existing Capabilities Audit

## Scope and baseline

This is a read-only audit for design transaction NE-1. It does not change runtime behavior, CKL, source evidence, release data, or Ask BHF.

- Repository baseline: origin/master at b9812fd0236cc2341fd4b777fe92b009dfb05c8b.
- The requested Genesis 1 corrective promotion is the current master tip. Fetch found no commits after it.
- Design branch: design/bhf-narrative-explorer.
- Root AGENTS.md contains Commentary v1.1 pipeline rules. NE-1 does not operate that pipeline.

## Reader and Study Companion

### Existing functionality

- bhf_web/templates/index.html contains the Bible reader and a passage-first Study Companion. The companion is a mobile sheet with peek, study, and full states and a desktop dock. It already has recommended resources, entity chips, a native resource detail host, Ask BHF, and history-aware back navigation.
- bhf_web/static/study-companion.js owns passage selection, companion state, resource routing, the Ask BHF modal, note and save actions, and workspace integration. companion-sheet.js, companion-viewport.js, and companion-history.js supply responsive sheet, viewport, and browser-history behavior.
- bhf_web/services/companion_context.py backs GET /api/study/companion-context. Its response includes reference, scope, resource availability/counts, entities, compact summaries, deterministic narration, a presentation packet, evidence used by visible cards, and subsystem status.
- bhf_web/static/companion-context.js and companion-context-controller.js cache and normalize that response. The in-memory cache is keyed by passage and translation, with resource-change invalidation.
- companion-discoveries.js displays packet cards only when their evidence IDs resolve to included evidence. It has three card types today: did_you_know, walk_the_land, and why_it_matters.
- resource-router.js opens passage-specific resources and canonical detail views. It already has compact loading, error, and back-to-overview states.
- Notes, highlights, saved passages/studies, Tyndale Study Notes, lexicon, translation comparison, and maps are separate reader workflows. Device-local notes and saved studies are not sent through the Ask BHF handoff.

### Reuse potential

Keep the existing Study Companion as the host for the chapter-first experience. Reuse its selection model, sheet/dock, resource host, browser history, focus restoration, cache invalidation, resource availability cards, accessible controls, offline asset registration, and personal-study actions. Add a read-only adapter that turns existing evidence records into Narrative Explorer sections; do not create a second evidence store or replace personal workflows.

## CKL records, retrieval, and evidence graph

### Existing functionality

- CKL objects are authored as JSON under framework/canonical_library/objects/ and validated by framework/canonical_library/schema.py. The object model includes typed relationships, Scripture references, sources, claims, typed evidence items, temporal scope, context applicability, review status, and human-review metadata.
- framework/canonical_library/evidence_models.py defines evidence assertions (primary-evidence, secondary-evidence, scholarly-reconstruction, inference), confidence, certainty, dispute status, passage relationship, temporal relation, external-domain references, and entity/value evidence targets.
- framework/canonical_library/evidence_graph.py computes graph edges from CKL records. It projects passage → subject → claim → evidence → source, adds geography, period, and external-domain edges, and namespaces local claim/evidence/source IDs under the parent object ID. It does not create a second graph database.
- bhf_agent.ckl and framework/canonical_library/repository.py expose JSON and SQLite repositories, Scripture-reference retrieval, object identity lookup, relationship retrieval, and stale-database fallback.
- GET /api/canonical/entities-for-passage, GET /api/canonical/search, and GET /api/canonical/objects/{object_id} are registered in bhf_web/routes/canonical.py. The passage-entity response is intentionally compact. Object detail includes source, Scripture-reference, relationship, and evidence counts and serialized object data.
- Passage eligibility is explicit in bhf_agent/presentation/eligibility.py: a record needs overlapping Scripture anchors and must pass the semantic-misanchor check. canonical_narration_material can reduce a non-eligible parent to nested claims or notes whose anchors overlap the requested passage.

### Reuse potential

Use the current CKL repositories, object IDs, claims, sources, typed evidence, passage eligibility, relationships, and graph projection as the source of truth. Resolve cross-domain links through stable CKL IDs or existing map and archaeology IDs. Use parent-qualified claim and evidence IDs in any public projection, following the namespace convention in evidence_graph.py.

### Verified gaps

- Legacy related_objects relationship names are free strings; intertextuality and some cross-references are plain text. They do not consistently encode the requested link taxonomy or reverse-navigation target.
- CanonicalScriptureReference.relationship has a useful but narrower controlled vocabulary (primary, supporting, background, quotation, allusion, typology, fulfillment, contrast, parallel). CanonicalEvidencePassageLink.relationship uses another vocabulary (direct, contextual, comparative, contrast, disputed).
- Compact Companion entity summaries omit claim and source detail. A second detail request can return the full CKL object, but a passage-level projection binding one claim to its evidence and sources is not a shared API contract.
- The Companion currently puts only CKL objects whose type is theme in entities.themes. Passage-anchored cultural_background records remain available under canonical summaries and narration but are not theme entities.
- CompanionContextService._canonical_context collects object-level cross_references and intertextuality from every eligible parent before truncating the user-facing list. Those strings are not filtered to the current claim. This produced unrelated Genesis-wide cross-references in the Genesis 6 census.

## Deterministic evidence presentation

### Existing functionality

- bhf_agent/presentation/evidence.py builds EvidenceBundle v1.0 from CKL, map, and archaeology inputs. It applies passage eligibility, preserves source and object provenance, and uses passage-specific map and archaeology records.
- bhf_agent/presentation/models.py defines evidence items, entities, geography references, a stable evidence hash, and packet/card schemas. Cards carry evidence IDs, confidence, interpretation level, map focus, and typed navigation actions.
- bhf_agent/presentation/validation.py checks evidence IDs, entity IDs, confidence ceilings, disputed-as-fact cases, unsupported dates, map references, action references, and significance evidence.
- framework/canonical_library/narration/ deterministically ranks and realizes authored CKL observations, claims, interpretive notes, sources, uncertainty, and provenance. NarratedSentence retains claim IDs, source IDs/details, Scripture references, evidence IDs, parent IDs, and review status.
- The normal web path calls the local presentation path; it does not call a paid rendering provider. The packet is a compact presentation projection, not CKL authoring.

### Reuse potential and limits

Reuse the evidence bundle, deterministic narrator, packet validator, and source-traceability rules. They can feed progressive evidence cards and compact overview counts. Narrative Explorer needs a broader, typed, read-only projection than the current three-card packet; that packet is not a replacement database or a complete chapter inventory.

## Geography and archaeology

### Existing functionality

- bhf_web/routes/maps.py exposes map catalogs, biblical places, archaeology markers, routes, historical and political layers, passage place/route resolution, related passages, and map-study actions.
- bhf_web/map_service.py, map matching/serialization services, and bhf_agent/study_db.py reuse SQLite tables for place identities, Scripture links, route references, periods, coordinates, source links, and confidence labels. bhf_web/static/maps/ renders markers and routes. JourneyMapData.js and static/data/journeys/ hold authored journey datasets.
- bhf_web/routes/archaeology.py and bhf_agent/archaeology_service.py expose archaeology browsing, search, passage links, item/site detail, sources, periods, confidence, cautions, and linked media. bhf_agent/study_db.py stores archaeology records and cross-domain CKL links.
- /api/study/companion-context joins passage-linked map places/routes and archaeology summaries into its evidence bundle. Full map and archaeology workspaces remain available from the Companion.

### Verified gaps

- Map confidence accompanies a location record, but the data contract does not clearly separate confidence of a biblical-name/reference match from confidence that a physical identification is correct. The local database returns point coordinates for Eden and named rivers in Genesis 2, and an Eden point for Genesis 3. Do not turn those coordinates into a settled Garden of Eden identification.
- The six pilots have no direct linked record in the Study DB archaeology passage resolver. Some CKL records contain useful ancient-text or manuscript evidence; that is not the same as an item linked through the archaeology service.
- The local map database has one route and two route references overall; none of the six pilot chapters has a route reference.
- Passage maps are chapter-indexed when a verse range is not supplied. A chapter-level result is not evidence that each mapped place is equally relevant to every verse.
- Cosmic or sacred-space language in CKL is text and concept evidence. It has no basis for being turned into coordinates or a physical map marker.

## Conversational study and hermeneutical boundary

### Existing functionality

- bhf_web/static/assistant-handoff.js creates a question containing the selected passage reference and the reader's typed question. It prepares visible text, copies it, and opens the configured external BHF assistant.
- The current handoff is a user-mediated copy/open flow. It does not send a CKL topic, evidence bundle, notes, or study history automatically.
- Ask BHF's hermeneutical pipeline, prompts, and model handoff live outside this reader handoff code. docs/architecture.md describes the deterministic reader and external conversational assistant boundary.

### NE-1 boundary

Leave all Ask BHF principles, prompts, model routing, and current handoff behavior unchanged. A future, separately designed interface may offer the reader an explicit choice to include a selected passage, topic/evidence IDs, source references, and a typed question. It must remain distinct from the present handoff and must never include private notes or study history by default.

## Architectural summary

**Existing:** passage selection and responsive Study Companion; CKL identity/retrieval; evidence graph; deterministic narration and card validation; map and archaeology domains; Tyndale and BHF commentary paths; device-local study state; offline caches; external Ask BHF handoff.

**Verified gaps:** source- and claim-bound passage projection; consistent connection types and reciprocal navigation; coverage state that separates absent data from query failure; safe physical-location identification status; separate cosmic-geography classification; unscoped object-level cross-reference aggregation; theme-only UI classification hides relevant cultural-background evidence.

**Proposed:** a versioned read-only projection adapter over these existing systems and a feature-flagged Narrative Explorer mode inside the current Companion.

**Future:** a typed, user-confirmed evidence-context handoff to Ask BHF; any CKL curation or renderer retirement requires its own transaction.
