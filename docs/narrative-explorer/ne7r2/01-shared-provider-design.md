# NE-7R2 shared verified CKL provider design

## Scope

One `VerifiedCKLProvider` is created per FastAPI application and stored at
`app.state.ckl_provider`. Companion Context, Narrative Explorer, canonical
read/editor routes, and manual Study-pack construction receive the same
provider. The provider returns the same loaded read-only library for a verified
source identity during that app lifetime.

## Identity and lifetime

Every lookup resolves the current `CKLRepositoryConfig` and derives an identity
from:

- backend and resolved JSON root;
- source inventory file signature (including ctime) and current manifest fingerprint;
- the exact source-content signature, computed once per inventory identity;
- the current canonical inventory fingerprint, validated from every source
  record and computed once per SQLite source identity;
- resolved SQLite path and its device/inode/size/mtime signature;
- stale-index policy, read-only setting, repository cache size, and Vercel mode.

The lightweight file and manifest identity check runs on every provider lookup.
Source-content signature work is single-flight and cached for that ctime-aware
file/manifest identity. A source edit or configuration change selects a new
identity; it cannot select a library verified for the old source. A successful
library is retained per identity until app shutdown. Shutdown closes every
cached repository. FastAPI startup calls `start()` so an application instance
can be restarted by its test/server lifecycle.

## Single-flight and errors

The first caller installs a `Future` under a `Condition`, then performs
initialization outside the lock. Concurrent callers for the same identity wait
on that future. They neither construct another repository nor repeat the full
source inventory validation. No synchronous lock is held across the wait.
Initialization failures complete the future with the original exception,
remove the in-flight entry, and are not cached as successful state. A later
request retries. Shutdown rejects new calls and closes any result that finishes
after shutdown began.

Provider access that may initialize is run through FastAPI's thread pool.
SQLite repository connections are thread-local; no live connection is shared
between request threads. Read-only connections are closed at application
shutdown. The library and its records contain no per-request fields.

## Integrity and backend policy

SQLite startup still runs the full read-only integrity and foreign-key checks,
validates source-manifest metadata, and compares the recorded source-content
signature with the exact current source bytes. It also parses and schema-validates
the complete source inventory, canonicalizes each record, and compares the
resulting fingerprint with the SQLite metadata. The fingerprint calculation
does not build retrieval indexes. Final acceptance also runs
`verify_database(compare_fingerprint=True)` as an independent check. The
verification connection uses a maximum 128 MiB read-only mmap hint; the check
itself remains complete. The provider never builds or downloads an index.
Missing or stale SQLite fails closed on Vercel. Local JSON fallback requires
the explicit `fallback_to_json` policy. A `rebuild` policy does not build an
index or silently select JSON from this read-only provider; it fails closed
and leaves index creation to the explicit build workflow.

JSON initialization still validates and loads the source inventory once per
provider identity. Genesis 2:8's serialized response is identical between the
JSON and SQLite backends.

## Diagnostics

`BHF_COLD_START_DIAGNOSTICS=1` records repository construction, SQLite index
discovery, full integrity verification, manifest validation, inventory
verification, repository readiness, provider waits, and passage retrieval.
Provider snapshots expose aggregate counts without exposing source paths.
These counters are process diagnostics, not request-specific repository state.

The implementation and concurrency test results are recorded in
[02-concurrency-and-integrity.md](02-concurrency-and-integrity.md).
