# Style Guide

Consistency makes modules easier for both humans and AI models to use. Follow
these conventions when writing or editing content.

## Voice and audience

- **Address the AI in the second person, as instructions:** "Identify the genre
  before interpreting," not "The interpreter should identify the genre."
- **Be directive and concrete.** Each interpretive move should be an action.
- **American English**, plain language. Prefer short sentences. Avoid jargon; when
  a technical term is necessary, it should appear in [`glossary.md`](glossary.md).

## Neutrality (non-negotiable)

- Describe **method and the range of views**, never a doctrinal verdict.
- Do not use a tradition's in-house framing as if it were neutral. When a view is
  contested, attribute it and label its support
  (see [`../framework/core/03-epistemic-humility.md`](../framework/core/03-epistemic-humility.md)).
- Avoid first-person plural that implies a shared creed ("we believe…").

## Sourcing

- Any factual claim about history, language, dating, authorship, or scholarship
  must be **sourceable** or **explicitly framed as uncertain**.
- Never invent a scholar, citation, date, statistic, or manuscript detail
  (see [`../framework/core/04-anti-hallucination.md`](../framework/core/04-anti-hallucination.md)).

## Structure

- Use the exact required section headings from [`module-spec.md`](module-spec.md),
  in order.
- Keep modules **focused and small** — one job per module. Token budgets matter;
  split rather than bloat.
- Cross-reference related modules with `[[id]]` (must resolve).

## Formatting

- Filenames: kebab-case (`honor-shame.md`); `core/` files use a numeric prefix to
  enforce read order.
- Module `id`: `<type>.<slug>`, matching the file's folder.
- Use Markdown lists for interpretive moves; keep code/quote blocks rare and
  purposeful.
- Update the `tokens` value when you change a module (the validator reports the
  acceptable range).

## Scripture references

- Refer to passages generically (book, chapter, verse). **Do not paste long
  copyrighted translation text**; quote minimally and only when necessary, and
  prefer describing the text over reproducing it.
