# Ruth 1 — READY_FOR_HUMAN_REVIEW

## Identity

- Old evidence hash: `9b25f9ec169873ffbbcfe387f238bf2618195918a136c2c6eda37ca4c74c119c`
- New evidence hash: `1224b8fcf887845f926aa765da713e3301c1b5f26f2d9bb8fc9505dc5e0677ba`
- Old synthesis hash: `ba93ac0b616347616f3e7d8c000cd05a31836a96429c0cd1268a194e351e72a7`
- New synthesis hash: `315fb5e50f38e7f3720f3bbdd574360e7d02e6dc48964b1edd1deae1a9e29969`
- Candidate Commentary SHA-256: `1b55bf3ec49942bc13eaf3cc58e4583adeeaf7b3786cafcff2eaeba4e353339e`
- Candidate artifact: `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/ruth-repair-001/corpus-runner/runs/batch-9ae3229dd2fdd5bd/chapters/ruth_001/commentary.json`
- Old published Commentary: `.bhf-data/bhf-commentary-v1.2/ruth_001.json`
- Renderer: `gpt-5.6-terra` via `commentary-v1.2-codex-cli`; prompt `1.8`, synthesis compiler `1.1`
- Attempt interval: `2026-10-07T01:16:29.322038+00:00` – `2026-10-07T01:17:04.706021+00:00`
- Result: `validated`; approval: `NOT_APPROVED`

## Transaction A evidence delta

- Added: `judah-territory-ruth-1-bethlehem-judah-territory-identity`, `source-lock-ruth-1-bethlehem-judah-territory`, `source-lock-ruth-1-bethlehem-moab-migration`
- Removed: none

## Validation

- Existing Commentary v1.2 candidate validation: passed. Required confidence and interpretation fields are present, confidence values are schema-valid, and no block exceeds the confidence ceiling of its cited evidence or synthesis.

## Superseded invalid attempt

- Original artifact SHA-256: `0529d5ddf77b5cfa5fbe1afa2513785cb1e02062384eb00af39c90bf2fae6e76`; archived at `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/ruth-repair-001/history/ruth-001-invalid-commentary.json`.
- Original raw response SHA-256: `962b13102f30d40b86e6b133a773f844ba75b32c37ae9dbbf344db2654363b5d`; retained at `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-9ae3229dd2fdd5bd/chapters/ruth_001/raw-response.bin`.
- Root cause: the model response omitted `confidence` and `interpretation_level` from its blocks. Prompt 1.8 requests both; JSON parsing and provenance normalization preserved the response without filling them. The validator rejected the blocks, including a `medium` fallback exceeding low-confidence support. No parser, renderer, prompt, schema, or validator change was needed.
- Original validator errors: section[0].block[0].confidence is required; section[0].block[0].interpretation_level is required; section[1].block[0].confidence is required; section[1].block[0].interpretation_level is required; section[2].block[0].confidence is required; section[2].block[0].interpretation_level is required; CONFIDENCE_EXCEEDS_EVIDENCE: section[2].block[0].confidence exceeds its cited evidence; CONFIDENCE_EXCEEDS_EVIDENCE: section[2].block[0].confidence exceeds its cited synthesis; section[3].block[0].confidence is required; section[3].block[0].interpretation_level is required; section[3].block[1].confidence is required; section[3].block[1].interpretation_level is required

## Commentary comparison

### Published Commentary

### Ruth's pledge

Ruth’s response to Naomi is a comprehensive pledge of loyalty: she will go, live, identify with Naomi’s people and God, and remain with her until death. The chapter therefore presents her decision as more than accompanying Naomi on a journey; it binds her future to Naomi’s life and community.

_Passages: Ruth 1:16-18_

### Questions the chapter raises

The narrative says that the LORD gave food to his people, while Naomi and Ruth’s return unfolds through their own decisions and actions. Ruth also continues to be identified as a Moabite even as she pledges herself to Naomi, Naomi’s people, and Naomi’s God. Some readers connect this to later debates about intermarriage, but the proposal that the book directly answers a particular later policy remains debated. Likewise, the setting in the days of the judges and the genealogy leading to David do not establish when the anonymous book reached its final form.

_Passages: Ruth 1:1, Ruth 1:6, Ruth 1:16-18_

### The wider story

Ruth 1 begins a movement that extends through the book: famine, bereavement, and Naomi’s sense of emptiness give way to harvest, kinship redemption, birth, communal blessing, and genealogy. The arrival at the beginning of barley harvest is therefore a transition within that larger movement, not the resolution of Naomi’s loss.

_Passages: Ruth 2:1-23, Ruth 3:1-18, Ruth 4:1-22_

A later discussion in Nehemiah applies an exclusion concerning Ammonites and Moabites in a particular temple-access setting. Read alongside Ruth, which retains Ruth’s Moabite identity while presenting her loyalty to Naomi and Naomi’s God, this cautions against treating the episode as support for a universal ethnic ban; how these texts relate remains disputed.

_Passages: Ruth 2:1-23, Ruth 3:1-18, Ruth 4:1-22_

### Replacement Candidate Commentary

### Places and movement

The chapter begins in Bethlehem in Judah, with Judah named as the setting. Famine sends Elimelech’s family from Bethlehem to Moab, and the chapter closes with Naomi and Ruth returning to Bethlehem. These place names frame the chapter’s movement from departure to return without supplying an itinerary between the two places.

_Passages: Ruth 1:1-2, Ruth 1:19-22_

### Ruth’s pledge

Ruth’s response to Naomi is more than an agreement to travel together. She pledges to go and live where Naomi does, to identify with Naomi’s people and God, and to remain with Naomi until death. The scene therefore presents Ruth’s decision as a comprehensive, enduring commitment after Orpah has returned home.

_Passages: Ruth 1:16-18_

### A debated question

The narrative continues to call Ruth “the Moabitess” even as she commits herself to Naomi, Naomi’s people, and Naomi’s God. Some readers connect this feature to later debates about intermarriage, but the proposal that Ruth was written as a direct response to a particular later policy remains debated.

_Passages: Ruth 1:1, Ruth 1:6, Ruth 1:16-18_

### The wider story

Ruth 1 opens the book’s larger movement: famine, bereavement, and Naomi’s description of herself as empty are followed by harvest, kinship redemption, birth, communal blessing, and genealogy. The arrival at the beginning of barley harvest is therefore the opening turn within that broader movement, not the story’s resolution.

_Passages: Ruth 2:1-23, Ruth 3:1-18, Ruth 4:1-22_

A later canonical discussion in Nehemiah 13 applies an exclusion concerning Ammonites and Moabites while addressing Tobiah’s access to temple space. Read alongside Ruth the Moabite and texts that welcome faithful foreigners, this material should not be turned into a universal ethnic ban; how these texts relate is a debated interpretive question.

_Passages: Ruth 2:1-23, Ruth 3:1-18, Ruth 4:1-22_

### Semantic/text diff

This diff collapses whitespace within each section and prose block before comparison, so line wrapping and repeated spaces do not appear as content changes.

```diff
--- published prose (whitespace normalized)
+++ candidate prose (whitespace normalized)
@@ -1,7 +1,9 @@
-## historical_context | Ruth's pledge
-- Ruth’s response to Naomi is a comprehensive pledge of loyalty: she will go, live, identify with Naomi’s people and God, and remain with her until death. The chapter therefore presents her decision as more than accompanying Naomi on a journey; it binds her future to Naomi’s life and community.
-## interpretive_questions | Questions the chapter raises
-- The narrative says that the LORD gave food to his people, while Naomi and Ruth’s return unfolds through their own decisions and actions. Ruth also continues to be identified as a Moabite even as she pledges herself to Naomi, Naomi’s people, and Naomi’s God. Some readers connect this to later debates about intermarriage, but the proposal that the book directly answers a particular later policy remains debated. Likewise, the setting in the days of the judges and the genealogy leading to David do not establish when the anonymous book reached its final form.
+## archaeology_geography | Places and movement
+- The chapter begins in Bethlehem in Judah, with Judah named as the setting. Famine sends Elimelech’s family from Bethlehem to Moab, and the chapter closes with Naomi and Ruth returning to Bethlehem. These place names frame the chapter’s movement from departure to return without supplying an itinerary between the two places.
+## historical_context | Ruth’s pledge
+- Ruth’s response to Naomi is more than an agreement to travel together. She pledges to go and live where Naomi does, to identify with Naomi’s people and God, and to remain with Naomi until death. The scene therefore presents Ruth’s decision as a comprehensive, enduring commitment after Orpah has returned home.
+## interpretive_questions | A debated question
+- The narrative continues to call Ruth “the Moabitess” even as she commits herself to Naomi, Naomi’s people, and Naomi’s God. Some readers connect this feature to later debates about intermarriage, but the proposal that Ruth was written as a direct response to a particular later policy remains debated.
 ## surrounding_passages | The wider story
-- Ruth 1 begins a movement that extends through the book: famine, bereavement, and Naomi’s sense of emptiness give way to harvest, kinship redemption, birth, communal blessing, and genealogy. The arrival at the beginning of barley harvest is therefore a transition within that larger movement, not the resolution of Naomi’s loss.
-- A later discussion in Nehemiah applies an exclusion concerning Ammonites and Moabites in a particular temple-access setting. Read alongside Ruth, which retains Ruth’s Moabite identity while presenting her loyalty to Naomi and Naomi’s God, this cautions against treating the episode as support for a universal ethnic ban; how these texts relate remains disputed.
+- Ruth 1 opens the book’s larger movement: famine, bereavement, and Naomi’s description of herself as empty are followed by harvest, kinship redemption, birth, communal blessing, and genealogy. The arrival at the beginning of barley harvest is therefore the opening turn within that broader movement, not the story’s resolution.
+- A later canonical discussion in Nehemiah 13 applies an exclusion concerning Ammonites and Moabites while addressing Tobiah’s access to temple space. Read alongside Ruth the Moabite and texts that welcome faithful foreigners, this material should not be turned into a universal ethnic ban; how these texts relate is a debated interpretive question.
```
