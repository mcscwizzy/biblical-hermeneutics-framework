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

## Preserve a relevant ordinary-language result

The added trailing boundary also stops the substring `Judges` from being
parsed inside “judging” in the question “What does Paul mean by judging
nothing before the time?” That removed an accidental book-category bonus that
had placed `1-corinthians` first, exposing a real relevance weakness: the
topical Pauline object ranked above the book record even though its
passage-anchored note uses the query wording and cites 1 Corinthians 4:5.

The shared coherent-match index now also considers the text of an individually
Scripture-anchored interpretive note as one bounded unit. It does not add
rationales, caveats, unanchored notes, or references to that unit. The query
has no detected Scripture reference, and `1-corinthians` ranks first from its
four-of-five term match in the verse-specific note. Existing negative tests
confirm that dispersed notes and rationales do not create false coherent
matches. This applies across passage-anchored notes without a book-specific
rule.

## Unprefixed heart-condemnation question

The exact ordinary-language query `What if our heart condemns us?` had no
parsed Scripture reference. On the ED-3 baseline, `ezekiel` ranked first at
0.7163, while `john` ranked second at 0.6395; `1-john` was absent from the
first five results. Two general retrieval details caused this: `if` remained
as a high-weight query token, and the query form `condemns` did not match the
passage-anchored wording `condemning` in 1 John 3:19–24.

The tokenizer now treats the common question word `if` as a stop word. The
existing coherent-match signal also recognizes a bounded progressive form on
the evidence side for long terms, including doubled-final-consonant forms.
Query tokens remain intact, and the match is available only inside the same
claim, descriptive evidence unit, or individually passage-anchored note. This
avoids globally stemming short or unrelated terms. With this correction the
query has substantive terms `heart` and `condemn`; the `1-john` claim
`1jn-heart`, anchored to 1 John 3:19–24, covers both and ranks first at 0.8694.
The fix is covered by the exact unprefixed-query regression and the complete
retrieval suite.

## Other reference handling

- Explicit verse/range references still take the Scripture-scope path.
- Comparison references remain jointly searchable, including John and 1 John,
  Samuel and Kings, and cross-Testament comparisons.
- Numbered and unnumbered book labels do not shadow one another when both are
  separately named.
- High-level ambiguous-entity handling for `Who was John?` is unchanged and
  continues to return ambiguity instead of a confident passage.
- Ordinary-language queries without a book reference remain lexical searches.
  The exact heart-condemnation query now ranks its anchored 1 John claim first;
  query tokens are otherwise unchanged and no global stemmer or semantic model
  was introduced.

## Files changed

- `framework/canonical_library/retrieval/tokenizer.py`: complete book-alias
  boundaries, punctuation trimming, containment-aware title matching, and
  common question stop words.
- `framework/canonical_library/retrieval/ranker.py`: scoped progressive-form
  comparison for coherent anchored evidence.
- `framework/canonical_library/retrieval/service.py`: relationship-focus
  ordering for explicit `How does A relate/connect to B?` forms.
- `framework/canonical_library/retrieval/indexer.py`: coherent matches from
  individually passage-anchored interpretive-note text.
- `tests/canonical_library/test_query_analysis.py` and
  `test_ed4_retrieval_regressions.py` and `test_ckl_retrieval_service.py`:
  parser, reference, ordering, comparison, anchored-note relevance, and
  bounded negative-control coverage.
