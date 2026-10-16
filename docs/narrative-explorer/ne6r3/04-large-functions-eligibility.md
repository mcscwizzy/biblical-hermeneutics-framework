# NE-6R3 — Vercel Large Functions Eligibility

Audit date: 2026-10-16  
Project: `biblical-hermeneutics-framework` (`mcscwizzys-projects`)  
Failed deployment: `dpl_4qr1e4Wa2g2QoMGFf5HSqNYPQNe6`

## Documented capability

Vercel's June 29, 2026 Large Functions announcement describes Python and
Node.js functions up to 5 GB when using Fluid Compute. Existing projects opt
in with `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`; the setting can be scoped to
Preview. The feature is a public beta. Vercel documents Fluid Compute and
Active CPU as requirements, and excludes projects using Secure Compute or
Static IPs. Large Functions are therefore a possible fit for this Python
FastAPI app, not a guaranteed fit for this account until the project-level
conditions are confirmed.

Sources: [Large Functions announcement](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistvS/eadf06d6c3), [function-size troubleshooting](https://vercel.com/kb/guide/troubleshooting-function-250mb-limit), [Python runtime](https://vercel.com/docs/functions/runtimes/python).

## Project evidence available without changing settings

| Requirement or state | Finding | Confidence |
|---|---|---|
| Python function compatibility | Failed deployment built Python 3.12; project uses FastAPI and `vercel.json` configures the app entry point | Confirmed |
| Fluid Compute | `vercel.json` sets `fluid: true` | Configured in source; project dashboard state not independently exposed |
| Static IP exclusion | Read-only project listing returned this project when filtering for Static IP disabled | Static IP is off |
| Secure Compute exclusion | Not exposed by available read-only project API | Unknown |
| Active CPU requirement | Not exposed by available read-only project API | Unknown |
| Account/team plan eligibility | Plan details not exposed by the available read-only tools | Unknown |
| Project age/automatic enrollment | Project metadata creation date is after the announcement's June 30, 2026 cutoff described for automatic enrollment | Suggests it may be included, but not proof of account/project eligibility |
| Existing opt-in setting | `VERCEL_SUPPORT_LARGE_FUNCTIONS` is absent from the project's environment-variable key list | Not enabled in the queried project env scopes |
| Current enforced limit | Failed build explicitly enforced 225 MB and stopped at 317.82 MB | Large Functions was not in effect for this deployment |
| Preview-only scope | Vercel documents Preview-scoped opt-in | Supported by platform documentation; not configured |

The project API reports a `container` framework classification while the
committed `vercel.json` and failed build identify a Python FastAPI Lambda.
The successful Python build is the best evidence for runtime compatibility;
the framework metadata mismatch should be checked in Vercel before the next
hosted run.

## Expected effect and operational implications

The measured 317.82 MB post-optimization bundle is below the documented 5 GB
Large Functions ceiling. A successful Preview build would establish whether
the project actually accepts the configuration and payload; it must not be
represented as successful until Vercel reports a completed deployment and
runtime retrieval checks pass.

The setting is opt-in at build time and would affect Preview only if assigned
to the Preview environment scope. It changes function packaging/compute
eligibility, not CKL data or application behavior by itself. Fluid Compute
has plan-dependent usage and billing implications, including active CPU and
memory usage. Exact rates and plan exposure are not knowable from the supplied
read-only project metadata. A larger package may also increase artifact
transfer and cold-start work; the size alone does not predict startup latency.

The user requested no billing changes or project-setting changes in this
audit. No opt-in variable was added, and no deployment was run.

## Eligibility conclusion

**Conditional candidate; not fully verified.** Python 3.12/FastAPI is
compatible according to Vercel's published runtime support, Fluid Compute is
declared in source, Static IP is off, and the bundle is within the advertised
package ceiling. Secure Compute state, Active CPU, team plan eligibility,
dashboard Fluid Compute state, and the framework metadata mismatch remain to
be checked. The prior 225 MB failure proves Large Functions is not currently
active for that deployment.

If those prerequisites check out, the least disruptive hosted validation is
one Preview-only build with `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` and
`VERCEL_ANALYZE_BUILD_OUTPUT=1`, followed by read-only CKL and reader checks.
Neither variable should be set until the user separately authorizes that
Preview action. Keep Production scope unchanged.
