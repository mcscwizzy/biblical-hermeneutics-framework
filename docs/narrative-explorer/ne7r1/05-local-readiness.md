# NE-7R1 local readiness

**Decision: `BHF_NARRATIVE_EXPLORER_NE7R1_VALIDATION_PENDING`**

## Verified local behavior

- **Ordinary reader:** The expanded Firefox smoke suite loaded Scripture, changed translation, selected a verse range, navigated chapters, returned to the prior chapter, and completed initialization with Explorer disabled. The browser received and parsed a real Bible API response and rendered the selected chapter.
- **Companion:** Existing BHF Commentary rendered for the passage; closing Companion preserved the original book/chapter/verse/translation selection and reading context.
- **Narrative Explorer:** With the flag explicitly enabled in the Explorer test fixture, Firefox opened Genesis 2:8, inspected evidence, followed an authored Evidence Trail, and returned to Scripture. The dedicated geography suite passed.
- **Maps:** Passage-first John 2 Maps returned compact markers, selected a place, loaded the full related passages, preserved selection acknowledgment, and returned to reading.
- **Recovery:** The geography browser suite stopped and restarted its server, exercised cached/offline reading, restored connectivity, and retried the pending operation successfully.
- **Disabled feature:** Ordinary-reader startup did not issue Narrative Explorer API requests. Explorer remains off by default.
- **Source and database:** The NE-7 CKL identities and protected study database checksum were preserved; verification is repeated before commit.

Detailed commands and results are in `04-integration-regression-results.md`. The full 15-test compatibility failure set remains characterized in `03-compatibility-failure-triage.md`; those failures were not edited to green.

## Unresolved local work

- The first Explorer request remains slow when Companion Context and Narrative Explorer each perform their own cold read-only source-fingerprint verification. Fingerprint checks remain enabled. Share a process-scoped verified CKL provider and add a concurrency test before claiming first-interaction performance is closed.
- Fifteen established Commentary/archaeology compatibility failures remain. Their evidence, prompt, rights, and packet identity gates remain fail-closed.
- The full web-app suite, Python compilation, JavaScript syntax check, and CKL/source identity checks completed. Five separate `tests/gui` focus/accessibility cases were skipped because the sandbox denied local socket binding; Firefox browser coverage remains the local evidence for those workflows.

## Not verified here

| Area | State |
|---|---|
| Real screen-reader output and spoken focus order | **Unverified.** Headless Firefox DOM and keyboard checks do not establish screen-reader acceptance; no usable accessible desktop/speech session was available. |
| 390-pixel mobile layout | **Unverified.** Firefox clamps the requested 390 × 844 viewport to 500 × 758 in this environment. |
| Hosted SQLite runtime and hosted cold starts | **Unverified.** Local read-only SQLite parity and request timing do not prove the index is packaged or verified in Vercel. |
| Hosted Tyndale provisioning | **Unverified.** Local UI fixtures do not prove the Tyndale archive is provisioned in a hosted runtime. |
| Vercel function packaging | **Blocked.** The latest recorded build failed with `LAMBDA_SIZE_EXCEEDED`: 317.82 MB against the 225 MB limit enforced for that deployment. No Vercel settings were changed in NE-7R1. |
| Public launch | **Not ready.** Local browser success does not resolve the hosting, accessibility, viewport, Tyndale, compatibility, or first-use contention gates. |

## Preserved identities

- CKL objects: **687**.
- CKL inventory fingerprint: `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.
- Source inventory signature: `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea`.
- Source manifest fingerprint: `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`.
- Protected study DB SHA-256: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.
- `BHF_NARRATIVE_EXPLORER_ENABLED` and `BHF_AUTO_INSTALL_OFFLINE_PACKS` both resolve false by default.

## Transaction boundary

- Branch: `fix/narrative-explorer-ne7r1-reader-reliability`, based directly on NE-7 `a7e6242d378361b77f2d20e4be7e9eef57252b45`.
- Master base: `480141f9b19e627c3f1d59ee67ad6aa6562812bd`.
- `vercel.json` master deployment safeguard remains `false`.
- Narrative Explorer remains disabled by default.
- No push, merge, deployment, Vercel configuration or environment update, CKL/Commentary/translation update, evidence generation, or protected study schema change was authorized or performed.
- The final report records local HEAD and its parent, clean-tree status, and protected data verification. The final commit SHA cannot be embedded in its own commit without changing that identity.
