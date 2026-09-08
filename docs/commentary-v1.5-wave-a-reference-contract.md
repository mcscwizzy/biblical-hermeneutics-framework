# Commentary 1.5 Wave A reference-contract trace

## Finding

Wave A exposed a boundary mismatch between the canonical Scripture-reference
parser used by synthesis schema 1.1 and the private verse-only regular
expression used by Commentary schema 1.2 validation. The synthesis compiler
was producing valid, deterministic contextual references such as `Daniel 9`
and `Judges 19`; the Commentary validator rejected those strings before it
could apply section or passage-scope semantics.

The `MALFORMED_SECTION` result reported for Daniel 9 was secondary. Its section
objects were well formed, but every block in the affected sections was
rejected for a malformed reference. Once those references are parsed under the
existing contract, the original response has no independent section error.

## Contract traced end to end

```text
CKL authored passage_anchors
  -> EvidenceBundle 1.1
  -> synthesis compiler/schema 1.1
  -> Prompt 1.5 synthesis units and citation summary
  -> Commentary schema 1.2 string verse_refs
  -> section-aware Commentary validator
  -> Gate v2.1 / scale evaluator
```

`source_anchors` and `verse_refs` are distinct. `source_anchors` preserve the
original authored CKL passage anchors for provenance. `verse_refs` are the
compiler's deterministic, reader-facing projection. A cross-chapter authored
anchor is split into chapter-local references; a unit marked
`SURROUNDING_PASSAGE` retains only the external projection and is routed to
`surrounding_passages`.

The canonical grammar already implemented by
`framework.canonical_library.scripture` is:

- `Book Chapter`;
- `Book Chapter:Verse`;
- `Book Chapter:Verse-Verse`;
- canonical chapter ranges and cross-chapter spans for contextual parsing;
- semicolon-separated compound references only in the multi-reference helper,
  not as one Commentary `verse_refs` entry.

Commentary validation applies the existing section boundary to that grammar:

- ordinary sections require a target-chapter, verse-level, contiguous
  reference and reject cross-chapter or wrong-book references;
- the existing verse-optional contextual sections may use a chapter-only
  target reference when verse anchoring is not more precise;
- `surrounding_passages` may use canonical chapter-only, verse-level,
  chapter-range, or cross-chapter contextual references, including chapters
  outside the target chapter;
- malformed syntax, unknown books/chapters, impossible ranges, and prose in a
  reference field remain rejected.

No prompt, schema, synthesis compiler/schema, Gate, CKL record, or protected
v1.1 artifact was changed. The correction is limited to replacing the
validator's narrower duplicate parser with the existing canonical parser and
keeping the section-aware scope checks at the validation boundary.
