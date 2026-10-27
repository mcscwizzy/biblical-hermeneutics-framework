# NE-11D Vercel release readiness

## Deployment state

| Environment | Deployment | Commit / source | State |
|---|---|---|---|
| Production | `dpl_4X8FwBmG9EznqymqZRP52bQzhghJ` | `e2f696db98be2e1662916a14781a6203073a4605` | Ready, but predates NE-11C2; **NE-11 is not deployed to production** |
| Preview | `dpl_CQzmofcjUwYkr7jJVyMk7TGptwbh` | `042e31f214ffa15a57b865db9f9fc3aa7e295328`, branch `feat/ne11c2-companion-route-handoff` | Ready; Git tree equals merged baseline `2ea868abce02a47bc2fdc403d83f9d083b500cb0` |

Read-only Preview smoke checks returned HTTP 200 for the app, Genesis projection, and Genesis Companion context. The Preview is not production. No deployment, promotion, alias, environment, or Vercel configuration was changed.

`vercel.json` explicitly sets `git.deploymentEnabled.master` to `false`; merging to master does not automatically deploy production. The project-level Narrative Explorer flag is enabled for Preview and Production. Tyndale archive URL and SHA-256 variable names are configured for the deployment environments; values and transport details are intentionally omitted.

## Packaging checks

- The Vercel function configuration includes `framework/canonical_library/**` and `framework/commentary/data/tyndale.sqlite`, while excluding `.bhf-data/**` and `build/**`.
- Targeted tests for Vercel startup, package assembly, CKL index generation/source parity, Tyndale archive provisioning, and Tyndale evidence passed as part of the 691-pass backend suite. The CKL source validation reports 687 objects and the expected inventory fingerprint.
- The target-equivalent Preview successfully served CKL-backed projections. The test suite verifies CKL index/source consistency and Tyndale archive checksum handling without exposing secret values.
- Retired Commentary compatibility tests passed: retired `/api/bhf-commentary` behavior remains HTTP 410. The deployment file rules do not include `.bhf-data` candidate payloads or development build artifacts.
- The remote Preview’s packaged SQLite files were not independently downloaded or inspected. Runtime CKL API smoke and local packaging tests are evidence for packaging, not a claim of direct file inspection.

## Release gate and manual verification

Vercel’s Preview build is ready. Production remains on the older SHA, and the repo baseline presentation/governance/sanitizer failures remain open; see [integrity and regression](03-integrity-and-regression.md). NE-11 feature acceptance is also NO-GO due the missing Jonah source-side handoff. No production promotion is authorized by this task.

After a separately reviewed correction and fresh acceptance, the release operator should:

1. Push the reviewed commit and create a Preview from that exact SHA.
2. Confirm the deployment reports Ready and its Git tree equals the reviewed source.
3. Recheck the Narrative Explorer flag without printing its value; verify CKL and Tyndale package gates in build output and smoke-test Genesis, Jonah, Tyndale notes, and retired Commentary 410 behavior.
4. Confirm frontend assets and backend API correspond to the same commit.
5. Obtain explicit release authorization, then promote/deploy through the approved release process. Do not rely on a master merge to deploy.
