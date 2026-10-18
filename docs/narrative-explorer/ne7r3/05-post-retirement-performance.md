# NE7R3 post-retirement performance

## Environment and comparison

Measurements ran on Linux with Python 3.12.3. The pre-Task-3 baseline was a
clean archive of `c4e1a7a00dd36d459b0f86088fab28fb864a7eac`; the current build
was that same source snapshot with the uncommitted retirement diff applied.
Both used copies of the same CKL, study, and Tyndale databases. The CKL backend
was read-only SQLite with stale policy `error`; the study database used
`BHF_STUDY_DB_READ_ONLY=1`. Database hashes were unchanged by these probes.

Process-cold means a fresh Python process and app/provider state. The host
filesystem page cache was not flushed, so these values do not represent cold
physical storage. API samples use three fresh processes for cold Genesis
retrieval and three warm calls per process (n=3 cold, n=9 warm); Maps uses
three requests in one fresh process. App import uses five processes. Firefox
uses a fresh browser session for each of three samples. Browser timings include
local driver, loopback transfer, and rendering. These are small local samples,
not percentile estimates or hosted results.

## Matched NE7R3 parent comparison

| Workload | Pre-Task-3 `c4e1a7a0` | Current NE7R3 | Payload / identity |
|---|---:|---:|---|
| `from bhf_web.app import app` | 1,783.932 ms median (n=5) | 1,821.042 ms median (n=5) | Current had one 3,116.574 ms outlier; other four were 1,790.535–1,883.254 ms |
| Reader `/` + `/api/bible/John/1?translation=kjv` | 268.222 ms median combined | 294.547 ms median combined | Home: 75,250 B vs 75,210 B; Bible: 8,014 B both |
| Explorer Genesis 2:8, process-cold | 9,853.012 ms median (n=3) | 9,836.920 ms median (n=3) | 17 items, 131,228 B, identical SHA-256 |
| Explorer Genesis 2:8, warm | 1,518.476 ms median (n=9) | 1,535.801 ms median (n=9) | 17 items, 131,228 B, identical SHA-256 |
| Companion + Explorer, concurrent first use | 11,761.084 ms | 11,769.206 ms | Same two route inputs and read-only source copies; both HTTP 200 |
| John 2 compact Maps | 276.796 ms median (n=3) | 266.717 ms median (n=3) | 69 markers, 187,007 B, identical SHA-256 |

Genesis 2:8 response SHA-256 in both builds:
`31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`.
John 2 compact Maps response SHA-256 in both builds:
`991064790c1e215ce69f09b1885818419c49f90e3f71dd408e0d24eb35aa32`.
The concurrent comparison used
`/api/study/companion-context?book=Genesis&chapter=2&translation=kjv` and
`/api/narrative-explorer/v1/passages/Genesis/2?verse_start=8&verse_end=14`
in both NE7R3 snapshots. This differs from the published NE7R2 concurrent
sample's request payloads, so the two wall times should not be treated as a
direct before/after delta. Both runs performed one repository construction, one full SQLite integrity
verification, one source manifest/inventory verification and fingerprint
comparison, and one single-flight waiter.

For that paired request, Companion returned 98,415 B (SHA-256
`1eb777b9ca1199bb3ceb137caefeeaaedd6c21268ed7ed51bf2b6249ad858a66`) and
Explorer returned 256,876 B (SHA-256
`26a9042a5e0da3bcd124df6903aaea6b3e8c49565003fee7b4a87fdb00fcf25b`) in both
builds.

## Firefox timings

Firefox 155.0.1 and geckodriver 0.37.1, with a fresh app/browser session per
sample (n=3):

| Browser measure | Pre-Task-3 median | Current median |
|---|---:|---:|
| Firefox session creation | 3,182.74 ms | 3,156.67 ms |
| Navigation request | 571.52 ms | 536.06 ms |
| Reader ready after navigation | 2,297.61 ms | 2,399.81 ms |
| Companion context ready after reader | 13,156.59 ms | 13,653.16 ms |

The browser and reader measurements vary by about 100–500 ms across these
small samples. They do not show a consistent reader or database speedup.

## NE7R2 context and interpretation

The NE7R2 report records 1,304.99 ms median app import, 9,892 ms process-cold
and 1,609 ms warm Genesis 2:8 retrieval, 10,526.8 ms for its specific
concurrent Companion/Explorer pair, and 271 ms median John 2 compact Maps.
Differences from the historical NE7R2 table include both source changes since
NE7R2 and run-to-run host variance; the direct Task-3 parent comparison above
isolates this retirement diff more closely.

The wheel fell by 1,566,728 B compressed and its installed payload by about
3.62 MB (see [03-runtime-package-reduction.md](03-runtime-package-reduction.md)).
Those package measurements describe distribution size only. The matched
startup and API timings are effectively flat at this sample size, and the
first-use latency remains dominated by required SQLite/source integrity and
fingerprint verification. No integrity check was removed to improve timing.

## Reproduction procedure

The NE7R2 procedure is documented in
[`../ne7r2/05-performance-and-local-acceptance.md`](../ne7r2/05-performance-and-local-acceptance.md).
To repeat the parent comparison, build two isolated source trees from the
`c4e1a7a0` archive and the same diff-applied snapshot, copy the same three
database files into each, and set the read-only runtime environment as follows:

```bash
BHF_STUDY_DB_READ_ONLY=1 \
BHF_CKL_BACKEND=sqlite \
BHF_CKL_DATABASE_PATH="$PWD/.bhf/ckl.sqlite" \
BHF_CKL_STALE_POLICY=error \
python -m pytest -q tests/test_ne6r2_projection_parity.py
```

The test command confirms retrieval parity; it does not produce timings. For
timed API samples, start a fresh app process, issue the requests below, and
record elapsed wall time, status, byte count, response SHA-256, and provider
counters. The single-request probes use
`/api/narrative-explorer/v1/passages/Genesis/2?verse_start=8` and
`/api/maps/places-for-passage?book=John&chapter=2&include_related_passages=false`.
For the concurrent first-use probe, issue these two requests at once:

```text
/api/study/companion-context?book=Genesis&chapter=2&translation=kjv
/api/narrative-explorer/v1/passages/Genesis/2?verse_start=8&verse_end=14
```

Repeat Genesis three fresh processes with three subsequent warm calls each,
Maps three times in one fresh process, and browser probes with new Firefox
sessions. These probes are diagnostic only; the retirement package delta does
not justify reducing SQLite verification or changing CKL policy.

## Release status

Two frozen v1.2 promotion checks continue to fail on both NE7R2 and NE7R3 due
to the documented historical CKL file-fingerprint discrepancy. The original
artifact is unavailable locally. Separately, the PR-triggered freeze workflow
still requires the retired packaged v1.2 reader data. The checks were not
changed, and the full workflow was not run because its first CKL build step
would regenerate `.bhf/ckl.sqlite`. See
[02-ckl-fingerprint-investigation.md](02-ckl-fingerprint-investigation.md)
and [03-runtime-package-reduction.md](03-runtime-package-reduction.md). These
performance results do not clear either release gate.
