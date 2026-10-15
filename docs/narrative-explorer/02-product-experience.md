# Narrative Explorer: Product Experience

## Product intent

Narrative Explorer helps a reader discover what a passage connects to in Scripture, history, geography, and material evidence without requiring generated chapter commentary. Ask BHF remains the place for a reader's deeper interpretive question. Evidence labels, links, and source views distinguish what a text or artifact says from a reconstruction about it.

The experience belongs in the existing passage-first Study Companion. The Bible passage remains visible and notes, highlights, lexicon, translation comparison, saved passages, maps, and Tyndale Study Notes remain familiar workflows.

## Entry and journey

1. The reader chooses a chapter or passage in the existing Bible reader.
2. The Companion loads its current passage context and offers **Explore the Narrative** as the primary evidence-navigation action.
3. An overview shows the narrative location and only categories that have relevant records. Each card gives a short description, availability label, and a count when backed by a completed query.
4. The reader opens a category or individual subject.
5. The detail view shows the authored claim, passage relationship, source, confidence, uncertainty, and explicit connection basis. Evidence details are expandable.
6. The reader follows a cited passage, source, place, event, or connected topic. A breadcrumb and Companion browser history return to the original passage.
7. The reader may open **Ask BHF** and type a question. NE-1 keeps the current handoff unchanged.

There is no required AI request. The experience does not manufacture a story summary when CKL has no authored or mechanically supported narrative data.

## Overview

### First screen

The overview keeps a calm hierarchy:

- **Passage and narrative location:** current chapter, book section, and explicitly represented preceding/following events.
- **Evidence categories:** Biblical Narrative, Archaeology & Ancient History, Biblical Geography, Divine Council & Cosmic Geography, Themes & Biblical Connections, and People, Events & Relationships.
- **Reading actions:** note, save-passage, highlight, and Ask BHF actions remain reachable.

For an everyday reader, show a short label and no more than one or two evidence highlights per category. Evidence depth, alternative interpretations, and bibliography appear after the reader opens a card. Do not use a single theological conclusion as the overview's lead.

Each card distinguishes:

- **Available:** the relevant source query completed and returned records.
- **Partial:** records exist, but a named subdomain or connection is not represented.
- **Not represented in CKL:** the completed CKL and domain lookups returned no eligible record for that category.
- **Unknown:** retrieval failed or did not complete, so availability cannot be stated.

Zero records must not be presented as a theological conclusion or proof that no historical evidence exists.

## Exploration categories

### Biblical Narrative

Show authored canonical-story relationships and mechanically supported adjacent events. Examples include creation and Eden, flood and dispersion, Abraham and the nations, Exodus and covenant, sacred space and temple, exile and restoration. A story trail labels the underlying relation and shows its source record. Do not synthesize a complete theological interpretation from a sequence of themes.

### Archaeology & Ancient History

Begin with a concise artifact/source card, then disclose:

- What the artifact or ancient source actually attests.
- The record's date, dating basis, provenance, and present location when recorded.
- The exact passage relationship: direct, contextual, comparative, or disputed.
- Source citations, scholarly uncertainty, and what the record does not establish when the source data supports it.

Keep an ancient literary comparator, manuscript witness, excavation context, and archaeological artifact recognizable as different evidence kinds. Proximity or motif resemblance is not proof of a biblical event.

### Biblical Geography

Reuse map and place records for named places, regions, kingdoms, routes, historical periods, and source-linked identifications. A map marker opens the place record with period, source, textual links, and identification status. If a site is not identified or its identity is disputed, show the textual name and uncertainty without a precise point marker. Do not generate coordinates.

### Divine Council & Cosmic Geography

Use a dedicated category or lens for textual descriptions of heavenly assemblies, divine beings, heaven and earth, sacred mountains, Eden, divine presence, temple/sacred space, nations, wilderness, sea, and chaos imagery.

Show textual observations, ancient comparative sources, later reception, and competing interpretations in distinct sections. The lens is an exploration route, not a verdict: it must not imply that a divine-council reading is the required meaning of every passage. Cosmic and sacred-space language receives a **textual/conceptual** view and is not automatically placed on a physical map.

### Themes & Biblical Connections

Display a connection trail with a visible type and basis. Use exact passage or evidence links and support reverse navigation when an explicit reciprocal or shared edge exists. A theme label alone does not establish quotation or literary dependence.

### People, Events & Relationships

Reuse CKL identities and relationship records for named people, historical figures, genealogies, events, kingdoms, and institutions. Label textual relationship records separately from historical reconstructions. Offer a relationship trail only when the underlying record contains the edge or an approved projection rule can explain it.

## Details, sources, and navigation

- Evidence cards use an explicit **Show evidence** disclosure. The collapsed state shows a reader-safe sentence and short basis; expanded details show exact references, source labels/type, date/locator, claim certainty, dispute/review status, and related record IDs.
- **Sources** opens a bibliography view, grouped by primary text, artifact/catalog, excavation report, academic source, or reference work when the source record supports that grouping. Missing author, publisher, date, or locator remains unreported.
- Breadcrumbs preserve the originating passage: Genesis 6 → Divine council / cosmic geography → Sons of God evidence. A back control returns to the previous detail; a persistent **Return to Genesis 6** action returns to the original selection.
- Passage and subject links open the reader at the cited reference or reopen the matching CKL/map/archaeology detail. External source links use the stored URL and are visibly external.
- A link shows its source and connection type. If the opposite edge is not represented, show a one-way link rather than silently inventing a reciprocal relationship.

## Screen and state specification

| State | Desktop | Mobile |
|---|---|---|
| No passage selected | Keep the Companion in its existing general-explore mode; explain that passage-specific evidence appears after a selection. | Keep the sheet collapsed or in its current peek state; selecting a passage opens the overview. |
| Loading | Keep the passage header and show labeled skeleton cards with a live status announcement. | Keep sheet controls reachable; show one-column skeleton cards and do not jump scroll position. |
| Ready with evidence | Show a two-column overview/card grid beside the reader; the native resource host shows one focused detail at a time. | Show one-column cards in the existing sheet. Use a clear back control and compact passage label. |
| Partial data | Show available sections and explain missing subdomains. Do not hide usable categories because another query failed. | Same content in one column, with status text before related cards. |
| No represented data | Say “No linked records are represented here yet” and offer neighboring categories or Ask BHF. | Same message and actions; keep buttons visible without horizontal scrolling. |
| Retrieval unknown/offline | Show cached results with an offline/stale label when available; otherwise state that availability could not be checked. | Show the cached state inline and retain back, reader, and personal-study actions. |
| Evidence detail | Show a short claim first, then expandable source, uncertainty, and relation sections. | Keep native disclosure behavior; maintain a return-to-passage action at the top of the sheet. |
| Nested destination | Record the destination in Companion history and keep a return-to-passage action visible. | Back returns one step; return-to-passage remains reachable. |

## Responsive behavior, accessibility, and offline use

- Continue the current desktop dock and mobile sheet patterns. Use companion-history.js, companion-sheet.js, and companion-viewport.js rather than adding a second navigation shell.
- Keep semantic headings, buttons for actions, links for destinations, and native disclosure semantics. Every icon control has an accessible name. Status changes use a live-region pattern.
- Preserve keyboard order, visible focus, Escape/back behavior, focus restoration to the opening control, and comfortable touch targets. Never rely on color alone for confidence, dispute, physical/cosmic classification, or availability.
- Continue service-worker caching and offline packs for local CKL/evidence, map, archaeology, and source data. Store only public/read-only projections in shared API caches. Device notes remain in their current local vault/storage and are not included in the projection.
- On an offline cache miss, say that the section is unavailable offline. Do not show an empty result as if a live query completed.

## Existing workflows retained

Narrative Explorer does not replace the Tyndale Companion tab, note/highlight actions, lexicon, translation comparison, saved passages, Bible navigation, or map and archaeology workspaces. The BHF-generated Commentary card may coexist during rollout and later move to archived access under the phased transition plan.
