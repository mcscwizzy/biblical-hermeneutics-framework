# Feedback Analysis Method

## Intake and separation

Analyze only authentic, de-identified local records. Synthetic fixtures are
for regression tests and must never be imported into the participant store or
reported as findings. Preserve the source notes privately; the CLI report
contains aggregate counts and denominators but intentionally excludes raw
observations and participant codes.

First check record validity and input-quality counts. Keep incomplete and
stopped sessions. When an assigned task has no observation, let the aggregate
report count it as `not_observed`; use an explicit `not_attempted` task entry
only when the facilitator observed that status. Report
the denominator for every quantity: assigned sessions for completion,
observed responses for verification distributions, numeric durations for time
summaries, and observed task sessions for note-entry counts. Missing data is
not zero and is not an implied failure.

For qualitative review, read de-identified notes task by task. Group similar
observations only after recording the direct behavior; maintain a separate
facilitator interpretation. Preserve disconfirming examples. Use quotations
only when separate quote consent is true, and avoid sensitive personal
disclosures even when consent exists. Do not calculate a single overall
“reader success” score.

## Transparent improvement priority

Use this 0–3 scale for each factor. Record the evidence behind the score and
do not conceal a high-risk concern inside an average:

| Factor | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Independent participants affected | one | two | three or four | five or more |
| Task-blocking severity | preference only | friction, task completed | task partially blocked | task impossible or materially misleading |
| Reproducibility | not reproduced | one clear observation | repeated in similar conditions | independently reproduced in a focused check |
| Evidence transparency importance | cosmetic | minor source-finding friction | uncertainty or attribution hard to find | claim/source relation or review state can be mistaken |
| Accessibility impact | none observed | added effort | substantial barrier for a user group | prevents access to a core task |
| Risk of misleading scholarship if changed | negligible | limited wording risk | could obscure an uncertainty | likely to misstate or erase evidence/uncertainty |
| Engineering complexity | small isolated change | bounded component change | cross-component or data migration | broad architectural or governance change |

Use the dimensions as a decision aid, not as an automatic rank. Integrity and
accessibility concerns receive explicit review even when one person reports
them. Before an implementation, document the observation, participants
affected (`n / N`), task and condition, reproducibility check, proposed change,
scholarly integrity risk, complexity, and a way to verify the result.

## Issue classes and action

- **Critical research integrity:** factual attribution, source linkage, review
  state, provenance, or uncertainty appears misleading. Verify against the
  actual record and source; pause reliance on the affected display and route
  scholarly questions to qualified review. Do not patch research conclusions
  from usability notes.
- **Accessibility barrier:** a user cannot operate or perceive a core task.
  Reproduce with the relevant assistive or viewport condition and prioritize
  an accessible fix.
- **Navigation problem:** a reproducible control, route, or return path blocks
  task continuity. Confirm with a focused browser check.
- **Unclear terminology:** participants interpret a label differently or
  cannot explain it. Consider a small wording change and verify it does not
  collapse distinct research categories.
- **Overwhelming evidence presentation:** users cannot identify claim/source
  relationships in the available display. Consider progressive disclosure
  while retaining access to full provenance and uncertainty.
- **Subjective preference:** one person's preferred color, layout, or feature
  is not treated as a general problem without corroborating impact.
- **Outside current mission:** record respectfully, but defer features that do
  not support contextual research, evidence inspection, or reader usability.

Implement a change only when its evidence, impact, and integrity risks are
reviewed. A single participant can surface a serious access or misleading
display defect, but the defect still needs independent reproduction. Do not
generate scholarly evidence to help someone finish a task. If the sample is
empty, retain this as a future analysis method and make no feedback-driven
change.
