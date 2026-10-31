# BHF UI-06 — Companion Discovery and Geography Cleanup

## Intent

Simplify the Study Companion overview and give selected-passage geography one
dedicated, navigable Places & Locations view. This is a focused UX cleanup
before the BHF plugin work begins.

## Goals

- Remove the standalone Did You Know? preview, inline Locations, inline Walk
  the Land, and People & Places preview list from the overview.
- Add one Places & Locations entry beside Explore the Narrative.
- Compose Locations, relevant CKL Biblical Places, and source-grounded Walk the
  Land in a passage-scoped resource view with empty, partial, loading, error,
  and offline states.
- Preserve exact Maps focus, CKL detail links, location pagination, accessible
  announcements, browser history, focus restoration, mobile use, and existing
  Ask BHF, Tyndale, and personal study actions.
- Avoid duplicate Places recommendations and suppress discovery projection
  requests when only removed Did You Know? cards need them.

## Non-goals and protected boundaries

- No CKL record, source, provenance, curation, bridge, fingerprint, or schema
  changes; no scholarly content changes.
- No change to the existing persisted `places` resource, Narrative Explorer
  APIs or classifications, Ask BHF handoff, Tyndale source data or licensing,
  retired Commentary HTTP 410 behavior, or deployment configuration.
- No second geography retrieval path. The view reuses the current Companion
  context and `/api/study/companion-locations` continuation contract.

## Approaches

1. **New `places_locations` resource in the current host (selected by the
   request).** Compose the already loaded context and existing location,
   discovery, and canonical-detail renderers. This preserves the current
   `places` contract, selection scope, routing, history, and retrieval path.
2. **Repurpose the existing `places` resource.** Rejected because it changes a
   persisted resource identity and conflates the canonical-place browser with
   the new combined geography view.
3. **Add a separate geography page or API pipeline.** Rejected because it
   duplicates retrieval and complicates stale-response and history behavior.

## Architecture

The overview contains a single Places & Locations card. Activating it opens a
new `places_locations` native resource. The resource renderer consumes the
current context record, keeps Maps and CKL identities separate, hides a CKL
place from the second section only when its exact CKL ID is already listed in
Locations, and keeps Walk the Land actions in their own section. Existing
resource-router sequence cancellation and Companion selection keys protect
chapter changes. Existing history state records the resource for Back/Forward.

Only Walk the Land cards may request Narrative Explorer projection for verified
relationship handoffs. Did You Know packet data and evidence remain untouched;
they simply have no overview renderer.

## Open implementation calls

- Use `relationship: "direct Scripture anchor"` to identify canonical place
  entities in the existing combined `entities.places` context list; keep maps
  out of Biblical Places and compare cross-section identity by exact CKL ID.
- Keep the existing map, canonical detail, and paged-location action callbacks.
- Add the requested before/after browser screenshots to the UI-06 UX report.
