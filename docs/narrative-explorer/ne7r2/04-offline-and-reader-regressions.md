# NE-7R2 offline and reader regressions

## Optional pack lifecycle

`autoInstallOfflinePacks` remains explicitly false by default. The ordinary
Firefox reader startup test saw no `/api/offline/packs/` requests and rendered
John 1. Its KJV chapter response body was consumed at about 3.0 s. The ordinary
reader does not build an optional pack during its opening path.

The manual Study pack request is now built on a worker and receives the shared
verified CKL provider. The focused Firefox probe returned 637 canonical
objects in 11.58 s wall time; the pack builder took 8.67 s and emitted a
15,099,413-byte response. In the final full browser suite, installation and
transfer took 16.34 s while other reader requests were active. Provider
counters showed one repository, one full integrity check, one
source-inventory verification, and a cache hit for pack generation. The reader
reloaded with the Study pack installed. IndexedDB held all 637 objects after
reload and after stopping the server. Disposable browser records confirmed
notes, highlights, and vault settings survived installation. An invalid pack
request returned the expected `unknown offline pack` error and a subsequent
valid Study installation succeeded.

The existing Firefox Maps acceptance still manually installs seven responses,
uses cached Maps data while the server is stopped, and recovers after the
server restarts. The separate browser test that starts Study pack generation
while requesting a Bible chapter confirms the Bible request completes first;
pack construction does not block that reader request.

## Offline reader boundary

The Study pack's local canonical objects and personal-data stores were readable
from the controlled page while the server was stopped. A Firefox WebDriver
refresh with the server stopped reached `about:neterror` in this fixture, even
though the active-page Maps offline request works. The full Chrome PWA suite
(`tests/gui/test_pwa_offline.py`) was skipped because `webdriver_manager` is not
installed. Therefore a cold/offline whole-reader navigation with an existing
Study pack remains unverified. This is recorded as pending acceptance, not a
pass.

The offline install test used disposable browser storage. The protected study
database remained read-only; its final SHA-256 is recorded in
[02-concurrency-and-integrity.md](02-concurrency-and-integrity.md).

## Other reader regressions

General Firefox reader smoke and Geography Firefox acceptance results are
recorded in `05-performance-and-local-acceptance.md`. The project’s known 15
compatibility failures are unchanged and remain individually listed in
[`../ne7r1/03-compatibility-failure-triage.md`](../ne7r1/03-compatibility-failure-triage.md).
