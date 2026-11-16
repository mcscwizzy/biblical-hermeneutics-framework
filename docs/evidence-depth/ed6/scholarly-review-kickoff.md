# Scholarly Review Kickoff

## Purpose

BHF (the Biblical Hermeneutics Framework) is a research workspace intended to
help readers explore biblical passages, historical context, textual evidence,
and attributed interpretations. The Canonical Knowledge Library (CKL) is its
authoritative, governed research source. Individual records carry their own
content and review states, which reviewers must inspect. A reader pilot
evaluates whether people can use the interface; it does not approve CKL
scholarship.

A CKL claim is a stable, passage-linked assertion with source and provenance
metadata. Typed evidence records expose a narrower observation or piece of
support, such as a manuscript reading, lexical observation, or historical
source. They are not independent proof merely because they have a type or
identifier. Reviewers should follow each record to the underlying source and
locator.

Keep direct textual observations distinct from scholarly reconstruction. An
observation may report what a named witness reads or what wording appears in a
specified edition. A reconstruction proposes what may explain the evidence,
such as a historical setting, authorial intention, or earlier wording. BHF
attributes such proposals to scholars and preserves confidence, alternatives,
and dispute status where the evidence warrants them. Manuscript uncertainty
must remain explicit: a reconstruction must not be described as an extant
witness reading unless that witness actually attests it.

## Existing packets and first review wave

ED-5 prepared 12 packets from the existing ED-3 queue. This kickoff does not
duplicate them. The first four requests follow the ED-5 pilot index's P0 order:

1. [2 Chronicles 14 — Cushites and rhetorical setting](../ed3/human-review-packets/wave-c-history/2chronicles-14-cushites-and-rhetorical-setting.md)
2. [Ecclesiastes 10:1 — “flies of death” translation](../ed3/human-review-packets/wave-b-wisdom/ecclesiastes-10-1-flies-of-death-translation.md)
3. [Mark 7:3 — *pugmē/pukna* variant](../ed3/human-review-packets/wave-e-new-testament/mark-7-3-pugme-pukna-variant.md)
4. [Nahum 3:8–9 — one-city text-critical proposal](../ed3/human-review-packets/wave-d-prophets/nahum-3-8-9-one-city-text-critical-proposal.md)

These are priorities for outreach, not completed reviews. The complete 12-item
[ED-5 index](../ed5/reviewer-pilot.md) remains available. Its access notes
identify which articles, manuscripts, images, or artifacts have not been
independently inspected. A qualified reviewer should decline or request more
research when the necessary source is inaccessible.

## What to inspect and report

For the selected packet, ask the reviewer to:

- Read the exact biblical passage in an identified edition and inspect the
  cited scholarly source at its stated locator.
- Inspect any primary manuscript, apparatus, artifact, or historical source
  explicitly called for by the packet, if access permits.
- Check that the CKL wording separates the textual observation from the
  attributed interpretation and does not exceed the source's evidence.
- Identify plausible alternatives, translation or witness limits, chronology
  assumptions, and uncertainty notices that should remain visible.
- Approve as written, approve with specified corrections, request more
  research, hold for insufficient evidence, or reject the claim, with a reason
  and exact inspection scope.

Reviewers decide the scholarly assessment. BHF staff should not prompt a
preferred outcome, fill gaps from memory, or treat agreement with the current
wording as a condition of participation. A reader's doctrinal response is not
scholarly evidence for or against a record.

## Recording and durable history

Use the local ED-4 workbench described in
[ED-4 review workflow](../ed4/review-workflow.md). It reads the existing queue
and packets without changing them and stores human review events in the
Git-ignored `.bhf-data/ed4-human-reviews.jsonl` ledger. Do not record any
decision until an actual reviewer has independently supplied it. The workbench
requires the reviewer to provide their own name, relevant expertise, date,
rationale, source inspections and confirmation of the human action. These are
self-reported details; the tool does not credential-verify reviewers.

For current status and local chain integrity, run
`python tools/ed4_review_workbench.py status`.
For export, use `python tools/ed4_review_workbench.py export --format json`
and, if useful, `--format csv`, redirecting output to a restricted local
destination. For a versioned backup, use
`python tools/ed4_review_workbench.py snapshot --output <restricted-path>`;
verify it with `python tools/ed4_review_workbench.py verify-snapshot <path>`.
Keep the snapshot and its verification result together. The local hash chain
is tamper-evident but is not a digital signature and cannot prove identity or
detect replacement of the entire ledger without an external checkpoint. See
ED-4's workflow for exact handling and retention limits.

## Invitation draft

> I am inviting you to independently review one existing BHF research packet
> related to your area of expertise. The packet identifies a passage, the
> textual observation, an attributed scholarly proposal, source locators, and
> known access limits. We are asking you to inspect the cited evidence you can
> access and tell us whether the wording is supported, needs correction, needs
> more research, should be held, or should be rejected. No particular outcome
> is expected. You may decline or report that access is insufficient. If you
> are interested, I can send the packet and explain the local review workflow.

Personalize only with a real recipient's name and known expertise. Do not claim
an affiliation, qualification, agreement, or review that has not occurred.
