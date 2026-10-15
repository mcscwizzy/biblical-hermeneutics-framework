# NE-A2 unassigned evidence analysis

## Baseline and method

The audit starts from `origin/master` at `a320e0adda1bda0403bdcb2c82cb8b5107d9a4cd` (`Add NE-A1 CKL coverage audit`). NE-A1 reports 687 CKL objects, 1,189 canonical chapters, 985 chapters with passage-specific evidence, 1,892 unassigned item-chapter placements in 591 chapters, 132 chapters with no eligible CKL material, and one unresolved Obadiah scope issue.

I read every row of `coverage-audit/chapter-census.csv`, parsed `unclassified_ckl_item_ids_json`, and joined each stable projection ID to the committed CKL JSON. This reproduces 1,892 placements across 839 distinct item IDs: 538 IDs occur once and 301 recur across chapters. The breakdown is 128 parent objects (687 placements), 493 claims (951), 210 evidence items (241), and 8 interpretive notes (13). Every ID resolves to a source record. These are placements, not 1,892 unique evidence records or 1,892 unique objects.

The router is deliberately type-based. `_object_sections` routes a limited set of parent types; `_child_sections` routes enumerated claim, evidence, and note types; exact-ID specialized cosmic rules apply only after the evidence type and passage anchor also match. The unassigned IDs are eligible, anchored projection items whose authored type currently has no generic route. They are not records missing from CKL, and no title, summary, or keyword search was used.

## Root causes

| Original record kind and type | Distinct IDs | Placements | Finding |
|---|---:|---:|---|
| Parent `faq` | 51 | 372 | Cross-topic reader questions have no section of their own and do not imply one evidence domain. |
| Parent `word_study` | 50 | 220 | Lexical records span narrative, theology, and language; the current six sections have no lexical lens. |
| Parent `cultural_background` | 13 | 23 | Explicit record kind supports historical/cultural context. |
| Parent `prophecy` | 10 | 50 | A broad source kind can describe text, interpretation, or reception; leave for review. |
| Parent `biblical_theology` | 1 | 7 | Explicit theological synthesis supports Themes & Biblical Connections. |
| Parent `covenant` | 1 | 6 | It may be a theme, event, or institutional record; leave for review. |
| Parent `symbol` | 1 | 6 | A symbol may be literary or theological; its name is not a geography classification. |
| Parent `literary_device` | 1 | 3 | No one section is implied by the generic parent type. |
| Claim `biblical_theology` | 253 | 467 | Explicit authored claim category supports Themes & Biblical Connections. |
| Claim `systematic_theology` | 5 | 8 | Explicit authored claim category supports Themes & Biblical Connections. |
| Claim `reception_history` | 55 | 148 | Reception may be canonical or extra-canonical and needs a more specific policy. |
| Claim `archaeology` | 25 | 121 | Explicit authored claim category supports Archaeology & Ancient History. |
| Claim `lexical` | 84 | 109 | Lexical observations can serve different reader lenses; leave for review. |
| Claim `pastoral_application` | 71 | 98 | The current sections do not have an application lens; leave for review. |
| Evidence `cultural-practice` | 208 | 239 | Explicit cultural-practice evidence supports Archaeology & Ancient History. |
| Evidence `other` | 2 | 2 | Type expressly does not establish a destination. |
| Interpretive note `hebraic-worldview` | 8 | 13 | Broad worldview notes can carry theological interpretation; leave for review. |
| **Total** | **839** | **1,892** | |

## Deterministic assignments

The following additions are supported directly by CKL type metadata and map to existing sections. They preserve parent IDs, local claim/evidence/note IDs, anchors, original types, source references, and certainty, dispute, interpretation, and review fields.

| Type rule | Distinct IDs | Placements | Section |
|---|---:|---:|---|
| Parent `cultural_background` and child evidence `cultural-practice` | 221 | 262 | `archaeology_ancient_history` |
| Parent `biblical_theology`, and claims `biblical_theology` or `systematic_theology` | 259 | 482 | `themes_biblical_connections` |
| Claim `archaeology` | 25 | 121 | `archaeology_ancient_history` |
| **Direct type-driven assignments** | **505** | **865** | |

Examples include the `biblical_theology` parent `ckl:exile-and-return-storyline`, `biblical_theology` claim `ckl:james#claim:jas-job`, and cultural-practice evidence under `ckl:honor-and-shame`. These examples remain in their original CKL categories; section membership is only a presentation lens.

Four additional previously unassigned claims gain a section through the existing authored `claim_ids` link aggregation:

- `ckl:pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status#claim:corinth-disclosure-other-conscience` (lexical) links to evidence `corinth-disclosed-sacrificial-provenance` at 1 Corinthians 10:28-30.
- `ckl:pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status#claim:corinth-wait-share-eat-home` (pastoral application) links to evidence `corinth-wait-and-home-hunger` at 1 Corinthians 11:33-34.
- `ckl:pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation#claim:conflict-08-parental-admonition` (pastoral application) links to evidence `parental-admonition-boundary` at 1 Corinthians 4:14-21.
- `ckl:pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation#claim:conflict-59-differentiated-care` (pastoral application) links to evidence `thess-differentiated-care` at 1 Thessalonians 5:14-15.

None receives an independent generic rule. Each becomes visible in Archaeology & Ancient History only because its explicitly linked evidence record has the deterministic `cultural-practice` classification. Together these are 4 item-chapter placements across 4 unique stable IDs.

The observed full-canon total is therefore 509 distinct previously unassigned items across 869 placements newly assigned, including the four relationship-driven placements. The existing parent aggregation also lets a parent object appear in sections supported by eligible children. This changes section membership counts but does not change item identity or chapter evidence-quality categories.

The section policy adds no generic cosmic-geography rule. In particular, general worldview, presence, mountain, temple, kingship, or glory records do not gain `divine_council_cosmic_geography`. The exact NE-5A specialized evidence rules remain unchanged. Genesis 1 creation comparison status, Genesis 2–3 sacred-space classifications and physical-location safeguards, disputed Genesis 6 readings, Deuteronomy 32 manuscript identity, Psalm 82/Ugaritic evidence identity, and the Exodus 3 Presence records remain governed by their existing source-specific rules.

## Remaining curation work

After these assignments, 330 distinct IDs across 1,023 placements remain without a section. The largest groups are FAQ (51 IDs / 372 placements), word study (50 / 220), lexical claims (84 / 109), pastoral-application claims (68 / 94), reception-history claims (55 / 148), and prophecy objects (10 / 50). Other review rows include covenant, symbol, literary-device, `other` evidence, and Hebraic-worldview notes. These records remain visible in the projection with empty `section_ids`; they are not silently dropped.

`remaining-curation-queue.csv` records each residual item with its stable ID, source object and child kind, original type, applicable Scripture references, authored category, source IDs, certainty/dispute/review metadata, current section state, candidate destination where one was considered, and the reason author review is still required. No CKL source record was changed. The census coverage category is based on lookup status and source-grounded claims/evidence, not section membership, so adding a section does not itself upgrade chapter evidence quality.

The historical NE-A1 totals remain in `coverage-audit/` and are not rewritten. The final A2 census is recorded separately in `04-before-after-results.md`; the 132 no-material chapters and unresolved Obadiah scope issue remain separate from classification work.
