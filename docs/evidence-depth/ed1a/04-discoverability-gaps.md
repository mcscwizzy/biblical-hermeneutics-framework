# ED-1A discoverability and gap classification

## Findings by gap type

| Gap class | Current measured signal | ED-1A classification and action |
| --- | --- | --- |
| Genuine research gap | 132 chapters have no CKL item eligible for the current Narrative Explorer passage projection; another 68 have contextual material and 3 have entity-only material. Psalm 72 has four eligible items but only two source-traceable child placements; 2 Chronicles 30 has nine items and three source-traceable child placements; Ezekiel 40 has twelve items and three source-traceable child placements. | The absence from projection is real. Whether each chapter warrants new research is **unknown until human triage**. Research candidates are prioritized only when the passage poses a concrete, answerable historical, literary, or interpretive question. |
| Discoverability gap | 1,023 eligible CKL item placements in 394 chapters are not assigned to one of the six Narrative Explorer sections. | A section-classification review is justified, but not every unclassified item is relevant or should be promoted. Example: `ckl:1-corinthians#claim:1cor-kephale` is a source-backed lexical claim anchored to 1 Corinthians 11:3 and appears in the unclassified item list for chapter 11. This is a precise reader-discovery candidate. By contrast, `ckl:proverbs#claim:proverbs-greek-order` appears unclassified in Proverbs 31 while its own anchors concern Proverbs 24 and 30; human scope review should precede any section assignment. |
| Relationship gap | 4,061 raw authored object edges coexist with 433 active accepted curated identities and 44 verified NE-10 bridge records. Seven NE-10 candidates remain held. | These are distinct graph and route states. Do not promote held or excluded relations to increase coverage. Any new relationship recommendation must identify exact source records, both canonical endpoint scopes, source IDs, chronology, and category-specific evidence. |
| Provenance gap | Two child source references are unresolved; 558 of 2,783 unique bibliography identities fail the audit's minimal title-plus-detail screen (472 scripture and 86 reference-work IDs); `patristic-minor-prophets` lacks an expected locator; 81 source IDs have differing non-empty identity metadata and 148 have differing locators. | Keep this as provenance triage, not a statement that all entries are defective. Exact unresolved sources occur on `roman-ephesus-civic-cultic-and-household-life#interpretive-note:sha256-a69db357b2e4ae0efd94846f597f048835c3ab81143ddc5371ad3c14b0702fff`: `harland-associations`, `glancy-slavery`. Spot checks identify possible same-ID publication conflations for `aune`, `bauckham`, and `burnett-imperial-honors`; variation IDs and exact values are in `summary.json`. Confirm editions/aliases and record-level locators before editing anything. |
| Domain integration gap | Four archaeology service items lack valid passage links; 57 map-place inventory items lack a valid passage link. All existing stored link rows passed reference and target checks. | Review only records whose scholarly passage relationship is established. Absence of a link is not itself an error or a reason to add a map. Keep archaeology catalog data in the archaeology subsystem and link by stable ID. |
| Not applicable | Many chapters do not warrant archaeology, an ancient text parallel, or a debate section. | Do not require one record in all six domains per chapter. Apply domain tests only when the passage itself makes the question relevant. |
| Unknown / human review | Typed tags cannot establish whether a chapter's historical, language, primary-source, archaeological, narrative, or interpretive evidence is adequate. The single incomplete chapter has an invalid anchor. | Use human source review to determine relevance, coverage, and uncertainty. Obadiah 1 remains incomplete pending source-owner review of `obadiah#interpretive_note:sha256-21d8661d398d03bd016453f63d2be7e1338764bf635c38c76ea40ec56f860819` (`Obadiah 7`). |

## Records represented but weakly discoverable

The census counts projection items eligible for a chapter. Narrative Explorer then assigns items to section categories; the reader-facing evidence preview is a separate selector with its own eligibility and display limit. Therefore a record can be:

1. present in CKL but not eligible for the selected passage;
2. eligible and returned by the projector;
3. returned but not assigned to a section;
4. assigned to a section but excluded from a limited preview; or
5. visible as a relationship route through a different presentation path.

These states are not interchangeable. `unclassified_ckl_item_count` in the CSV means the record did not receive a section assignment; it does not mean the record is globally inaccessible. Reader preview selection and maximum-card behavior are presentation rules, not CKL evidence absence.

Specific review examples:

- **1 Corinthians 11:** the current projection includes `ckl:1-corinthians#claim:1cor-kephale`, a source-backed lexical claim on 1 Corinthians 11:3, plus several typed `evidence_items` on the same passage. It is the strongest example for reviewing section discoverability and preserving its alternatives. The object has many other directly scoped records, so mass evidence generation here would be low value.
- **Mark 2:** the unclassified list includes `ckl:mark#claim:mark-disability`, `ckl:chiasm`, and `ckl:what-is-the-significance-of-the-sabbath`. These records may serve pastoral, structural, or question-oriented navigation rather than the six section categories. Check the exact consumer and identity before recommending a UI/category change.
- **Exodus 12:** the unclassified items include `ckl:what-is-a-covenant-sign`, `ckl:what-is-the-significance-of-passover`, and `ckl:who-was-moses`. Their reader value should be judged separately from the passage's source-backed evidence, not counted as missing primary-source evidence.
- **Ezekiel 40:** `ckl:new-jerusalem-prophecy` appears unclassified in the chapter projection. Its presence must not be treated as approval of the held NE-10 bridge `ezekiel-40-48-revelation-21-22-temple`.

## Primary-source presentation

The corpus contains dedicated ancient-text and manuscript records, and the 2 Kings 18 projection is already a strong example: `ckl:sennacherib-prism#evidence:taylor-prism-annals` (source `taylor-prism`), `ckl:sennacherib-prism#evidence:lachish-relief-royal-siege-rhetoric`, and `ckl:assyrian-tribute-and-royal-representation#evidence:sennacherib-hezekiah-tribute`. Their original Assyrian royal setting and genre need to be presented alongside the biblical narrative. The British Museum identifies the Taylor Prism as carrying Sennacherib's account of Hezekiah's tribute in 701 BCE and catalogs the Lachish relief panels separately; see [Taylor Prism collection record](https://www.britishmuseum.org/collection/object/W_1855-1003-1) and [Lachish relief panel 124908](https://www.britishmuseum.org/collection/object/W_1856-0909-14_5). These texts and images are royal representations, not neutral transcripts of every event.

## Do not convert held or excluded research into routes

The NE-10 held records are research prompts with explicit limits, not reader routes. In particular, `deuteronomy-32-psalm-82-job-1-divine-assembly`, `exodus-12-1-corinthians-5-passover`, `ezekiel-37-john-3-water-spirit`, and `ezekiel-40-48-revelation-21-22-temple` remain held. NE-9C exclusions likewise remain excluded. ED-1A reports no change to either registry and proposes no relationship promotion.
