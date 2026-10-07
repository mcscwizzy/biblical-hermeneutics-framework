# Numbers 18 — READY_FOR_HUMAN_REVIEW

## Identity

- Old evidence hash: `94b518a68787e9ca707665e95a262b0169bfb611f3cd51d8654e799ad99d204d`
- New evidence hash: `785aafb367ed47fa7eb77a2266b51348c31451de23d2cf455c6c77901dd9c6bc`
- Old synthesis hash: `81a4afab49a895a9957932a35496b7c574dc951ca032285e16f08c58c5007674`
- New synthesis hash: `462866b275503b11655d321f4286a59d16d5637e50b0ad572e61f46f921f0253`
- Candidate Commentary SHA-256: `4a2629a3e8b65a5fb99c3bbc972572e4e45a0341dcd6df46e9fdf4d8333c58c6`
- Candidate artifact: `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-dae7a68dd8db0c99/chapters/numbers_018/commentary.json`
- Old published Commentary: `.bhf-data/bhf-commentary-v1.2/numbers_018.json`
- Renderer: `gpt-5.6-terra` via `commentary-v1.2-codex-cli`; prompt `1.8`, synthesis compiler `1.1`
- Attempt interval: `2026-10-07T00:29:50.504625+00:00` – `2026-10-07T00:30:12.491571+00:00`
- Result: `validated`; approval: `NOT_APPROVED`

## Transaction A evidence delta

- Added: `source-lock-numbers-18-levites-no-territorial-inheritance`
- Added: `source-lock-numbers-18-levites-tithe-as-inheritance`
- Removed: none

## Validation

- Existing Commentary v1.2 validation: passed.

## Commentary comparison

### Published Commentary

### Context

The chapter sits within the book's larger movement; reading it alongside the surrounding account helps clarify its place in that development.

### Candidate Commentary

### Inheritance and the Levites' support

Verses 20–24 distinguish Aaron from the Levites while linking both to the chapter's provisions. Aaron is told he will have no land inheritance among Israel, and the Levites receive Israel's tithe as their inheritance in return for their service at the tent of meeting. The passage therefore presents the tithe as a defined provision for the Levites rather than as a general economic principle.

_Passages: Numbers 18:20, Numbers 18:21, Numbers 18:23-24_

### Wilderness-route maps

Maps proposed for the wilderness journey described across Numbers 10–21 should mark uncertain site identifications as uncertain, rather than presenting one reconstructed itinerary as established.

_Passages: Numbers 10, Numbers 11:1-35, Numbers 12:1-16, Numbers 13:1-33, Numbers 14:1-45, Numbers 15:1-41, Numbers 16:1-50, Numbers 17:1-13, Numbers 19:1-22, Numbers 20:1-29, Numbers 21:1-35_

### Semantic/text diff

This diff collapses whitespace within each section and prose block before comparing, so line wrapping and repeated spaces do not appear as content changes.

```diff
--- published prose (whitespace normalized)
+++ candidate prose (whitespace normalized)
@@ -1,2 +1,4 @@
-## surrounding_passages | Context
-- The chapter sits within the book's larger movement; reading it alongside the surrounding account helps clarify its place in that development.
+## cultural_context | Inheritance and the Levites' support
+- Verses 20–24 distinguish Aaron from the Levites while linking both to the chapter's provisions. Aaron is told he will have no land inheritance among Israel, and the Levites receive Israel's tithe as their inheritance in return for their service at the tent of meeting. The passage therefore presents the tithe as a defined provision for the Levites rather than as a general economic principle.
+## surrounding_passages | Wilderness-route maps
+- Maps proposed for the wilderness journey described across Numbers 10–21 should mark uncertain site identifications as uncertain, rather than presenting one reconstructed itinerary as established.
```

## C2S semantic stabilization

C2S narrows the tithe sentence to: “In this passage, the tithe functions specifically as provision and inheritance for the Levites in connection with their service.” The claim remains bounded to Numbers 18 and preserves the inheritance/service connection without making a negative claim about tithe language elsewhere in Scripture. The published generic book-context sentence is replaced by the current wilderness-route uncertainty note and the requested inheritance/tithe explanation; the generic sentence is not chapter-specific and added no distinct interpretive claim. The wilderness-route note remains low/disputed with unchanged provenance.

**Replacement artifact:** `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/stabilization-001/chapters/numbers_18/commentary.json`
**Replacement SHA-256:** `502c079673d07725a126502a869ccdf28a8fefd054110f5495deb2e29753206a`
**Superseded C2 candidate SHA-256:** `4a2629a3e8b65a5fb99c3bbc972572e4e45a0341dcd6df46e9fdf4d8333c58c6`
**C1 input identity:** evidence `785aafb367ed47fa7eb77a2266b51348c31451de23d2cf455c6c77901dd9c6bc`; synthesis `462866b275503b11655d321f4286a59d16d5637e50b0ad572e61f46f921f0253` (unchanged).
**Validation:** full Commentary v1.2 validator passed; candidate remains `READY_FOR_HUMAN_REVIEW`, not approved.

### Replacement Commentary

#### Inheritance and the Levites' support

Verses 20–24 distinguish Aaron from the Levites while linking both to the chapter’s provisions. Aaron is told he will have no land inheritance among Israel, and the Levites receive Israel’s tithe as their inheritance in return for their service at the tent of meeting. In this passage, the tithe functions specifically as provision and inheritance for the Levites in connection with their service.

#### Wilderness-route maps

Maps proposed for the wilderness journey described across Numbers 10–21 should mark uncertain site identifications as uncertain, rather than presenting one reconstructed itinerary as established.
