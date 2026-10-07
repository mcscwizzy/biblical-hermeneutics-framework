# Genesis 13 — READY_FOR_HUMAN_REVIEW

## Identity

- Old evidence hash: `4b16ee265db55e19aa832b598ce57e18fe3e847f3a2fd0c0955eba97084f12f6`
- New evidence hash: `513efc8ac13f279874b658ffb3529b1fb78e0a5102c7f1bb650e38f93be21fc2`
- Old synthesis hash: `d22dadff9ff153050af30dbeeb1021b84248c1d310ef4830f6f73f709f0fe710`
- New synthesis hash: `c83250bfd35e5cfca438a18d707bfb57a1145e626fac61a4d8c998a9b1330c95`
- Candidate Commentary SHA-256: `c389b19f4781f3000242d437c61c0d36ffefc48c596e20f00f7935bafe97c8d4`
- Candidate artifact: `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-13c4d7e346924c69/chapters/genesis_013/commentary.json`
- Old published Commentary: `.bhf-data/bhf-commentary-v1.2/genesis_013.json`
- Renderer: `gpt-5.6-terra` via `commentary-v1.2-codex-cli`; prompt `1.8`, synthesis compiler `1.1`
- Attempt interval: `2026-10-07T00:28:33.766903+00:00` – `2026-10-07T00:29:22.674100+00:00`
- Result: `validated`; approval: `NOT_APPROVED`

## Transaction A evidence delta

- Added: `source-lock-genesis-13-abram-negev-bethel-ai-movement`
- Added: `source-lock-genesis-13-jordan-valley-well-watered-description`
- Added: `source-lock-genesis-13-lot-eastward-separation`
- Removed: none

## Validation

- Existing Commentary v1.2 validation: passed.

## Commentary comparison

### Published Commentary

### History and archaeology

The supplied context keeps Mosaic-attribution and compositional models distinct positions: Genesis does not narrate the history of its own literary formation. It also cautions that the absence of direct archaeological identification cannot by itself prove or disprove every ancestral narrative, because archaeology and literary interpretation answer different questions.

### Candidate Commentary

### Places and Movement

Abram returns from the South to the earlier campsite between Bethel and Ai before the dispute over land is described. The chapter then makes geography central to the separation: Lot sees the Jordan Plain as well watered and chooses it, traveling east and settling among its cities as far as Sodom, while Abram remains in Canaan. The description of the plain is the stated basis for Lot’s choice.

_Passages: Genesis 13:1, Genesis 13:3, Genesis 13:10, Genesis 13:11-12_

### Genesis in Context

Genesis 13 belongs to the ancestral family narratives that occupy Genesis 12–50, following the book’s opening movement from universal origins in chapters 1–11. Questions about how Genesis came to be written remain disputed: Mosaic attribution and compositional models are distinct positions, and Genesis itself does not narrate its own literary formation.

### Semantic/text diff

This diff collapses whitespace within each section and prose block before comparing, so line wrapping and repeated spaces do not appear as content changes.

```diff
--- published prose (whitespace normalized)
+++ candidate prose (whitespace normalized)
@@ -1,2 +1,4 @@
-## surrounding_passages | History and archaeology
-- The supplied context keeps Mosaic-attribution and compositional models distinct positions: Genesis does not narrate the history of its own literary formation. It also cautions that the absence of direct archaeological identification cannot by itself prove or disprove every ancestral narrative, because archaeology and literary interpretation answer different questions.
+## archaeology_geography | Places and Movement
+- Abram returns from the South to the earlier campsite between Bethel and Ai before the dispute over land is described. The chapter then makes geography central to the separation: Lot sees the Jordan Plain as well watered and chooses it, traveling east and settling among its cities as far as Sodom, while Abram remains in Canaan. The description of the plain is the stated basis for Lot’s choice.
+## surrounding_passages | Genesis in Context
+- Genesis 13 belongs to the ancestral family narratives that occupy Genesis 12–50, following the book’s opening movement from universal origins in chapters 1–11. Questions about how Genesis came to be written remain disputed: Mosaic attribution and compositional models are distinct positions, and Genesis itself does not narrate its own literary formation.
```
