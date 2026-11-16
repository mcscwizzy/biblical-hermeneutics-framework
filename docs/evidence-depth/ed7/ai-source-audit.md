# ED-7 AI-Assisted Source Audit

## Scope and method

The audit used the existing 99-record ED-3 queue, its record-level CKL entries,
inventory, and human-review packets. It did not regenerate research or repeat
the ED-3 literature survey. Every record has stable CKL identity, selected
passage anchor, packet path and SHA-256, materials inspected, access limit,
Pass A rationale, and a distinct Pass B critical challenge in
[`source-verification-results.json`](source-verification-results.json).

Pass A reconciled exact CKL and queue anchors and checked the original-language
or translation claim to the extent recorded in the existing audit. Linkage
checks establish that the record points to the passage; they do not establish
that a cited publication supports the claim. Pass B challenged source scope,
observation versus interpretation, competing readings, chronology, lexical or
manuscript inference, and whether a citation locator was being treated as proof.

Both passes were performed by the same GPT-6 agent in the existing Codex
session. The exact sub-version is not exposed. No independent model invocation
was available or used. Pass B is a second analytical pass by the same agent,
not independent verification. These are machine-audit findings, not human peer
review, approval, or scholarly sign-off.

## Findings

| Outcome | Records |
|---|---:|
| Source checked; specific observation supported with qualifications | 28 |
| Source checked; unqualified support | 0 |
| Source checked; correction required by ED-7 | 0 |
| Source inaccessible or insufficiently verified | 71 |
| Unsupported by available evidence | 0 |

The categories remain distinct: inaccessible is not the same as unsupported.
No record was assigned `human_reviewed` or `human_approved`; all 99 remain
drafts requiring human review. ED-3's previously applied Psalm 17 source-access
note correction is documented in the result file and is not a new ED-7 CKL
change.

## Material directly re-opened

- Nesina Grütter, “A Tale of One City,” *Journal of Septuagint and Cognate
  Studies* 50 (2017), pp. 160–175. The article supports an attributed
  one-city reconstruction and records a disputed reading. No 4Q385a image or
  critical edition was inspected.
- Jean-Daniel Macchi, « De Yhwh la réponse de la langue », *Études Théologiques
  et Religieuses* 99, no. 2 (2024), pp. 381–394, especially pp. 382–383. The
  article reports Hebrew/Greek differences and attributes the proposed
  editorial relationship; alternatives remain. No fragment image or critical
  edition was inspected.
- Stanisław Bazyliński, “Annotazioni sul testo del Salmo 17,” *The Biblical
  Annals* 11, no. 3 (2021), pp. 398–402 and 406–407. The article presents a
  conjectural proposal at v. 11 and favors the *qere* at v. 14 while reporting
  that the question is unsettled. No apparatus volume or manuscript image was
  inspected.

The ED-3 packets and records also note a small number of accessible abstracts,
publisher excerpts, translations, or edition text checks. The audit states
their exact scope per row. For 69 of the records no cited source text was newly
inspected. No manuscript image, artifact, inscription, or primary critical
apparatus was examined. No claim is made of universal access to cited works.

## Objections retained

The record-level audit keeps unresolved objections verbatim where source text
or a primary witness was unavailable. Among them: whether a secondary author's
full reasoning was represented, whether a chronology is independently
established, whether a lexical range is too broad, whether a variant is
supported by an apparatus, and whether alternatives are fairly represented.
No absence of contrary evidence was converted into confirmation.
