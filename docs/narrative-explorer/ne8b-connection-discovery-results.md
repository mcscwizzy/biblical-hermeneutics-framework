# NE-8B connection discovery — local results

## Before and after

**Before:** readers opened a passage overview with general guidance and section cards ordered by stable record IDs. They had to choose “Inspect evidence and connections” before seeing an authored edge's recorded basis. Scripture anchors with an uncategorized CKL label could look like unclassified relationships.

**After:** a compact “Explore related passages and evidence” section appears above the existing sections. It selects at most three source-backed CKL evidence records from the current projection, prefers records already represented in focused evidence sections, and uses the Geography section's two passage-specific records together when both are available. Each card shows the authored basis note, evidence category, and Scripture/comparison anchor scope before the existing inspect action. Source IDs, original relationship labels, status, uncertainty, and all projected edge provenance remain in the existing expandable source details.

The detail renderer now labels a `ckl_scripture_anchor` as a Scripture or comparative passage anchor. It explains that an anchor marks evidence scope and does not establish a cross-passage literary or theological relationship. Unclassified `ckl_related_*` relationships keep their existing descriptive-association warning.

### Example reader journeys

- **Genesis 6:1–4:** the preview leads with the disputed “sons of God” positions, then later Watchers reception, then the Gilgamesh comparison. The Watchers card explicitly says the record is later reception and preserves the CKL `contemporary` temporal-metadata review caution. The comparison card says it does not establish borrowing or dependence.
- **Psalm 82:** the poem's own assembly-language record remains distinct from the Ugaritic comparison. Its visible qualification separates the explicit wording from disputed claims about the judged figures and background. The comparison retains the authored note that it does not decide the poem's referents.
- **Deuteronomy 32:8–9:** the manuscript/textual-witness record is identified as such; readers see that the witness differences are documented while the earliest wording and implications remain debated. The textual-variant status stays expandable and is not turned into a theological conclusion.
- **Genesis 2:** the two geography records surface together. The garden card keeps sacred-space analogy qualified as interpretation; the rivers card states that the text supplies no coordinates and does not establish a recoverable Eden location.

The cards use the existing “Inspect evidence and connections” action and evidence detail. The existing history, return-to-origin, one-way/reciprocal, cycle, and three-hop behavior were not changed.

## Source and hermeneutical safeguards

- A preview candidate must already be an evidence record in the projection, have CKL source IDs or source entries, have a passage anchor, and have an outgoing `ckl_related_object` or `ckl_related_evidence` edge with an authored basis note.
- `ckl_scripture_anchor` edges are never treated as the candidate's relationship basis. Direct and comparative anchors are displayed separately and described as evidence scope.
- The component does not create edges, alter CKL records, infer borrowing, derive coordinates, or invoke an AI service. Comparative, later-reception, disputed, partial, and unclassified states retain explicit qualifications.
- Empty, partial, and incomplete CKL lookups receive different availability text. A partial result with previews is also marked partial.
- No feature default or feature-flag configuration changed.

## Local acceptance

| Check | Result |
| --- | --- |
| `npm test` | 12 frontend test files passed. Includes source identity/provenance, trail hop/cycle rules, offline retry, and map/front-end regression tests. |
| `tests/test_narrative_explorer_projection.py` | 53 passed. |
| `tests/test_narrative_explorer_api.py` + `tests/test_narrative_explorer_ui_config.py` | 23 passed; the feature-default contract remains unchanged. |
| Firefox browser: NE-8B desktop/mobile preview | Passed. Three-card bound, Watchers temporal caution, responsive width, keyboard activation of Inspect, keyboard expansion of provenance, and return-to-origin were exercised. |
| Firefox browser: four-passage NE-8A journey | Passed for Genesis 6, Psalm 82, Deuteronomy 32, and Genesis 2. |
| Existing Ask BHF / Compare Translations and mobile dock journey | Passed. |
| Notes/highlights route and Maps workspace event-wiring contract | Passed. |
| Tyndale Notes + translation comparison browser test | Skipped because `.bhf/commentary.sqlite` is absent. |
| Populated Maps browser search | Did not complete: the browser test timed out waiting for Jerusalem results in the temporary test database. `.bhf-data/study.sqlite` and `.bhf/ckl.sqlite` are absent from this worktree. The Maps workspace opened, but no passage-specific Maps coverage was tested for Narrative Explorer. |

Firefox was run with the cached local geckodriver because Selenium Manager is unavailable in this environment. The preview screenshots show the feature inside the running reader app:

- Desktop: `/tmp/ne8b-connection-preview-desktop.png`
- Mobile width (Firefox's narrow viewport triggers the mobile sheet): `/tmp/ne8b-connection-preview-mobile.png`
- Preview section crops: `/tmp/ne8b-connection-discovery-desktop.png` and `/tmp/ne8b-connection-discovery-mobile.png`

The worktree's CKL inventory fingerprint is `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`, matching the documented baseline. There are no CKL file changes. No Study or CKL SQLite database exists in this worktree to integrity-check; the browser API tests use a temporary test database. No CKL or commentary records were written.

## Remaining gaps

- Passage-specific Maps and archaeology coverage for Genesis 2 remains unverified because the Study database is missing. The UI reports returned-source availability and does not infer a place or coordinate.
- Tyndale Commentary continuity remains unverified in the browser because the local Commentary database is missing.
- The mobile screenshot uses Firefox's narrow viewport; Firefox clamps the CSS viewport wider than the requested 390px, while still activating the application's mobile breakpoint. The mobile sheet and no-horizontal-overflow checks passed.
