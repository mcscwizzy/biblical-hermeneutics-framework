# Source Integrity Fixes

## Applied

1. In `framework/canonical_library/objects/cultural_background/roman-ephesus-civic-cultic-and-household-life.json`, changed the two unresolved IDs in one interpretive caution to the exact local records `harland-associations-ephesus` and `glancy-slavery-ephesus`. Their title/author/publication identity is present in the same object. No bibliography record was fabricated, and no other CKL object's locally scoped source IDs were rewritten.
2. In `framework/canonical_library/objects/books/psalms.json`, corrected the Psalm 17 source note to say that the full Italian article was read, record its relevant pages, preserve its lack-of-consensus qualification, and state that its cited manuscript apparatus remains independently unchecked. Updated the evidence confidence rationale and interpretation to match the article-level scope without asserting manuscript confirmation or original priority.

## Retained findings

- `patristic-minor-prophets` remains without a specific locator. The OUP
  catalog verifies the book identity but not the Malachi passage locator.
- The 102 source-support-target heuristic findings remain visible. No checker
  rule was weakened, and the 19 unresolved semantic targets were not guessed.
- No broad repair was made to the 558 sparse bibliography IDs. Exact
  publication-level review and dependency analysis are still needed.

## Validation required

Validation after these data edits: `python3 tools/validate.py framework/`
reported 94 valid modules; the deep CKL report found 687 valid objects, zero
unresolved child-source references, 102 inherited source-support-target
signals, zero strict errors, and 14 inherited warnings. Focused Psalm/Ephesian
coverage tests passed (17 tests); manifest, schema/package, and source-lock
tests passed (51 tests). Protected curation regressions remain for the final
governance phase. No human scholarly review field or approval state was changed.
