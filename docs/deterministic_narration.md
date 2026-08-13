# Deterministic CKL narration

The narrator is an offline presentation layer above already-selected
Canonical Knowledge Library (CKL) evidence. It is not a replacement for CKL,
an article generator, an interpretation engine, or an AI system. It performs
no broad retrieval and does not modify canonical records.

## Evidence to sentence

`CanonicalNarrator` accepts a CKL object, a list of retrieved objects, or a
context-builder payload. It uses selected claims first, then structured
interpretive notes, then context fields, and finally legacy summaries. Claim
and note taxonomy is mapped to a small set of presentation roles in
`narration/roles.py`. Recipes in `narration/planner.py` decide which roles are
useful for historical, cultural, literary, archaeological, canonical, and
covenant context.

The planner uses the retrieval score and Scripture scope already attached to
the supplied evidence. Direct passage references outrank chapter and book
context. It applies small fixed budgets so the primary UI stays readable;
`additional_evidence_count` reports what was left out while the raw CKL
records remain available to the evidence UI.

## Provenance and qualification

Every `NarratedSentence` retains claim IDs, source IDs, Scripture references,
certainty, dispute status, evidence IDs, and content/review status. Sources
are not inferred from prose. Certainty and dispute mappings in
`narration/certainty.py` provide stable, concise qualifications; interpretive
notes keep their authored wording while their metadata remains visible in the
structured result.

To add a role or recipe, update the role mapping and the recipe in separate
focused changes, add a provenance assertion, and test the no-evidence and
passage-scope cases. Do not add a generic transition that asserts significance
unless the supplied CKL evidence states that relationship. The narrator may
verbalize supported significance, but it must never supply missing theology or
historical claims.

The Study Companion consumes narration as an additive summary. AI prompt
context construction and raw CKL evidence packaging remain separate paths.
