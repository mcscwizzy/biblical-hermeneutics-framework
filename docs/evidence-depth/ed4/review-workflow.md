# ED-4 Human Review Workbench

## What it does

The repository-maintainer CLI makes the 99 ED-3 review records searchable and
opens each existing packet with its exact passage, observation, interpretation,
source IDs, bibliography locators, access limits, qualifications, and reviewer
questions. It reads the ED-3 queue and packets without changing either file.

The workbench stores real reviewer actions in
`.bhf-data/ed4-human-reviews.jsonl`, which is ignored by Git. It does not expose
a network endpoint, alter CKL governance fields, edit the queue or packets, or
turn machine validation into an approval.

## Find and inspect a record

From the repository root:

```bash
python tools/ed4_review_workbench.py list
python tools/ed4_review_workbench.py list --book 2-chronicles --priority P0
python tools/ed4_review_workbench.py list --evidence-type manuscript
python tools/ed4_review_workbench.py list --source-access "No new independent source text inspected"
python tools/ed4_review_workbench.py list --source-outcome "Unable to independently verify"
python tools/ed4_review_workbench.py list --query "apparatus"
python tools/ed4_review_workbench.py show acts-15-29-eu-prassete-range
python tools/ed4_review_workbench.py progress
```

`list` shows the stable evidence ID, book, passage, priority, evidence type,
ED-3 machine outcome and source-access classification, a separate local human
review status, and packet path. Use `--limit` and `--offset` to page through
matches. `show` prints the linked
packet verbatim, including source locators and questions for the reviewer,
followed by any attributed events already recorded for that ID.

The recommended priority field retains ED-3's P0/P1/P2 values. `--source-access`
filters the specific inspection/access description; `--source-outcome` filters
the distinct ED-3 machine outcome. The 71 items marked unable to independently
verify describe an access/verification limit, not proof that a claim is false.

## Record a human decision

The five allowed choices are `approve_as_written`,
`approve_with_corrections`, `request_more_research`,
`hold_insufficient_evidence`, and `reject_claim`. The reviewer must supply their
own name, relevant expertise, today's review date, a rationale, the source or
text actually inspected and its locator/access scope, and the explicit
`--confirm-human-action` flag. The CLI rejects an absent identity, rationale,
inspection, confirmation, invalid decision, or a backdated review date.

Example shape (the qualified reviewer supplies every value):

```bash
python tools/ed4_review_workbench.py decision <evidence-id> \
  --decision request_more_research \
  --reviewer "Reviewer name" \
  --expertise "Relevant field and qualification" \
  --review-date "$(date +%F)" \
  --rationale "Describe the inference and remaining research question." \
  --inspection 'source-id|pp. 22-24|full article' \
  --inspection 'greek-edition|1 John 3:19-24|text inspected; apparatus not checked' \
  --confirm-human-action
```

For `approve_with_corrections`, also supply
`--required-corrections-or-follow-up`. Each decision is appended as an event;
later decisions do not overwrite earlier ones. A local decision is a review
record only. CKL approval still requires the repository's separate governed
research and validation process.

## Corrections

Record a request and its evidence inspection:

```bash
python tools/ed4_review_workbench.py correction-request <evidence-id> \
  --requested-change "State the manuscript scope and limit the wording." \
  --rationale "The current claim generalizes beyond the cited witness." \
  --reviewer "Reviewer name" --expertise "Text criticism" \
  --review-date "$(date +%F)" \
  --inspection 'edition-id|apparatus at the cited verse|edition and apparatus inspected' \
  --confirm-human-action
```

After a human applies a change through the ordinary CKL governance process, a
reviewer can record separate verification. The command requires the correction
request event ID, the CKL path/field or commit containing the change, the exact
corrected wording, a verification rationale, and the text/source inspected:

```bash
python tools/ed4_review_workbench.py verify-correction <evidence-id> \
  --correction-event-id <event-id> \
  --change-reference 'framework/canonical_library/objects/books/example.json#claims[0]' \
  --corrected-text "The exact corrected wording inspected." \
  --rationale "Explain how the corrected wording resolves the request." \
  --reviewer "Reviewer name" --expertise "Relevant field" \
  --review-date "$(date +%F)" \
  --inspection 'source-id|specific locator|full text checked' \
  --confirm-human-action
```

Verification appends a new event and leaves the request intact. It does not
apply the correction, validate CKL, or record a separate scholarly decision.

## History and export

```bash
python tools/ed4_review_workbench.py progress
python tools/ed4_review_workbench.py export --format json > ed4-review-history.json
python tools/ed4_review_workbench.py export --format csv > ed4-review-decisions.csv
```

JSON includes all events, a summary, latest decisions by evidence ID, reviewer
attribution, source inspection scope, and event hashes. CSV includes actual
latest human decisions. Both exports are deterministic for a fixed ledger. A
SHA-256 chain detects edits or reordering, including removal of an interior
event, when history is read. A local hash chain cannot detect deletion of only
the final events or replacement of the whole file without an external
checkpoint; it is tamper-evident, not a digital signature or identity provider.

The ledger captures the supplied review date and separately records the real
UTC time the CLI appended the event. It rejects backdated review dates. The
CLI is a local maintainer tool: reviewer names and expertise are self-reported,
not credential-verified. Repository access control remains responsible for
protecting the local ledger. No public approval interface or authentication
service is introduced.

## Current state

The ED-3 queue and all 99 packet identities remain unchanged. At ED-4 delivery,
the default ledger is absent, progress reports 99 pending records and zero
human decisions, and no reviewer approval is recorded. Tests exercise decision
and correction events only in temporary directories.
