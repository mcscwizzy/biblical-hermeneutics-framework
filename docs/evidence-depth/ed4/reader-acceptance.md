# ED-4 reader acceptance

## Passage evidence coverage

The current API and projection regressions keep representative evidence types
available under their exact passage scopes. These checks exercise the existing
reader projection and make no scholarly classification changes.

| Reader need | Passage and record | Verified result |
|---|---|---|
| Historical/cultural context | Genesis 6; interpretive positions on the “sons of God” | Context record remains scoped to its anchors, marked disputed, and is not expanded by book-level cross-references. |
| Literary convention | 1 Chronicles 16:36; `first-chronicles-16-36-five-book-psalter` | Projected as `literary-convention`; the primary observation and Longacre’s scholarly proposal remain separately available with source attribution and major-dispute metadata. |
| Hebrew/Greek word study | 1 Corinthians 11:3; `1cor-kephale` | The additional-record disclosure presents “Lexical research,” keeps its disputed lexical status, and retains source IDs `bdag` and `thiselton-1cor`. |
| Manuscript variant | Deuteronomy 32:8–9; `deuteronomy-32-8-manuscript-variant` | The manuscript item remains visible when archaeology lookup is empty, keeps the Qumran source and textual-variant uncertainty, and does not become a direct-quotation route. |
| Cultural practice | John 10:22; `john-10-22-dedication-term-and-winter` | Projected as `cultural-practice`, scoped to John 10:22; the record states that the proposal is reported from an abstract, preserving the access limit. |
| Later reception | Jonah 1:17 and Matthew 12:40; `jonah-1-17-matthew-12-40-sign-of-jonah` | The verified bridge is reachable from both endpoints with its historical source/receiving-text direction, exact support, and interpretive caveat. |
| Disputed interpretation | Psalm 82; `psalm-82-assembly-text` and related evidence | The text-level claim remains marked textually explicit while the interpretive question remains disputed; no theme object is inferred. |
| Unassigned source-backed child record | 1 Corinthians 11:3; `1cor-kephale` | “Additional sourced records” starts collapsed. On activation the item appears once, with its applicable anchor and exact sources; broader parent objects and ineligible records remain excluded. |

The API checks also cover Genesis 6 cultural evidence, the Psalm 82 context,
the 44 verified passage bridges, seven held NE-10 candidates, and the Proverbs
31 child-record scope. Ten existing evidence and route tests passed, along with
the new literary/cultural record regression (11 total). The related modules are
`tests/test_narrative_explorer_api.py` and
`tests/test_narrative_explorer_projection.py`.

## Desktop and mobile browser checks

The checks ran in headless Chromium through the repository's Selenium harness.
The disclosure test applied an actual 390 CSS-pixel mobile emulation with
device metrics, DPR 1, and a 390-pixel viewport.

| Flow | Desktop | Mobile / result |
|---|---|---|
| Narrative Explorer overview and category navigation | Six overview categories, category detail, back/forward history, and return to the selected passage passed. | Six categories fit at 390 CSS px with no horizontal overflow; selection and back navigation remained in scope. |
| Additional lexical record | The record starts hidden, then appears exactly once with its type and source details. | At 390×844 it remained within the viewport; the disclosure was 44px high and there was no horizontal overflow. |
| Draft review label and source provenance | Genesis 12 context record showed “Draft evidence — awaiting human review”; all 17 source IDs and 46 evidence records matched the API response. | The same label and disclosure behavior passed at 390 CSS px; no overflow. |
| Long bibliography locator | The attributed source’s title, author, and locator were readable from its own source disclosure. | The exact source detail remained visible at configured 320px and 390px browser widths with no document overflow. |
| Back/forward navigation | Opening/closing source details did not alter history; browser back/forward preserved Genesis 12 and restored focus to the originating record. | Passage scope remained intact in the selected mobile disclosure check. |
| Reader search | Bible text search rendered results and retained reader navigation. | Retrieval correctness for named books and ordinary-language queries is separately covered by Phase 1 ranking tests. |

Desktop and mobile measurements from the exact ED-1C passage-scoped record:

- Desktop configured viewport: 1440×1200; document/client width: 1425/1425px.
- Mobile emulated viewport: 390×844; document/client width: 390/390px.
- Toggle height: 44px at both sizes; one item after expansion; source IDs
  `bdag` and `thiselton-1cor` retained.

The selected browser runs passed: ED-1C additional-record acceptance (2),
draft/source/history and 390px governance checks (3), overview and Bible search
(2). The source detail case also checked 320px and 390px layouts. No duplicate
item, incorrect passage scope, clipped control, or horizontal overflow was
reproduced, so no presentation change was needed.

## Commands and results

```bash
.venv/bin/python -m pytest -q \
  tests/test_narrative_explorer_api.py::test_genesis_6_exposes_scoped_cultural_evidence_without_book_level_cross_references \
  tests/test_narrative_explorer_api.py::test_jonah_matthew_reception_bridge_projects_exact_support_in_both_directions \
  tests/test_narrative_explorer_api.py::test_psalm_82_discloses_council_context_and_keeps_explicit_text_distinct_from_dispute \
  tests/test_narrative_explorer_api.py::test_deuteronomy_32_ckl_manuscript_witness_survives_empty_archaeology_lookup \
  tests/test_narrative_explorer_api.py::test_api_serializes_curated_reception_with_separate_temporal_and_approval_metadata \
  tests/test_narrative_explorer_api.py::test_ed1c_additional_record_inputs_keep_exact_scope_and_held_ezekiel_bridge_out \
  tests/test_narrative_explorer_projection.py::test_genesis_6_projects_cultural_background_and_comparison_as_distinct_evidence \
  tests/test_narrative_explorer_projection.py::test_psalm_82_cultural_context_is_discoverable_without_a_theme_object \
  tests/test_narrative_explorer_projection.py::test_deuteronomy_32_manuscript_evidence_survives_empty_archaeology_lookup \
  tests/test_narrative_explorer_projection.py::test_genesis_1_keeps_passage_anchored_themes_and_comparative_sources
```

Result: **10 passed**. The Phase 5 literary and cultural evidence regression
also passed separately (**1 passed**). Browser results: **7 passed** across
the selected ED-1C, reader, overview, draft-governance, and source-history
flows. Full frontend, API, and release tests are recorded in
[validation results](validation-results.md) after Phase 7.
