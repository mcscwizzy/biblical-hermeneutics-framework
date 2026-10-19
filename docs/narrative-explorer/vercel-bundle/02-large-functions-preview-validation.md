# Large Functions Preview Validation

- Audit date: 2026-10-18
- Project: `biblical-hermeneutics-framework`
- Investigation branch: `investigation/vercel-lambda-size-2026-10-17`
- Baseline commit: `551a998f5c40d6cb4d5e8a1f41db1bfe8f307096`
- Result: eligibility is not fully confirmed; no environment variables were changed and no new deployment was created.

## Executive finding

The August 21, 2026 Vercel project is newer than Vercel's June 30, 2026 Large Functions automatic-enrollment date. Its checked-in configuration enables Fluid Compute, its failed deployment used Python 3.12, and Vercel's project listing reports Static IPs disabled. Those facts make the project appear compatible with the published Large Functions requirements.

The prior NE7R3 build nevertheless took the standard bundle-size path: Vercel logged 340.46 MB before dependency optimization and 308.39 MB afterward, then failed with `LAMBDA_SIZE_EXCEEDED` against 225 MB. This is direct evidence that Large Functions was not applied to that deployment. It does not establish why. The account interfaces available here do not expose the Active CPU activation state, Secure Compute attachment state, or the project's beta enrollment flag. The Vercel project metadata also says `framework: container`, while the checked-in configuration says `fastapi` and the build log identifies Python 3.12.

Because the remaining eligibility gates are not observable, the authorized Preview deployment condition was not met. No Preview-only variables were added. A Vercel support request is justified to reconcile the project enrollment and the 225 MB build result before retrying. CKL externalization is not implemented or recommended yet; 308.39 MB is within the published 5 GB Large Functions ceiling if Vercel confirms the project can use it.

## 1. Eligibility review

| Requirement or restriction | Finding | Evidence and limits |
|---|---|---|
| Fluid Compute | Enabled in repository config; deployment-level confirmation is unavailable | `vercel.json` has `"fluid": true`. Vercel documents this field as enabling Fluid Compute. The failed build did not reach function startup. |
| Active CPU | Partially supported; activation state unverified | The Vercel team context reports the Hobby plan. Vercel documents Active CPU usage on Hobby, but the project/account interface exposed here does not return an Active CPU activation toggle or its current remaining allowance. |
| Large Functions beta enrollment | Not applied to the failed deployment; current enrollment flag unverified | Project creation timestamp is 2026-08-21, after the published automatic-enrollment cutoff. The project environment list has neither `VERCEL_SUPPORT_LARGE_FUNCTIONS` nor an explicit `=0` override. The failed build says it exceeded the *standard* size and ended with `LAMBDA_SIZE_EXCEEDED`; the feature-flag endpoint returned no flags and no enrollment status. |
| Secure Compute | Unverified | The project and team responses do not expose Secure Compute attachments, and no Secure Compute network listing capability was available in the connected account tools. |
| Static IPs | Disabled | Vercel's project listing filtered by `staticIpsEnabled=1` returned no project; filtering by `staticIpsEnabled=0` returned this project. |
| Account plan | Hobby | Vercel's Git deployment context reports `plan: hobby`. The available plan and project responses do not say whether the Large Functions enrollment was granted or suppressed for this team. |
| Runtime support | Supported by the published runtime list | Source configuration uses FastAPI/Python (`framework: fastapi`, `[tool.vercel] entrypoint = "bhf_web.app:app"`). The prior deployment log says `Using Python 3.12 from pyproject.toml`. Vercel lists Python as a Large Functions runtime. |
| Project framework metadata | Inconsistent; effect unverified | Vercel project/deployment metadata reports `framework: container`; the repo config and build log identify FastAPI/Python. No evidence shows this label itself caused the size gate. |
| Master deployment protection | Preserved | `vercel.json` still has `git.deploymentEnabled.master = false`. No Vercel project setting was changed. |

### Why the newer project still received 225 MB

Project age alone does not establish eligibility. The official docs also require Fluid Compute with Active CPU and exclude projects using Secure Compute or Static IPs. Static IPs are ruled out here, while Active CPU and Secure Compute remain unverified.

The specific build failure occurred because Vercel applied its standard function-size check rather than the Large Functions path. The project date is not an explanation for this behavior: the published docs say projects created after June 30, 2026 are enrolled automatically. The missing project enrollment state, hidden eligibility settings, and `container`/FastAPI metadata mismatch prevent a supported conclusion about which gate stopped the beta from applying.

There is also a limit discrepancy to resolve with Vercel: the current Functions documentation lists a 500 MB standard uncompressed limit for Python and up to 5 GB for eligible Large Functions, while this deployment was explicitly capped at 225 MB. The actual deployment error is authoritative for that build; the API and logs do not explain the lower cap.

## 2. Resource and billing review

The connected account reports the Hobby plan. Vercel's published Hobby plan includes 4 Active CPU hours, 360 GB-hours of provisioned memory, and 1 million function invocations; Hobby does not charge overages and may pause service when limits are exceeded. The available account API did not expose current remaining quota, so the remaining allowance cannot be estimated.

The documented Large Functions setting changes bundle-size handling. No memory, CPU size, duration, region, billing plan, or production configuration would be changed for the proposed test. The Preview build and representative request tests would consume the team's existing build and function usage. On Hobby, expected incremental billing is $0 while the test stays within included allowances; the operational limit is quota exhaustion and service pause, not usage overage billing. Current remaining allowance was not exposed, so exact quota headroom is unknown. The official pricing docs describe charges in terms of Active CPU, provisioned memory, and invocations; they do not identify package size itself as a usage meter. A larger package may still increase initialization work and cold-start risk, which would need measurement on a working Preview.

No deployment was started because Vercel's hidden eligibility state prevents confirming the preconditions. No paid upgrade was requested or made. No application code, CKL records, source inventory, fingerprint, database, canonical evidence, or authoring-pipeline state was modified.

## 3. Environment changes and Preview deployment

| Item | Result |
|---|---|
| `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` | Not added |
| `VERCEL_ANALYZE_BUILD_OUTPUT=1` | Not added |
| Environment scope | No changes; production and Preview settings remain as found |
| Preview deployment | Not created; no deployment ID or URL |
| Production | Not deployed or modified |
| Project domains/aliases | Read only; no changes |

The existing failed deployment was `dpl_7FfDEarUciyFzfa2vvGubSmYnk4f`, from commit `483611ceef4a44fb34b4e2d8c62d737fd4cf192f` on `refactor/narrative-explorer-ne7r3-commentary-retirement`. Its failed URL was `https://biblical-hermeneutics-framework-ow92me7t1-mcscwizzys-projects.vercel.app`; it did not become a working Preview.

## 4. Build evidence and analyzer availability

The prior Vercel build log was retrieved read-only and preserved here:

```text
Using Python 3.12 from pyproject.toml
Force-bundling 2 package(s) without compatible wheels: cffi, cffi
Bundle size (340.46 MB) exceeds the standard size; optimizing dependencies.
Error: [LAMBDA_SIZE_EXCEEDED] Total bundle size (308.39 MB) exceeds the maximum function size (225 MB) even after optimizing dependencies.
```

The previous deployment did not have `VERCEL_ANALYZE_BUILD_OUTPUT=1`, so it produced no dependency-by-dependency analyzer report. The earlier inventory report records the build-generated CKL database at 116,334,592 bytes and other known assets, but it does not attribute the full optimized bundle. No analyzer output was created during this audit.

## 5. Application validation results

No Preview was available, so no runtime or browser acceptance checks were run. The previous Vercel build's CKL build hook reported 687 objects, 2,329 claims, 5,232 sources, and 1,297 evidence rows. Those are baseline build results, not a new Preview integrity validation.

| Requested validation | Result |
|---|---|
| CKL source/manifest integrity and object/claim/source/evidence counts | Not revalidated on a new deployment |
| Narrative Explorer | Not tested |
| Genesis chapter evidence, including Genesis 2:8 | Not tested |
| Maps and geography | Not tested |
| Compare Translations | Not tested |
| Tyndale Study Notes | Not tested |
| Notes and Highlights | Not tested |
| Offline/service-worker compatibility | Not tested |
| Retired Commentary/coverage endpoints returning 410 | Not tested |
| Function startup, runtime errors, memory use, and representative response times | Not measurable; there was no ready deployment |

No workflow is represented as passing based on this audit. The prior acceptance baseline is in [01-post-merge-bundle-investigation.md](01-post-merge-bundle-investigation.md).

## 6. Support request and CKL externalization assessment

A Vercel support request is warranted because the project is newer than the documented auto-enrollment date, has Fluid Compute enabled in source config, uses a supported Python runtime, and has Static IPs disabled, yet the build took the standard 225 MB path. Ask Vercel to confirm:

1. Whether Large Functions enrollment is active for project `prj_15SaSVJykrPDrncFg6jehwGzr3j9` and team `team_OIjeUT7LxEQvrDBdYmV8ysVP`.
2. Whether Active CPU is enabled for this project and whether the Hobby plan is eligible for this beta on the project's current deployment path.
3. Whether the project is attached to Secure Compute or subject to any other beta restriction.
4. Why this Python 3.12 build was capped at 225 MB rather than using the published Python standard limit or the Large Functions path.
5. Whether `framework: container` in project metadata conflicts with `framework: fastapi` in the repository's `vercel.json` for enrollment or bundle handling.

Do not send or change any account settings to resolve these questions without a confirmed answer. If Vercel confirms eligibility and no exclusion applies, the next authorized test can set both documented variables to `1` for the `investigation/vercel-lambda-size-2026-10-17` Preview branch only, then create one Preview deployment and run the acceptance checks. Do not add either variable to Production or re-enable master deployments.

If Vercel confirms the project cannot use Large Functions, or a Preview with the two Preview-only variables still fails the 225 MB gate, then reassess the immutable external CKL SQLite option separately. Do not change CKL records, source inventories, fingerprints, databases, canonical evidence, provider verification, or fail-closed behavior as part of that assessment.

## 7. Recommendation

The full 308.39 MB BHF reader and Narrative Explorer are below the published 5 GB Large Functions ceiling. Current evidence is not enough to conclude that this Vercel team/project can use that path, and no Preview runtime validation has been performed. Do not recommend Production readiness or CKL externalization yet.

After Vercel resolves the eligibility discrepancy, the minimum controlled path is one branch-scoped Preview with the analyzer enabled, followed by the CKL integrity, reader, offline, and retirement checks listed above. Only a successful measured Preview can support a later production-readiness recommendation. No Production deployment or merge is authorized by this report.

## References

- [Vercel Large Functions changelog](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistv/eadf06d6c3)
- [Vercel function-size troubleshooting](https://vercel.com/kb/guide/troubleshooting-function-250mb-limit)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)
- [Vercel Fluid Compute pricing](https://vercel.com/docs/functions/usage-and-pricing)
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Earlier post-merge bundle investigation](01-post-merge-bundle-investigation.md)
