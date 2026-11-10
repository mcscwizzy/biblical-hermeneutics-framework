# ED-2A additions and chapter coverage

## Exact additions

All nine new evidence records are in `framework/canonical_library/objects/books/psalms.json`. Their CKL state is `draft` / `in_review`, with an empty human reviewer list and `human_review_required: true`. None adds `related_objects` or `related_evidence`; the projection exposes only the direct Scripture anchor authored on each record.

| Evidence ID | Exact anchor | Genre / research question | New scholarly source ID(s) |
| --- | --- | --- | --- |
| `psalm-06-embodied-lament-language` | Psalm 6:2–8 | Individual lament; body and life/self idiom | `wessels-coetzee-psalms-body-2013` |
| `psalm-15-ethical-entrance-liturgy` | Psalm 15:1–5 | Ethical entrance-liturgy classification and its limits | `boloje-groenewald-psalm15-2016` |
| `psalm-30-superscription-and-reuse` | Psalm 30:1–12 | Distress/thanksgiving movement and ambiguous dedication title | `sommer-psalm30-2022` |
| `psalm-37-acrostic-gap-debate` | Psalm 37:1–40 | Wisdom acrostic; missing ayin unit and interpretation debate | `benun-acrostics-psalms-2006` |
| `psalm-44-communal-lament-and-book-context` | Psalm 44:1–26 | Communal protest and qualified Book II–III memory proposal | `verde-psalms-trauma-2022` |
| `psalm-47-enthronement-hymn-setting-debate` | Psalm 47:1–9 | Kingship hymn and disputed cultic reconstruction | `perdue-psalm47-1974` |
| `psalm-67-jussive-call-and-cultic-setting-debate` | Psalm 67:1–7 | Petition/jussive pattern and harvest-setting disagreement | `botha-psalm67-2004` |
| `psalm-96-kingship-hymn-and-memory-proposal` | Psalm 96:1–13 | Universal praise and qualified memory/resilience reading | `hays-psalm96-2023` |
| `psalm-145-nun-verse-witness` | Psalm 145:13 | Masoretic, Qumran, and Greek nun-strophe witnesses | `sanders-11qpsa-1965`, `rahlfs-hanhart-septuaginta-2006`, `gentry-textual-criticism-2020`, `iaa-11q5-digital-library`, and `benun-acrostics-psalms-2006` |

Each record also cites the existing `psalms-masoretic` primary-text source. Psalm 96 additionally cites the Greek edition for its versional framing. The twelve new bibliography IDs each identify one distinct publication or archive record; see [sources.md](sources.md).

## Before and after by chapter

The before state is the reproduced ED-1A audit at the ED-1C merge. The after state is produced by rerunning the same audit against the nine-item CKL change and the same local study-database snapshot. Counts describe chapters, not number or quality of evidence records.

| Coverage category | Before | After | Change |
| --- | ---: | ---: | ---: |
| No eligible CKL material | 74 | **66** | −8 |
| Contextual coverage | 22 | **22** | 0 |
| Passage-specific evidence | 53 | **61** | +8 |
| Entity-only coverage | 1 | **1** | 0 |
| **Psalms chapters** | **150** | **150** | **0** |

Eight previously uncovered Psalms gain eligible passage-specific coverage. Psalm 44 stays in the passage-specific category because it already had the claim `psalms-lament-praise-range`; the new, distinct item deepens that chapter without changing the chapter count. Psalm 72 remains unchanged as the ED-1B positive control.

The exact post-run audit output, fingerprint, and per-chapter item counts are recorded with the validation results in [04-regression-compatibility.md](04-regression-compatibility.md). Historical ED-1A counts are reference points only.

The final NE-A1 run validated 1,189 chapter rows with zero unmapped record identities and `pass` status. Its CKL inventory fingerprint is `45bc240f39f258fc9ef46c62d083eef87d8d60a346d40052ed0b1895c8156095`. All nine new passage anchors resolve to the intended chapters; the Psalms chapter rows contain no invalid anchors.
