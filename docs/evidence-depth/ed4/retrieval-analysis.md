# ED-4 Retrieval Analysis

## Retrieval path

The production path is deterministic and model-free:

1. The caller sends a question to `CKLRetrievalService.search`.
2. `retrieval.tokenizer.analyze_query` normalizes text, extracts terms and
   phrases, parses canonical Scripture references, and recognizes indexed
   book/title aliases.
3. `CKLIndex` gathers candidates from title, alias, Scripture, keyword, and
   category indexes.
4. `retrieval.ranker.score_indexed_entry` scores evidence and record fields.
5. `CKLRetrievalService._rank_and_limit` orders direct and related results,
   applies scope and category limits, then returns the final list.
6. Narrative Explorer's query-analysis layer handles entity ambiguity and
   constructs passage context before presenting results.

There is no semantic model call or vector database in this path.

## Inherited case A: numbered John

The test sends `1 John What if our heart condemns us?`. Alias recognition
correctly found `1 John`, but indexed-label matching also found the shorter
`John` label inside that same phrase. The ranking layer then treated both book
records as explicitly named. Their lexical scores favored `john` (0.947) over
`1-john` (0.931), so the unnumbered book was returned first.

The correction keeps longest matching title spans and ignores a shorter label
only when every occurrence of it is contained by a longer recognized label.
If a question separately mentions both `1 John` and `John`, both mentions
remain available. This applies uniformly to nested titles across numbered
books.

## Inherited case B: Thessalonians and Acts

The book-reference regular expression required a word boundary before an alias
but not after it. The canonical alias `re` for Revelation therefore matched
inside `relate`; the false book-only reference also consumed text before the
later `Acts 17` reference could be parsed. A similar short alias `heb` matched
inside `Hebrew`.

The parser now requires a word boundary after a book alias and trims trailing
reference punctuation before canonical parsing. The real references survive
without the spurious Revelation result.

Once the false reference was removed, the Thessalonians and Acts book records
had equal direct Scripture scores. Ranking gave neither passage a focus role,
so stable tie-breaks put Acts first. The requested question form explicitly
asks how subject passage A “relates to” supporting passage B. For that
asymmetric grammar only, the first parsed reference is the primary book;
reversing the question reverses the primary result. `Compare A and B` remains
symmetrical and keeps both passages in the leading results.

## Other reference handling

- Explicit verse/range references still take the Scripture-scope path.
- Comparison references remain jointly searchable, including John and 1 John,
  Samuel and Kings, and cross-Testament comparisons.
- Numbered and unnumbered book labels do not shadow one another when both are
  separately named.
- High-level ambiguous-entity handling for `Who was John?` is unchanged and
  continues to return ambiguity instead of a confident passage.
- Ordinary-language queries without a book reference remain lexical searches.
  The unprefixed `What if our heart condemns us?` still does not rank `1-john`
  first in the raw CKL retrieval service. The inherited acceptance case
  explicitly prefixes `1 John`; broader morphology/semantic retrieval is
  outside this bounded correction and remains an evaluation limitation.

## Files changed

- `framework/canonical_library/retrieval/tokenizer.py`: complete book-alias
  boundaries, punctuation trimming, and containment-aware title matching.
- `framework/canonical_library/retrieval/service.py`: relationship-focus
  ordering for explicit `How does A relate/connect to B?` forms.
- `tests/canonical_library/test_query_analysis.py` and
  `test_ed4_retrieval_regressions.py`: parser, reference, ordering, comparison,
  and bounded relevance coverage.
