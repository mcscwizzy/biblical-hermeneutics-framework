# Commentary v1.2 corpus runner

The bounded runner discovers canonical Scripture in BHF order, treats the
packaged v1.2 release and its own immutable result receipts as terminal state,
and selects at most 25 chapters by default (50 maximum). It delegates each
selected chapter to the existing CommentaryGenerator path and preserves the
returned classification without changing v1.2 validation or publication code.

The persisted v1.2 candidate state contains the explicit
`full_bible_generation_authorized` guard. Dry runs are allowed regardless of
the guard; generation fails closed while it is false.

```bash
.venv/bin/python tools/commentary_v12_corpus.py dry-run --batch-size 25
.venv/bin/python tools/commentary_v12_corpus.py generate --batch-size 25 --config PATH
```

Each generation invocation creates an immutable manifest and per-chapter
result receipt under
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/corpus-runner/`.
The next invocation rescans those receipts and skips terminal results. Duplicate
or conflicting identities, invalid package checksums, non-terminal persisted
results, and pipeline status mismatches stop the run without guessing.
