# Before and After Reader Experience

## Cases and capture method

The same selected passage journeys were captured on ED-6 baseline and ED-7
branch in real Chromium: Genesis 6, Genesis 12, Psalm 82, Deuteronomy 32:8–9,
Psalm 145:13, Jonah 1:17→Matthew 12:40, 1 Corinthians 11:3, 1 John 3:19–24,
John 10:22, and 1 Kings 2. Genesis 6, Psalm 82, and 1 Kings 2 were also checked
at 390px and 320px. Nahum 3:8–9 and Proverbs 15:25 were added because they are
the two audited featured discoveries. See the row-level
[`journey-metrics.json`](screenshots/journey-metrics.json) and representative
[before](screenshots/before/) and [after](screenshots/after/) screenshots.

The initial journey values below describe visible page content, not the count
of records returned by the API projection. For the ten prescribed ED-5/ED-6
passages, the overview retained six topic cards in both builds and displayed
zero research cards as initial discovery cards. The baseline additionally
printed query-state labels and linked-record counts on topic cards. ED-7 keeps
zero featured discovery cards for these ten passages, but now opens with a
positive path into study topics and original context, with verified biblical
connections offered where evidence supports them. The completed-empty 1 Kings
2 lookup retains its coverage explanation after this reader-first guidance.
All six topic cards remain free of metadata counts. The two supplementary
featured cases each display one card, for a maximum of one visible feature in
those selected cases (the policy cap is three).

## Journey comparison

| Check | ED-6 baseline | ED-7 | Evidence |
|---|---|---|---|
| Opening content on the ten prescribed passages | Six topic cards; status/count labels; no featured card | Same six categories, no lookup labels/counts; reader pathways lead when no feature qualifies | `journey-metrics.json`; Genesis 6 screenshots |
| “Additional sourced records” in overview | Technical list path present, with duplicate/low-value records possible | Removed from default journey; source search and topic paths remain | Reader clutter audit; frontend regression |
| Featured discoveries | No featured-card tier | Two total explicitly selected: Nahum 3:8–9 and Proverbs 15:25 | [Nahum](screenshots/after/nahum3-desktop-how-we-know.png), [Proverbs](screenshots/after/proverbs15-desktop-how-we-know.png) |
| Supporting source access | Existing source browsing and per-record disclosures | One “How we know” expansion from each featured card; cited works, relevant pages, and plain access limits shown without editorial workflow wording | ED-7 Chromium test; screenshots |
| Internal status/IDs on reader cards | Present in some research/connection text and the source audit labels | Not rendered on ED-7 overview or tested featured/connection card | Metrics and source/route assertions |
| Uncertainty | Some records used technical certainty and editorial metadata | Natural-language disputed/proposed/access-limit wording retained | Featured cards; ED-6 passages retain existing item qualifications |
| Verified connection | Jonah → Matthew direction and passage navigation available | Direction remains Jonah 1:17 to Matthew 12:40; “Follow a Connection” reaches destination | [route](screenshots/after/jonah-matthew-desktop-route.png), [destination](screenshots/after/jonah-matthew-desktop-destination.png) |
| 1 Kings 2 empty coverage | Completed-empty notice with “Research coverage in BHF” and count-style framing | Reader pathways lead, followed by the truthful completed-empty lookup explanation and current-coverage caveat | [desktop](screenshots/after/1kings2-desktop.png), [390px](screenshots/after/1kings2-390px.png), [320px](screenshots/after/1kings2-320px.png) |
| Responsive width | Existing page captured at desktop, 390px, and 320px | Genesis 6, Genesis 12, Psalm 82, both featured discoveries, Jonah→Matthew, and 1 Kings 2 checked at 1440px, 390px, and 320px with no horizontal overflow | `journey-metrics.json`; Chromium tests |

## Supporting sources and uncertainty

The final source-disclosure screenshots identify the cited articles and page
ranges, summarize their relevant textual material, and state the manuscript
access limits: the Qumran discussion was not compared with a 4Q385a or other
manuscript image, and the 4QProvb discussion was not checked against a fragment
image or critical edition. Incomplete citation details are stated plainly. The
tested Jonah connection keeps exact direction and destination navigation.

## Limits

These scripted checks report visible cards, labels, source disclosure,
selection state, and layout geometry. They do not measure how well a person
understands the passage, source, or uncertainty. No participant was observed.
The independent ED-6 participant pilot remains ready for actual sessions.
