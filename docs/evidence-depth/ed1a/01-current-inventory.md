# ED-1A current inventory

## Baseline

This is a fresh read-only audit of the CKL and current Narrative Explorer projection on branch base `d4071380f18c5891307fcc3b5a4b99610646e567` (2026-11-01). The CKL inventory fingerprint is `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. The JSON object tree was not changed. The census covered **66 books and 1,189 of 1,189 canonical chapters**, with 1,189 unique chapter identities and zero unmapped projected record identities.

| Current CKL inventory measure | Count | Counting method |
| --- | ---: | --- |
| CKL objects | 687 | Validated objects in the committed CKL manifest and loader |
| Claims | 2,329 | All `claims[]` children |
| Typed evidence items | 1,297 | All `evidence_items[]` children |
| Interpretive notes | 3,691 | All `interpretive_notes[]` children |
| Source record occurrences | 5,232 | Bibliography entries repeated across CKL objects |
| Unique source IDs in bibliographies | 2,783 | Distinct non-empty source IDs across those occurrences |
| Child source-reference occurrences | 17,483 | `source_ids` on claims/evidence and `sources` on interpretive notes |
| Resolved / unresolved child source references | 17,481 / 2 | Resolved only when the same parent object contains the referenced source ID |

The records contain 10 claim types, 17 evidence types, and 10 interpretive-note types. The exact distributions are in [`summary.json`](summary.json). Counts describe the inventory; they do not measure scholarly completeness.

## Passage coverage and source identity

The current NE-A1 runtime census classifies chapters as follows:

| Runtime census state | Chapters |
| --- | ---: |
| Passage-specific source-grounded claim/evidence | 985 |
| Contextual CKL material | 68 |
| Entity-only CKL material | 3 |
| No eligible CKL material | 132 |
| Incomplete or unknown | 1 |

There are **6,098 source-backed claim/evidence chapter placements** and **12,662 eligible CKL item-to-chapter placements**. The term *placement* matters: one record can apply to more than one chapter. The 1,023 eligible placements not assigned to one of the six Narrative Explorer sections occur in 394 chapters. These are a section-discoverability signal; an unclassified item may still enter a qualifying, limited connection preview. The six section totals overlap and are not a unique-item partition.

Among 2,783 bibliography source IDs, 2,225 meet this audit's minimum traceability screen: a title plus at least one author, publisher, year, locator, or URL. The other 558 are **screen failures for human review**, not 558 confirmed bad citations; they comprise 472 scripture and 86 reference-work identities. One source classified as a locator-expected type lacks a locator: `patristic-minor-prophets`. In repeated bibliography occurrences, 81 source IDs have differing non-empty identity metadata and 148 have differing locators. Multiple locators are often legitimate, and the counts are not automatic defects. Spot checks do show likely same-ID publication conflations: `aune` includes *Revelation* and *The New Testament in Its Literary Environment*; `bauckham` includes *Jude, 2 Peter* and *The Theology of the Book of Revelation*; `burnett-imperial-honors` maps to two different titles and authors. The full field values are in `summary.json`; source owners should confirm identities before reuse or correction.

Two child source references are unresolved: `harland-associations` and `glancy-slavery` on `roman-ephesus-civic-cultic-and-household-life#interpretive-note:sha256-a69db357b2e4ae0efd94846f597f048835c3ab81143ddc5371ad3c14b0702fff`. This note has no Scripture anchor, so the issue is provenance review rather than a demonstrated passage-coverage gap.

The one incomplete chapter is Obadiah 1. Its note `obadiah#interpretive_note:sha256-21d8661d398d03bd016453f63d2be7e1338764bf635c38c76ea40ec56f860819` carries the out-of-bounds reference `Obadiah 7`. The audit did not guess the intended scope.

The separate CKL deep quality report returned **1,036 heuristic review findings**: 62 error-severity `dispute-confidence-mismatch` signals and 974 warnings (523 missing chronology, 396 generic legacy boilerplate, 43 unknown passage chronology, 1 overbroad context, 4 unsupported cross-period links, and 7 weak source-type signals). For example, `genesis#evidence:g4-mark-sign-unspecified-protection` and `genesis#evidence:g4-offerings-and-divine-regard` are flagged because high confidence is paired with disputed or uncertain evidence. These are quality-report checks, not schema-validation errors or scholarly adjudications. The standard CKL validator remains at zero errors and 14 warnings. A further 544 records are flagged by the deep report's broad candidate-quality-gap completeness screen; that screen does not establish a content defect. Reproduce these separate quality signals with the `ckl_report.py --deep --json` command below.

## Relationships and adjacent evidence services

- The CKL contains **4,061 authored `related_objects` edges** and **305 explicit `related_evidence` links** authored on typed evidence items. These counts do not represent accepted passage routes. The CKL deep graph report separately expands evidence into **22,503 structured graph edges**, including support, source, geography, temporal, and relationship edges; that larger graph-edge count is not a count of authored connections.
- Current NE-9C validation passes all **3,925 reviewed decisions**: 408 curated, 1,895 held, and 1,622 excluded. The accepted runtime registry contains **433 identities** (431 object relationships and 2 evidence relationships): 408 newly curated object decisions, 23 retained earlier object decisions, and 2 existing evidence decisions. Held and excluded decisions remain out of the accepted route set.
- The current NE-10 registry has **44 verified bridge records** and **7 held research candidates**. The 44 are registry identities, not endpoint rows. Since NE-11A's 43-record snapshot, the additional bridge is `jonah-1-17-matthew-12-40-sign-of-jonah`; its inclusion is not a reason to reclassify any held candidate.
- The current sample validated 19 deterministic census checks and 16 resolver-backed builds. Stored external links have valid targets/references in study database schema 37. Stored map links: 7,741 place, 2 route, and 13 territory rows. Archaeology: 94 explicit links to 75 service items, of which 71 items have valid passage links and 4 have none. Manuscript service: 11 links to 6 items, all with valid passage links. Six static-map files contain 222 passage-link rows. These are explicit stored links, not exhaustive resolver coverage or evidence that every chapter should have a map or artifact.

The archaeology catalog remains in its service domain. ED-1A records its integration links and identifiers without duplicating the catalog. Map coordinates are not used to infer ancient identity.

## Lexical reference inventory

The packaged `framework/lexical/database/lexicon.sqlite.gz` passed SQLite integrity checking. It contains 14,197 lexical entries (5,523 Greek; 8,674 Hebrew), 444,339 verse-word rows (137,554 Greek; 306,785 Hebrew), and word rows in all 1,189 canonical chapters. Its four source rows are identified with revisions and license metadata in `summary.json` (two dictionary-source revisions are unspecified). This enables general lookup and aligned word tokens; it is not passage-specific lexical research. The CKL separately has 50 `word_study` objects and 107 claims typed `lexical`.

## Comparison with earlier work

The NE-A1, NE-9C, NE-10, and NE-11 reports were read as historical snapshots. NE-11A recorded the same CKL fingerprint, the same 985 / 68 / 3 / 132 / 1 chapter distribution, 6,098 source-backed placements, 1,023 unclassified placements in 394 chapters, and 43 verified NE-10 bridge records. The current independent census confirms those values and finds 44 bridges after the separately documented Jonah/Matthew addition.

The earlier NE-A1 executive summary combined contextual and entity-only chapters into 71; NE-11A split them into 68 and 3. Its projection reported unclassified items in 591 chapters, while NE-11A and the present census report 394. Those snapshots use different commits and projection logic, so this is not presented as a controlled measure of application improvement. The current measurements come from the current projector.

NE-10's held candidates remain held. NE-9C acceptance decisions remain unchanged. The NE-11 reports' distinction between an evidence record, a curated relationship route, an API projection, and a visible card is retained throughout ED-1A.

## Reproduction and validation

From the repository root, run:

```bash
python3 scripts/audit_ed1a_evidence_depth.py \
  --output-dir docs/evidence-depth/ed1a \
  --study-db .bhf-data/study.sqlite
python3 tools/ckl_validate.py --root framework/canonical_library
python3 tools/ckl_report.py --root framework/canonical_library --deep \
  --json --output /tmp/ed1a-quality-report.json
python3 scripts/ne9c_bulk_curation.py --source-root . \
  --state-dir docs/narrative-explorer/ne9c-bulk-curation validate
```

The first command reruns the complete NE-A1 chapter retrieval/projection census and then adds typed CKL, source, and lexical inventories. It writes the machine-readable [`summary.json`](summary.json) and one-row-per-chapter [`chapter-coverage.csv`](chapter-coverage.csv). Current CKL validator result: 687 valid objects, zero errors, and 14 existing incomplete-section-status warnings (including `arad-ostraca`, `exile-and-return-storyline`, `chiasm`, `branch-prophecy`, and `abba`). CKL deep-report quality heuristics raised review signals separate from schema errors; ED-1A does not convert those heuristic flags into scholarly judgments.
