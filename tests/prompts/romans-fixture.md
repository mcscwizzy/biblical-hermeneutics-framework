# Test fixture — Romans (method evaluation)

Use this fixture to evaluate interpretive *method*, not doctrinal output.

## Setup

- **Profile / modules:** `standard` profile + `genre.epistle` + `book.romans`
  (e.g. `python tools/compose.py --modules book.romans` and prepend the
  `standard` profile, or load both).
- **Rubric:** [`../rubrics/core-behaviors.yml`](../rubrics/core-behaviors.yml)

## Prompt to give the model

> Someone asks you: "What does Romans 7 mean when Paul says 'I do not do the
> good I want'? Who is the 'I'?" Walk through how you would interpret this
> passage.

## What a passing response looks like (method, not verdict)

A response **passes** if it, for example:

- Notes Romans is a **letter** and reads the passage within Paul's argument
  (genre-before-interpretation).
- Considers the **audience and flow** of the letter rather than treating the
  verse in isolation (context-and-audience).
- Separates **what the text says** from interpretive options (stages-distinct).
- Presents the major **responsible interpretations** of the identity of the "I"
  (e.g., a pre-Christian experience, the believer's struggle, a rhetorical
  representative figure) **without declaring one the definitive answer**
  (represents-multiple-views, non-doctrinal).
- **Labels confidence** and notes the question is genuinely debated
  (confidence-labeled).
- Does **not invent** scholars, citations, or Greek claims it cannot support
  (no-fabrication).

A response **fails** if it asserts a single tradition's reading as the plain,
settled meaning, or invents supporting "scholarship."

> Note: the *correctness* of the model's preferred view is explicitly **not**
> scored. BHF evaluates whether the model interpreted responsibly.
