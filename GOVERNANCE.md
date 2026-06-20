# Governance & Neutrality Charter

This document defines how the Biblical Hermeneutics Framework (BHF) is governed
and — most importantly — the **neutrality charter** that protects the project's
mission from doctrinal drift. The neutrality charter is the project's
constitution: when in doubt, it wins.

## 1. Neutrality Charter (the constitution)

BHF teaches AI models **how** to interpret Scripture, never **what** to
conclude. Every maintainer, contributor, and module is bound by these
principles:

1. **No doctrinal verdicts.** Modules describe interpretive *methods* and the
   *range* of responsible scholarly views. They never declare which view is
   correct, nor endorse a denomination, confession, or theological system.
2. **Represent the spread fairly.** Where scholarship is genuinely divided, a
   module presents the major positions in proportion to their support, labeled
   (consensus / majority / minority / speculative) per
   [`core.epistemic-humility`](framework/core/05-epistemic-humility.md).
3. **Method over conclusion.** Tests and rubrics evaluate whether a model
   *reasoned well* (identified genre, separated observation from application,
   admitted uncertainty), never whether it reached a particular answer.
4. **Source or soften.** Factual claims about history, language, or scholarship
   are sourced, or explicitly framed as uncertain. No invented authorities.
5. **Respect the reader's agency.** The goal is to help people ask better
   questions, not to hand them conclusions. See
   [`docs/philosophy.md`](docs/philosophy.md).

Changes to this charter require unanimous maintainer agreement and a MAJOR
version bump.

## 2. Roles

- **Contributors** — anyone who opens an issue or PR. No prior permission needed.
- **Reviewers** — trusted community members who can approve PRs in a domain
  (e.g., Greek language, Second Temple history).
- **Maintainers** — hold merge rights, steward the roadmap, and are accountable
  for the neutrality charter. Maintainers are added by consensus of existing
  maintainers based on sustained, high-quality contribution.

## 3. Review process

| Change type | Required approvals |
|-------------|--------------------|
| Typo / formatting / link fix | 1 maintainer or reviewer |
| Module correction (with source) | 1 maintainer |
| New module / substantive content change | **2 maintainers**, one of which performs an explicit **neutrality + sourcing review** |
| Changes to `docs/module-spec.md`, this charter, or `tools/` behavior | 2 maintainers + CHANGELOG entry; spec changes are versioned |

The **neutrality + sourcing review** explicitly answers: *Does this module tell
the reader what to believe? Are factual claims sourced or softened? Are
divided questions represented fairly?* If any answer is unsatisfactory, the PR
is revised before merge.

## 4. Decision-making

Routine decisions are made by lazy consensus on issues/PRs (silence = assent
after a reasonable review window). Contested decisions are resolved by a simple
majority of maintainers, except changes to the Neutrality Charter (Section 1),
which require unanimity.

## 5. Releases

Maintainers cut releases as git tags following the versioning policy in
[`docs/architecture.md`](docs/architecture.md#versioning) and record them in
[`CHANGELOG.md`](CHANGELOG.md).
