# NE-5A Narrative Explorer response fixtures

These are the exact uncompressed JSON response bodies returned by the
unmodified NE-5A API at commit `bf1c4772f03f4aa12aef2a0faa5a5aaa1e54b005`.
They cover all seven pilot chapters and the selected verse ranges listed in
`scripts/benchmark_narrative_explorer_ne5b.py`.

The capture used the read-only SQLite CKL repository and study database with
SHA-256 values:

- CKL: `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`
- Study DB: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`

Each file preserves the exact API response bytes for complete post-change
parity checks. The NE-5B results document records response sizes, item and
connection counts, domain states, and SHA-256 values.

The benchmark harness can compare the live API response bytes to these files
without overwriting them:

```bash
python scripts/benchmark_narrative_explorer_ne5b.py \
  --revision <revision> \
  --branch <branch> \
  --output /tmp/narrative-explorer-benchmark.json \
  --fixtures tests/fixtures/narrative_explorer/ne5a_baseline \
  --compare-fixtures
```
