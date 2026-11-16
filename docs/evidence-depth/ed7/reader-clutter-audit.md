# Reader-Facing Clutter Audit

## Method

I inspected the Narrative Explorer renderer, the related-passage view, its
CKL projection, existing ED-2 through ED-6 reader and governance records, and
the rendered baseline pages in genuine Chromium. Representative captures are
under [`screenshots/before/`](screenshots/before/) and
[`screenshots/after/`](screenshots/after/). This is a UI and source review, not
a participant study.

## Findings and disposition

| Existing presentation | Reader value | ED-7 treatment |
|---|---|---|
| `draft`, `human_review_required`, review and curation states, CKL/source IDs, and certainty internals on cards | Useful for research governance; not a substitute for whether a claim is true and not needed to understand it | Removed from ordinary reader cards; preserved in CKL and maintainer research tools |
| “Source lookup complete,” availability diagnostics, and item counts on each of six topic cards | Counts describe the query, not the passage's significance or quality | Removed from topic cards; retain the six topic routes |
| Similar claims repeated in additional sourced records and other sections | Repetition adds little and can make a passage look more settled | Remove additional-record list from the initial view; exact duplicate suppression applies to selected evidence; keep the research searchable |
| Bibliographic provenance mixed with empty metadata fields | Source attribution matters; field-by-field diagnostics distract from the cited work | Show cited works in “How we know”; replace field diagnostics with one plain limitation when details are incomplete |
| Valid but less relevant or specialist records | Can support follow-up study but need not lead the first encounter | “Available on demand” inside the existing topic flow |
| Unverified, weakly anchored, or otherwise unresolved material presented as a discovery | Risks implying reliable support | Withhold from reader promotion; retain underlying CKL records and provenance |
| Unnecessary certainty and technical relationship descriptions such as “Connection type” | Readers benefit from an observation and its actual limitation, not a registry enum | Use the explanation, relevant passages, sources, and natural-language uncertainty; retain exact directional support in connection detail |
| Content unrelated to the selected passage | Obscures what the reader opened the page to study | Feature only the exact selected passage's reviewed policy IDs; keep broader context behind topics |
| Location quick glance and geographic uncertainty | Gives useful chapter-level orientation | Preserve, including geographic qualification and source details |

## Representative screens

- [Genesis 6, baseline desktop](screenshots/before/genesis6-desktop.png) shows
  six topic cards with query status and record counts.
- [Genesis 6, ED-7 desktop](screenshots/after/genesis6-desktop.png) leads with a
  truthful empty state, then connection and study-topic choices.
- [Genesis 6, 390px](screenshots/after/genesis6-390px.png) and
  [320px](screenshots/after/genesis6-320px.png) show the same reading hierarchy
  on narrow viewports.
- [Nahum 3:8–9 source disclosure](screenshots/after/nahum3-desktop-how-we-know.png)
  shows the named article, actual source limit, and a plain note about incomplete
  bibliographic fields.
- [Jonah 1:17 connection](screenshots/after/jonah-matthew-desktop-route.png)
  shows the direction and source support before following the link.

## Six categories retained

Biblical Narrative, Archaeology & Ancient History, Biblical Geography, Divine
Council & Cosmic Geography, Themes & Biblical Connections, and People, Events
& Relationships remain. The category cards no longer imply that more linked
records means stronger or more useful passage research. No category
simplification was justified by the acceptance evidence.
