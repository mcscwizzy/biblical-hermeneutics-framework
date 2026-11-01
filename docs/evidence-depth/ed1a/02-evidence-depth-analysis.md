# ED-1A evidence depth analysis

## How this audit measures depth

The audit is deterministic and does not score a chapter. It joins the NE-A1 full-chapter census to CKL objects and their typed children by Narrative Explorer's exact stable identities. It uses the current projector to determine eligibility and reader section assignment, then counts explicit CKL types and citation metadata. It never classifies evidence by scanning its prose for keywords.

For each projected child record, the script uses the child's own canonical Scripture references first. If it has no child reference, the parent's reference is recorded as inherited context. It distinguishes verse, chapter, book-wide, multi-chapter, unanchored, and invalid scopes. A broad citation can be traceable and useful while still being less specific than a verse-scoped record.

Across the 1,189-chapter projection, the script counted **8,484 typed child-record placements with an applicable valid scope**: 6,276 verse-scoped, 8 chapter-scoped, and 2,200 broad book- or multi-chapter placements. No projected child placement inherited only the parent object's scope. These are overlapping placements, not 8,484 distinct CKL records. The out-of-bounds Obadiah note is detected by the NE-A1 validation path but is not a valid projected child placement.

The current NE-A1 chapter category `passage_specific_evidence` uses a minimum test: a directly projected, applicable claim or evidence item cites a source present in its parent bibliography, and the source has a title plus one bibliographic detail. It is an availability indicator. It does not establish the depth, quality, relevance, originality, or adequacy of the research. One CKL record can count in several chapters; placement totals are not unique-record counts.

## Domain results

The traceability threshold above is applied to explicit child source IDs. The category counters below count scoped CKL child-record placements; a child can receive more than one domain tag where its explicit type warrants both. Chapters without a tag remain unknown until a reviewer inspects the record.

| Domain indicator | Source-traceable record placements | Chapters with a source-traceable typed record | What this does and does not measure |
| --- | ---: | ---: | --- |
| Historical and cultural | 2,305 | 499 | Historical/cultural claim, context, period, person, people group, institution, practice, or worldview type. It does not guarantee coverage of all the historical subtopics in the request. |
| Lexical language | 140 | 100 | Only `claim_type=lexical`; ordinary Greek/Hebrew dictionary and token availability is counted separately. |
| Literary form | 1,889 | 758 | Literary claims, literary-convention evidence, and literary-observation notes. Generic `biblical_text` claims and `textual-observation` notes are not silently classified as literary form or textual criticism. |
| Ancient primary sources | 594 | 228 | Child records typed as ancient text, manuscript, primary source, inscription, or with an attached ancient-primary-source source type. It does not imply that an ancient source is contemporary with the biblical event. |
| Archaeology and geography | 429 | 198 | CKL's archaeology/geography type tags. Archaeological catalog depth and rights-bearing media remain owned by the archaeology service. |
| Biblical narrative connections | 351 | 225 | Canonical-connection and later-reception note types plus reception-history claims. It is not a count of accepted NE-9C routes or verified NE-10 bridges. |
| Scholarly discussion signal | 7,137 | 916 | Records with explicit uncertainty or dispute metadata. This is a proxy for a need to handle interpretation carefully, not proof the record documents multiple scholarly positions. |

The exact per-book and per-chapter values are in the machine-readable summary and CSV. Text-observation notes (`textual-observation`) remain a separately counted CKL type: **1,320** corpus notes. They include a broad range of text observations and cannot be counted as textual-critical apparatus without inspecting their contents and source support.

## Historical and cultural context

Typed historical/cultural content is widely distributed, but it is not uniformly passage-scoped. Whole-book objects and multichapter clusters repeat across chapter views. Psalm books, wisdom literature, and Chronicler material remain sparse in several distinct ways even where their general objects exist. In the current chapter inventory, Psalms has 74 chapters with no eligible CKL item and only 6 chapters with a source-traceable historical/cultural type. 2 Chronicles has 14 chapters with no eligible item and one chapter with a source-traceable historical/cultural type. Proverbs has 12 empty chapters and three chapters with a source-traceable historical/cultural type. Ezekiel has 9 empty chapters and four chapters with such a type.

Those gaps call for passage selection and human judgment. A Psalm does not automatically need a political chronology or archaeological site; a wisdom saying does not need a map; an exilic temple vision should not be anchored to a modern site by resemblance. Historical circumstances, audience, institutions, customs, and economics should be researched where they clarify the passage's own language and setting.

## Language and literary evidence

The word-study service provides broad lexical lookup and aligned original-language tokens for all canonical chapters. At the same time, the CKL has only **107** claims typed `lexical` in its full corpus. The two figures answer different questions: one is lookup infrastructure, the other is typed curated research. A dictionary entry or lemma count is not evidence that a passage's usage, syntax, idiom, discourse role, or alternative readings have been studied.

The audit therefore counts passage-scoped `lexical` claims separately from literary structure and form. Existing literary claims, literary-convention evidence, textual observations, and textual witnesses should remain distinguishable. For textual criticism, the useful unit is an identified reading or witness with a precise passage, source and locator, chronology, and an explanation of its interpretive consequence; an ordinary note saying “the text says” does not meet that definition.

## Ancient texts and primary evidence

The CKL has 31 `ancient-text`, 11 `manuscript`, 17 `inscription`, and 6 `primary-source` evidence items. Its bibliography has 128 unique IDs typed `ancient-primary-source`. These counts overlap and should not be summed as if they were independent objects. The safest next work asks whether a given source is primary for the claim, whether it is contemporary or later, and what the source actually says in its own genre and political setting.

Second Temple texts, the Septuagint, and manuscript witnesses can illuminate reception or textual history without being collapsed into the setting of an earlier biblical passage. The NE-10 registry's 44 verified records and 7 separately held candidates maintain these distinctions; ED-1A does not turn thematic proximity or a shared source into a route. The held Deuteronomy 32/Psalm 82/Job 1 and Ezekiel 40–48/Revelation 21–22 candidates remain held under the existing scholarly decisions.

## Archaeology and geography

The stored external-link inventory is healthy at the schema and target level: every recorded map and service reference passed validation. Archaeology service evidence is explicitly linked to 75 service items and 71 of those items have valid passage links; four inventory items have no valid passage link. Map-place inventory has 1,338 items, with 1,281 having valid linked references and 57 without one. These are domain-integration review candidates only. They do not demonstrate that those items should link to a biblical chapter. Six map files have 222 static feature passage links. Dynamic resolver results were checked for 16 sampled API builds; unqueried chapters remain unknown for text-based dynamic resolution.

In a pilot, the CKL should provide concise passage relevance and an external stable ID. The archaeology domain should continue to own the catalog description, dating basis, context, excavation history, media rights, and artifact attribution. Coordinates and modern identifications require their own confidence and source trail.

## Narrative connections

The raw 4,061 authored object edges are not passage routes. NE-9C decisions determine which authored relationships are accepted for reader use; NE-10's 44 exact bridge records are a separate presentation registry. The ED-1A type scan counts scoped textual connection records but deliberately does not reinterpret those curation decisions. Each future relation still needs an exact record, passage scope at both ends, type-specific evidence, source support, chronology, and preserved uncertainty. Held and excluded records remain out of the accepted route graph.

## Scholarly discussion

Explicit uncertainty metadata is common: the current proxy places uncertainty/dispute-tagged, traceable records in 916 chapters. The high count does not mean readers can inspect a structured set of competing positions. The pilot review should determine whether major controversies actually include the major alternatives, their supporting evidence, the sources and specific locators, confidence and limits, and the distinction between original setting and subsequent theological reception. For chapters without a meaningful scholarly dispute, no “both sides” content should be manufactured.

## Interpretation limits

- No count is a quality score or a per-chapter quota.
- A complete empty lookup means “not represented by eligible CKL material in this projection,” not “nothing is known.”
- An attached bibliography entry is not child-level support unless the child names its source ID.
- A title-plus-one-detail threshold detects only minimal bibliographic traceability; it is not a universal citation-style requirement.
- A typed tag is a search signal, not a scholarly verdict. Untagged prose, unclassified section items, and dynamic resolver-only results need human review.
- The audit does not infer a quotation, dependence, site, route, date, or theological conclusion from common vocabulary, coordinates, or an empty result.
