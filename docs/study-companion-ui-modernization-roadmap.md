# BHF UI Modernization Roadmap

UI-01 establishes the Study Companion hierarchy: passage actions, Ask BHF, a
reserved contextual Tyndale card slot, and a Dig Deeper area for passage research.
The follow-on transactions are:

## UI-02: Tyndale First-Class Reader Integration

Add a contextual Tyndale card in the reserved Study Companion position. On a
chapter 1 view with no verse selection, show the matching book introduction.
When verses or a range are selected, show the matching notes and keep full note
access available. Audit and correct book-introduction matching so the chosen
introduction belongs to the selected book. Retain attribution, offline
behavior, the current Tyndale API, and the existing workspace tab. Do not
change the Tyndale data or importer as part of UI-01.

## UI-03: Narrative Explorer UX Redesign

Replace the stacked evidence inventory with a guided discovery overview. Show
six recognizable exploration categories, clear connection trails, readable
summaries, expandable evidence, and navigation that works on mobile. Keep
source relationships, provenance, evidence classifications, uncertainty, and
all existing API contracts intact. Keep NE-9C curations and NE-10 passage
bridges read-only.

## UI-04: Integrated Verification and Release

Run frontend, Python, browser, accessibility, mobile, performance, packaging,
and regression checks across the reader, Tyndale card, and Narrative Explorer.
Review the complete experience manually, including loading, missing-data,
offline, and feature-disabled states. Resolve release-blocking findings before
any production release; production release is a separate approval.

The intended sequence is UI-02, UI-03, then UI-04. Each implementation should
preserve BHF source attribution, the Ask BHF handoff contract, existing
Narrative Explorer routes and feature gates, and the retired commentary
endpoints' HTTP 410 behavior.

## UI-07: Reader-First Research Consolidation

Keep Scripture, personal study, Ask BHF, and contextual Tyndale notes ahead of
research discovery. Reduce the selected-passage overview to Explore the
Narrative and Places & Locations. Add a focused Understand the Passage view
inside Narrative Explorer for the five existing Companion context summaries,
and provide secondary access to the existing research libraries and passage
tools. Preserve direct routes, research services, Narrative Explorer evidence
and relationship semantics, source disclosures, and feature-disabled access.
See the [UI-07 design](superpowers/specs/2026-10-31-bhf-study-companion-ui07-design.md),
[implementation plan](superpowers/plans/2026-10-31-bhf-study-companion-ui07.md),
and [UX report with browser captures](ui-modernization/ui07/ux-change-report.md).
