# NE-6R2 — Index Integrity and Projection Parity

## Source and index identity

The build ran from the committed `framework/canonical_library` JSON inventory in the NE-6R2 worktree. It generated a new package-owned index rather than copying any local database. The verified build report was:

| Field | Value |
| --- | --- |
| Database schema version | `4` |
| Retrieval-index version | `3` |
| Object count | 687 |
| Claim count | 2,329 |
| Source count | 5,232 |
| Evidence count | 1,297 |
| CKL inventory fingerprint | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` |
| Stable manifest fingerprint | `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40` |
| Manifest file SHA-256 | `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4` |
| Full JSON source-inventory signature | `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea` |
| Generated SQLite size | 116,334,592 bytes |
| Generated SQLite SHA-256 | `0f7552f335ca88acf0a1ea1e49cdbf6a76b1e550191dc89d7e2ff742e76737c9` |

The source inventory is the unchanged CKL JSON tree from NE-6R1 commit `60b582764092ba920f34aa97ee77e56a3b44d18b`; the inventory files and manifest have no diff from that baseline. It included 687 object JSON files plus the manifest (688 files total, approximately 15,163,112 bytes). The verifier checked all required indexes, exact source identity, schema and counts, `PRAGMA integrity_check=ok`, and an empty `PRAGMA foreign_key_check`. The index has no WAL sidecars after the runtime proof. It is ignored by Git and is not committed.

## Runtime selection and fail-closed behavior

With `VERCEL=1`, the deterministic path is the package-owned `framework/canonical_library/data/ckl.sqlite`. A local runtime proof patched JSON repository construction to fail if invoked, selected `SQLiteCanonicalLibrary`/`SQLiteCanonicalRepository`, retrieved Genesis 2:8, confirmed read-only/query-only state, rejected a write attempt, and observed unchanged database SHA and a one-file data directory after access.

Focused tests verify clear failures for a missing index, stale source inventory, mismatched manifest, incompatible schema/retrieval version, and conflicting backend/database path. The missing-index test also fails if runtime invokes `build_database`, proving there is no request-time rebuild. JSON fallback remains a separate local mode; it is not considered a successful indexed verification.

## Exact projection parity

`tests/test_ne6r2_projection_parity.py` builds a fresh index from the source root in a temporary directory and compares JSON and SQLite serialized Narrative Explorer projections. It covers 14 scopes: Genesis 1, Genesis 2, Genesis 2:8–14, Genesis 3, Genesis 6, Genesis 6:1–4, Deuteronomy 32, Deuteronomy 32:8–9, Psalm 82, Exodus 3, Exodus 3:1–6, Acts 7, Joshua 1, and Joshua 1:1–9. The self-contained test passes the same deterministic domain lookup inputs to both backends and passed `1 passed in 184.04s`.

For end-to-end source parity, the same 14 scopes were also run with the real read-only study DB and the normal Maps/archaeology service lookups. Each JSON-source projection and package-index projection produced identical canonical serialized bytes and hashes:

| Scope | Bytes | Canonical SHA-256 |
| --- | ---: | --- |
| Genesis 1 | 262,865 | `3c1e03c0c622a30bef7b74f6925f4bdc6a2f8bf2b99a6a796bb10691f3d4ab9a` |
| Genesis 2 | 423,882 | `b0276f28dcc4bb2c950b015fa369938c76b2bd14fcd7cb54e339a434187fab3d` |
| Genesis 2:8–14 | 256,876 | `eb324329f33b9f171290def43e11c16460e3fe12b71e80c7c4431c5707c01d36` |
| Genesis 3 | 155,665 | `f56efb8e8ddb499c8a71b2ae9bd602dbb56b030ff03ce3ca81668331602b0df3` |
| Genesis 6 | 248,747 | `7978d8ded88a77c549565d6df180b3b82cdd30fa15d4732c052b2c0fccd6c190` |
| Genesis 6:1–4 | 164,791 | `2bb868090fdf4cbc7cb6c33db35892a080ea7db282252342031238ed62ce6fd1` |
| Deuteronomy 32 | 461,816 | `d326f7aeaf1708ca760ff88ec05047095b087f70d25fb1f9264bde5acd0d382f` |
| Deuteronomy 32:8–9 | 84,721 | `d9e2439da6893b11225f3408d552c5ccb5262f0faae6dd5e73908bbe5818feac` |
| Psalm 82 | 45,386 | `c7bb6219fe7c89efe16ce8556baf328ecc6ad15639b74ed13d263652863d3bf8` |
| Exodus 3 | 564,363 | `25acbcc3f4ba187b25bd93d7a385b3adacdb1599755d54784d6d5fd9cc53fb09` |
| Exodus 3:1–6 | 197,893 | `23dfbacf57feb6c8869d9eb59e0f92baabcc3db776f4b966d26927e48ccbb183` |
| Acts 7 | 711,019 | `f0818c51924a058a4222b213b5fdbdf887af06af670e419ec4327fe3eaa71899` |
| Joshua 1 | 298,418 | `5595a2dc032ee3028988a7a292d20aaafa495605e94672d5edfa85bce36db3c7` |
| Joshua 1:1–9 | 294,614 | `a162ef158b72a507fdca9d9669b37a78444c02a0a7051cea15b9c1f1daa4a6b9` |

The compared projection includes item IDs; claim/evidence IDs; scripture anchors; connection identities; section assignment; bibliography; confidence and dispute metadata; geography identification; uncertainty and displayability; coverage states; and navigation targets. Both passes cover withheld Eden precision, Horeb/Sinai uncertainty, Acts 7 Nile, and Joshua 1 Negeb. The real-domain pass used 14 read-only DB-backed projections and confirmed study database SHA unchanged. Neither pass expands or modifies source evidence.

## CKL and protected study data safety

No CKL object, claim, evidence relationship, manifest, fingerprint, or source inventory file changed. The protected study DB was read through `BHF_STUDY_DB_READ_ONLY=1`; observed SHA-256 remained `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`, schema migration version remained 37, and `integrity_check` remained `ok`. Browser-injected map records were test-only intercepted responses; they were not written to the study DB or catalog.
