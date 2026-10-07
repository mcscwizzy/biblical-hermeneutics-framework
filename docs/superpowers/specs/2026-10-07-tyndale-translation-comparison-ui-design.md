# Tyndale and Translation Comparison UI Design

## Goal

Separate BHF Context, Tyndale Study Notes, and Scripture translation comparison in the reader while repairing the BHF Context `compare_translations` action.

## User-visible boundaries

- **BHF Context** remains the CKL-backed BHF Commentary card and retains its evidence, references, maps, canonical objects, and personal actions.
- **Tyndale Companion** remains the independent published Tyndale Study Notes reader pane. Its persisted resource ID `commentary`, workspace tab ID, `/api/commentary/...` endpoints, importer, local database, and offline behavior remain compatible.
- **Compare translations** opens a distinct `translation_comparison` resource in the existing Study Companion resource host. It displays Scripture text in parallel and does not route to BHF Commentary or Tyndale.

## Routing and state

The `compare_translations` study action will be an explicit case in `dispatchStudyAction()`. It will ask the Study Companion to open `translation_comparison` through its existing `openResource()` flow. That flow stores ordinary in-memory companion navigation history and uses the existing resource detail host; it creates no workspace tab and does not alter the persisted Tyndale resource ID. Back navigation returns to the previous companion overview/resource naturally.

The resource reads the active selection from `BHFStudySelection` at open time. A selected verse or range is preserved exactly. With no selected verses, it displays chapter-level context using the chapter data returned by the reader; it never writes to or fabricates state in `BHFStudySelection`.

## Translation data

The current/source translation appears first. The remaining translations come only from the existing installed/readable translation state, in its available order, with IDs deduplicated. Translation chapters are loaded through the existing reader Bible API/data abstraction and its normal cache/offline behavior. No comparison-specific loader, download, install, or import is added. This keeps bundled, imported, and device-local translations eligible when the reader already considers them readable, while excluding license-required translations that are not installed.

If one translation is readable, show its passage text plus a clear message to install or import another translation and an action into the existing translation-management/import flow. Do not duplicate importer UI.

## Presentation and accessibility

Show a clear passage reference and each translation's abbreviation/name as a semantic heading. Keep comparison sections vertically scrollable on desktop and mobile with readable narrow-screen text and no horizontal page overflow. Use existing companion buttons and focus patterns; back navigation returns focus to the initiating action when possible. Loading and unavailable/offline states use the normal companion resource status presentation.

## Naming and compatibility

New internal identifiers use `bhf_commentary`, `tyndale`, `tyndale_notes`, and `translation_comparison` where applicable. Existing public endpoints, persisted tab/resource IDs, browser storage keys, offline cache keys, and compatibility contracts are not renamed or migrated. The existing `commentary` resource ID is explicitly documented as Tyndale.

## Verification scope

Add focused regression coverage for dispatcher execution, BHF Context action routing, exact selection preservation, current-first unique readable translations, one-translation guidance, resource back behavior, responsive/accessibility markup, independent Tyndale tab/API/selection behavior, and independent BHF Commentary loading. Run the relevant existing frontend, GUI, and API tests, including existing translation selection/import coverage. Compare the recorded Commentary v1.2 release descriptor, checksum index, manifest identity, and corpus checksum root identity against their pre-change values. CKL and Commentary release artifacts are outside the transaction and must remain untouched.

## Explicit exclusions

No CKL/evidence changes, Commentary v1.2 content or release edits, Tyndale source-content edits, model calls, deployments, or automatic translation downloads/imports.
