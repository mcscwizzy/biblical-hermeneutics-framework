# NE-7R2 concurrency and integrity

## Paths before the change

The app constructed a `NarrativeExplorerService` and a separate
`CompanionContextService`. Each had its own canonical-library provider and
service-local cache. On concurrent first use, both could construct a repository
and verify the same source inventory. Canonical API/editor reads and the Study
offline pack also called the legacy default loader instead of reusing the app's
verified library.

## Reuse after the change

All compatible app consumers now receive `app.state.ckl_provider.get_library`.
Explorer and canonical provider resolution run in the thread pool; Companion
Context already runs its build in a worker. The Study pack is built in a worker
and receives the same provider. The app records one successful initialization
per source identity and closes repositories on shutdown.

Measured concurrent direct first use on the verified local SQLite index:

| Measure | NE-7R1 | NE-7R2 |
|---|---:|---:|
| Simultaneous Companion + Explorer lookups | 957 ms direct lookup | 10,527 ms FastAPI wall |
| Repository constructions | 2 | 1 |
| Complete source inventory verifications | 2 | 1 |
| Canonical inventory fingerprints computed and compared | 0 in that comparison | 1 |
| Full SQLite integrity verifications | 0 in that comparison | 1 |
| Single-flight waiters | n/a | 1 |

NE-7R2 takes longer for this process-cold comparison because its single
initialization now retains both the complete SQLite integrity gate and the
canonical source fingerprint check. The measured improvement is reuse: the
two consumers share one repository and one verification sequence. The final
fresh-app API probe completed in 10,527 ms overall. Both requests returned
HTTP 200; Companion Context returned 102,915 B (SHA-256
`3e28a8801563b29422507763504aa90fe2e0d292a4eb2a287d1d27884929569b`) and
Explorer returned 131,228 B (SHA-256
`31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`). The
provider constructed one repository, ran one full index integrity scan, one
source-manifest validation, one source-content signature computation, one
canonical source fingerprint computation and comparison, and recorded one
single-flight waiter.

Eight concurrent Explorer API calls also produced one repository construction,
one source-content signature computation, one canonical source fingerprint
computation and comparison, and one inventory verification. Companion plus
Explorer initialization shared the same entry. Tests cover failure
propagation/retry, backend and source-root
changes, database path/signature changes, Vercel missing-index failure,
provider close/restart, event-loop health-route responsiveness, parallel
thread-local SQLite reads, response bytes, and consumer re-resolution.

## Genesis 2:8 response parity

SQLite and explicit JSON fallback returned the same Genesis 2:8 projection:
17 items, 131,228 serialized bytes, SHA-256
`31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`.
No CKL object, claim, evidence, source, passage association, classification,
geographic certainty, authored relationship, citation, or Evidence Trail limit
was changed.

## Verified authoritative fingerprints

The final read-only verification ran `verify_database(...,
compare_fingerprint=True)` against the configured SQLite index and current JSON
source tree. It returned `integrity_check=ok`, no foreign-key errors, and:

- CKL objects: **687**
- inventory fingerprint: `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`
- source inventory signature: `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea`
- source manifest fingerprint: `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`
- protected study database SHA-256:
  `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`

The SQLite index was opened read-only. The protected study database was guarded
by `BHF_STUDY_DB_READ_ONLY=1`. No CKL source or study database content was
changed.
