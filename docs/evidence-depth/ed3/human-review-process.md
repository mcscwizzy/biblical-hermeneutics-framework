# Human scholarly review process

## Purpose and status

This process applies to ED-3 and later research waves. It prepares traceable
review packets; it does not confer approval. ED-3 assessments are machine-assisted
research notes. A qualified human reviewer must independently examine the claim,
its source locators, relevant textual evidence, and material alternatives. Every
ED-2 addition remains draft / in review, human review required, and unapproved.

## Review sequence

1. Open the queue row and linked packet. Confirm the stable evidence ID, passage
   anchor, current CKL wording, and ED-2 source packet.
2. Inspect the cited publication at the exact locator. Record whether the full
   argument, a relevant excerpt, an abstract, or metadata was examined. Do not
   infer access from an earlier audit note.
3. Check the Scripture observation against an appropriate text or edition. For
   textual claims, identify the edition and witnesses inspected; distinguish an
   attested variant from conjecture and from a claim about the original reading.
4. Evaluate the inference separately from the observation. Check significant
   alternatives, attribution, chronology (narrated event, proposed occasion,
   composition, manuscript, and later reception), confidence, and reader-facing
   scope.
5. Enter the reviewer identity, relevant expertise, date, decision, and rationale
   in the packet and queue. Cite the evidence actually consulted and specify
   corrections or follow-up. Do not backdate or attribute another person's work.
6. If wording or CKL data changes, preserve provenance and status conventions,
   obtain a second qualified review when required by local governance, then run
   applicable CKL and application checks. Keep the review decision separate from
   technical validation.

## Decisions

Use exactly one decision after review:

- **Approve as written** — the wording, sourcing, qualification, and scope are
  defensible at the inspected level.
- **Approve with corrections** — the reviewer records and verifies precise
  changes before approval is recorded in the governed CKL workflow.
- **Request more research** — name the missing publication, witness, context, or
  comparison and the question it must resolve.
- **Hold due to insufficient evidence** — the claim should not be published in
  its current evidentiary state.
- **Reject the claim** — the claim is contradicted, materially misattributed, or
  otherwise not supportable after review; document the basis and follow governance
  for removal or archival.

A blank decision means no human decision has been recorded. Draft/in-review,
source-access limitations, or a machine-assessed outcome must never be converted
into human approval. A reviewer may leave a decision blank while requesting
consultation; record that request in rationale/follow-up without implying approval.

## Reuse for future waves

For every new research wave, generate one queue row and one packet per stable
CKL evidence ID from the approved inventory fields. Include the exact anchor,
observation, interpretation, confidence/dispute status, source IDs and locators,
independent inspection scope, access limits, chronology, alternatives, priority,
review questions, and blank reviewer fields. Validate row-to-packet coverage,
unique IDs, empty decision fields, and allowed decision vocabulary before routing
the queue. Keep packets grouped by book or research wave and maintain a searchable
index. Do not copy copyrighted articles into packets; cite the publication and
locator instead.

## Queue contents

The machine-readable queue is `human-review-queue.csv`; packet indexes and
individual reviewer packets are under `human-review-packets/`. All reviewer
identity, date, decision, rationale, and correction fields are currently blank.
