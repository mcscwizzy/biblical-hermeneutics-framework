# NE-11A recommendations for NE-11B and NE-11C

## What the audit establishes

**Strong verified connections are mostly already visible in Narrative Explorer’s Related Biblical Passages section.** The clearest confirmed visibility gap is in Study Companion: a visible, source-backed card about the Genesis 1 / John 1 bridge does not navigate to that exact verified route. Several other claim-backed routes (including Isaiah 53, Hebrews 7, and Revelation 21) are visible in the route section but are not eligible for the separate “Evidence about this passage” preview, which deliberately accepts source-identified, anchored evidence records rather than all claim records.

**Weak chapter coverage is real as CKL availability, not automatically as product failure.** The census found 132 chapters with no eligible item and one incomplete Obadiah chapter. Psalms is the largest low-eligibility area (74 chapters), followed by 2 Chronicles (14), Proverbs (12), Ezekiel (9), 1 Kings and 2 Kings (6 each), Numbers (4), 1 Chronicles and Luke (3 each), and Ecclesiastes (1). These figures identify where passage-specific research might be valuable; they do not authorize routes or imply that every chapter needs one.

**The principal research gaps are exact scope and attached evidence.** Current metadata suggests several worthwhile candidates, but it often lacks a child claim/evidence record that names both passage endpoints and has attached sources. Existing held decisions are working safeguards, not work queues that may be promoted by volume.

## NE-11B: research and curation scope

1. Review two narrow, source-backed candidates first: Psalm 22:1 / Mark 15:34 using `mark#claim:mark-crucifixion`, and Jonah 1:17 / Matthew 12:40 using `jonah#claim:jonah-three-days`. Read the exact cited sources and verify endpoints, relationship type, direction, and wording. Treat both as proposals for review, not preapproved routes.
2. Keep all seven NE-10 candidates held while targeted research is done. The best next research questions are Ezekiel 40–48 / Revelation 21–22 and Eden/tree-of-life / Revelation 21–22 because the reader already has related routes to explore and the missing piece is precise source-backed support. Exodus 12 / 1 Corinthians 5, Isaiah 43 / Exodus, and Ezekiel 37 / John 3 also need exact pair evidence before any curation decision.
3. Reconcile Psalm 110 / Acts 2 against the existing Acts 2 authored route. Do not create a duplicate bridge because a held candidate exists; compare its exact route identity, support record, scope, and provenance.
4. Resolve the Obadiah malformed reference and Roman Ephesus missing source IDs through their data owners. Those are source-integrity questions, not UI opportunities.

If a future task authorizes CKL curation, update all required identity, source, registry, manifest, and validation artifacts together and run the CKL integrity gates. This NE-11A branch does not do that work.

## NE-11C: engineering scope

Implement a small, exact-identity action from a Companion card to a route already returned by Narrative Explorer. The candidate example is the John Logos card and the existing Genesis 1 / John 1 NE-10 bridge.

- Match using the complete record key: parent CKL object ID, record kind, and local claim/evidence ID. Do not join by topic, passage string, source ID alone, headline, or card text.
- Require the target route to exist in the verified projection for the current passage. The action should open that precise destination and preserve the existing trail, history, route label, source details, and uncertainty.
- Keep the bridge’s current `interpretive_association` label. The UI must not imply direct quotation, dependence, or scholarly consensus.
- If no exact route identity is present, retain the current generic cross-reference behavior or omit the route action. Never synthesize a route from card co-occurrence.
- Add regression coverage for exact identity matching, wrong parent/record-kind rejection, hidden/held routes, source details, and passage navigation. Keep the current three discovery-card / one land-card limits and duplicate-map suppression unless a separate audit demonstrates a measured presentation problem.

Do not broaden the Narrative Explorer quick-preview selector merely to make claim-backed routes appear twice. The dedicated related-passage section already carries those routes and their provenance. If later reader research supports another surface, design it as a distinct route handoff with its own evidence and uncertainty, not as duplicated preview content.

## Duplication and overreach to avoid

- Do not add a second route for any existing authored or bridge destination without identifying a distinct, exact record and reader need.
- Do not count reciprocal endpoint views as separate NE-10 records or sum authored route rows as unique destinations.
- Do not convert scripture anchors, shared parent objects, common topics, bibliographies, or historical comparison into passage relationships.
- Do not treat a complete empty lookup as proof of no relationship, or an incomplete lookup as zero coverage.
- Do not equate comparative literature with borrowing, later reception with original meaning, or a debated interpretation with a settled claim.
- Preserve NE-6 geography safeguards, Phase B Locations paging, Phase C card allocation/relevance, retired Commentary HTTP 410 behavior, runtime API contracts, release assets, and Tyndale Open Study Notes.

## Completion boundary

This audit adds documentation and a compact deterministic chapter inventory only. It changes no CKL records, NE-9C decisions, NE-10 bridge or held-candidate records, runtime code, API contract, geography behavior, presentation behavior, or release asset. NE-11B and NE-11C remain future reviewed work; this branch is for review and must not be merged, deployed, or used to start those phases without separate authorization.
