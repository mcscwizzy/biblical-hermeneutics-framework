# 2 Kings 5 — READY_FOR_HUMAN_REVIEW

## Identity

- Old evidence hash: `a92d1c9d4c6c771bc882fe0af2e8518526c88e484a141d6c595f762d4907a952`
- New evidence hash: `3809454fdb77b0baf035e62d82d15102942d170a17b5025163c308d3dd38e76c`
- Old synthesis hash: `13e54a21f10d4097fb1d360bb352e16f3725ca8e9afb10959b05d3a9811118de`
- New synthesis hash: `6314975c710fce70018f69f07ae6c4e28a6c7097ca092e74669eba4e0b1666fc`
- Candidate Commentary SHA-256: `480c7585e9836ded362662004d2818ed8f81f05affb5e9568d367a572b08c3c6`
- Candidate artifact: `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-0e53eca15a36aa3a/chapters/2_kings_005/commentary.json`
- Old published Commentary: `.bhf-data/bhf-commentary-v1.2/2_kings_005.json`
- Renderer: `gpt-5.6-terra` via `commentary-v1.2-codex-cli`; prompt `1.8`, synthesis compiler `1.1`
- Attempt interval: `2026-10-07T00:32:13.437655+00:00` – `2026-10-07T00:32:35.279370+00:00`
- Result: `validated`; approval: `NOT_APPROVED`

## Transaction A evidence delta

- Added: `abana-2kings-5-damascus-river-comparison-identity`
- Added: `pharpar-2kings-5-damascus-river-comparison-identity`
- Added: `source-lock-2kings-5-damascus-river-comparison`
- Added: `source-lock-2kings-5-naaman-aram-israel-jordan-journey`
- Added: `source-lock-2kings-5-naaman-jordan-immersion`
- Removed: none

## Validation

- Existing Commentary v1.2 validation: passed.

## Commentary comparison

### Published Commentary

### Naaman’s Healing

Naaman, an Aramean commander, follows Elisha’s instruction and is healed. He then confesses that no God exists in all the earth except in Israel, making his healing and response the central movement of the chapter.

_Passages: 2 Kings 5:1-19_

### Candidate Commentary

### Overview

The chapter follows Naaman, an Aramean commander, as he follows Elisha’s instruction, is healed, and then declares that there is no God in all the earth except in Israel. His healing and confession form the central movement of verses 1–19.

_Passages: 2 Kings 5:1-19_

### Rivers in Naaman’s Objection

Naaman’s objection is geographically specific: he names Abana and Pharpar as rivers of Damascus and contrasts them with Israel’s waters. Yet Elisha’s instruction concerns the Jordan, the actual water location where Naaman later immerses himself. The contrast explains why Naaman initially resists the command.

_Passages: 2 Kings 5:10, 2 Kings 5:12, 2 Kings 5:14, 2 Kings 5:5-6, 2 Kings 5:9-10_

### Semantic/text diff

This diff collapses whitespace within each section and prose block before comparing, so line wrapping and repeated spaces do not appear as content changes.

```diff
--- published prose (whitespace normalized)
+++ candidate prose (whitespace normalized)
@@ -1,2 +1,4 @@
-## historical_context | Naaman’s Healing
-- Naaman, an Aramean commander, follows Elisha’s instruction and is healed. He then confesses that no God exists in all the earth except in Israel, making his healing and response the central movement of the chapter.
+## chapter_overview | Overview
+- The chapter follows Naaman, an Aramean commander, as he follows Elisha’s instruction, is healed, and then declares that there is no God in all the earth except in Israel. His healing and confession form the central movement of verses 1–19.
+## archaeology_geography | Rivers in Naaman’s Objection
+- Naaman’s objection is geographically specific: he names Abana and Pharpar as rivers of Damascus and contrasts them with Israel’s waters. Yet Elisha’s instruction concerns the Jordan, the actual water location where Naaman later immerses himself. The contrast explains why Naaman initially resists the command.
```
