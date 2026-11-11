# ED-4 Retrieval Before and After

Scores are CKL deterministic relevance scores on a 0–1 scale. “Rank” is the
position in the returned result list. Queries and outputs were sampled from the
same fetched ED-3 branch baseline and ED-4 worktree.

## Inherited failures

| Query | Expected primary | Baseline | ED-4 | Relevance change |
|---|---|---|---|---|
| `1 John What if our heart condemns us?` | `1-john` | `john` #1 (0.947); `1-john` #2 (0.931) | `1-john` #1 (0.931); `john` #2 (0.947) | Expected book moved from rank 2 to rank 1; overlapping title no longer masks explicit numbered book. |
| `1 Thessalonians How does 1 Thessalonians relate to Acts 17?` | `1-thessalonians` | `acts` #1 (1.000); `1-thessalonians` #2 (1.000); false `Revelation` reference | `1-thessalonians` #1 (1.000); `acts` #2 (1.000); no false Revelation reference | Primary passage moved from rank 2 to rank 1; supporting Acts passage remains rank 2. |

## Bounded relevance sample

| Query type | Query | Baseline result | ED-4 result | Assessment |
|---|---|---|---|---|
| Explicit verse / disputed passage | `1 John 3:19-24 What if our heart condemns us?` | `1-john` #1 (1.000), `john` #2 | Same order and scores | No regression; explicit scope remains primary. |
| Reversed narrative relationship | `How does Acts 17 relate to 1 Thessalonians?` | `acts` #1, `1-thessalonians` #2 (tie) | Same passage order, with Acts primary by grammatical subject | Subject and supporting context are identified from syntax. |
| Numbered-book comparison | `Compare John 1 and 1 John 1.` | `john` #1, `1-john` #2 | Same | Both requested passages remain in the first two results. |
| Cross-Testament comparison | `Compare Genesis 1 and John 1.` | `genesis` #1, `john` #2 | Same | Both passages remain in the first two results. |
| Hebrew word study | `What does Hebrew hesed mean in Ruth?` | False `Hebrews` reference; `ruth` #1 | Only Ruth is parsed as a book reference; `ruth` #1 (0.990) | False reference removed; lexical Hebrews candidate remains lower in the list. |
| Greek word study | `What does the Greek word for love mean in John 21?` | `john` #1 | Same | Passage book remains primary. |
| Manuscript variants | `What manuscript variants occur in Mark 16:9-20?` | `mark` #1 | Same | Passage remains primary; this evaluator checks scope, not the scholarly answer. |
| Historical context | `What historical evidence illuminates Nehemiah 2?` | `nehemiah` #1; Persian restoration record also ranks highly | Same leading passage and Persian-context record | Relevant context remains available. |
| Archaeology | `What archaeological evidence relates to Hezekiah's tunnel in 2 Kings 20?` | `2-kings` #1; tunnel-inscription record #2 | Same | Text and external evidence remain co-visible. |
| Literary convention | `What literary device shapes Psalm 23?` | `what-is-a-psalm` #1; `psalms` #2 | Same | Passage-book coverage remains available. |
| Later reception | `How was Daniel received in later Jewish tradition?` | `daniel` #1 | Same | Book remains primary. |
| Ordinary-language event | `What happened at the crucifixion?` | `crucifixion` #1 | Same | Relevant event record ranks first without a reference. |
| Ambiguous entity | `Who was John?` | Existing Narrative Explorer test returns no primary result and an ambiguity object | Same | No confident passage is selected for the unresolved title/person ambiguity. |

The raw unprefixed `What if our heart condemns us?` remains a weak lexical query
and does not put `1-john` first. This was not the inherited test input (which
prepends `1 John`) and is documented as follow-up retrieval work rather than
hidden as a success.

## Regression evidence

- New ED-4 retrieval and query-analysis tests: 14 passed, 14 numbered-book
  subtests passed in 82.53 seconds, including the reverse-subject assertion.
- Existing precision and inherited 1 John / 1 Thessalonians suites: 26 passed,
  226 subtests passed in 452.96 seconds. Both formerly failing assertions now
  pass.
