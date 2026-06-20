# Contributing to BHF

Thank you for helping build a responsible, denomination-neutral hermeneutics
framework. There are 66 books and many historical, literary, and language
topics to cover — contributions are very welcome.

Before anything else, read the **[Neutrality Charter](GOVERNANCE.md#1-neutrality-charter-the-constitution)**.
It is the one rule everything else serves: *BHF teaches method, never doctrine.*

## Ways to contribute

- **Add a module** (a genre, book, context, or language module).
- **Correct a factual error** in an existing module (open a *Module correction*
  issue and include a source).
- **Improve docs, examples, or rubrics.**
- **Improve the tooling** (`tools/`).

## Adding or editing a module

1. **Pick the category** and copy its template:
   - Genre → [`framework/genres/_TEMPLATE.md`](framework/genres/_TEMPLATE.md)
   - Book → [`framework/books/_TEMPLATE.md`](framework/books/_TEMPLATE.md)
   - Context → [`framework/context/_TEMPLATE.md`](framework/context/_TEMPLATE.md)
   - Language → [`framework/language/_TEMPLATE.md`](framework/language/_TEMPLATE.md)
2. **Name the file** in kebab-case (e.g., `honor-shame.md`) and set the module
   `id` as `<type>.<slug>` (e.g., `context.honor-shame`). See the
   [module spec](docs/module-spec.md).
3. **Fill every required section.** Follow the [style guide](docs/style-guide.md)
   (American English, plain language, second-person instructions to the AI).
4. **Declare dependencies** (`requires` / `recommends`) and an approximate
   `tokens` count.
5. **Validate locally** (use a virtualenv if `pip` reports a PEP 668
   "externally-managed-environment" error — see
   [`tools/README.md`](tools/README.md)):
   ```bash
   pip install -r tools/requirements.txt
   python tools/validate.py framework/
   ```
6. **Open a pull request** using the PR template.

## PR checklist

Your PR description must confirm:

- [ ] `python tools/validate.py framework/` passes.
- [ ] Frontmatter is complete and the `id` matches `<type>.<slug>`.
- [ ] All required body sections are present.
- [ ] Factual claims (history, language, scholarship) are **sourced** or
      **explicitly framed as uncertain** — no invented authorities.
- [ ] Divided questions present the major views fairly and labeled
      (consensus / majority / minority / speculative).
- [ ] **Neutrality self-check:** *Does this module tell the reader what to
      believe?* If yes, rewrite it as method.
- [ ] `requires` / `recommends` reference real module IDs; cross-references
      (`[[id]]`) resolve.

## Review

New modules require **2 maintainer approvals**, one being an explicit
neutrality + sourcing review (see [GOVERNANCE.md](GOVERNANCE.md#3-review-process)).
Be patient and responsive to review feedback — the bar is high on purpose.

## Tone

Disagreements about *method* are healthy. This is not a venue for advancing or
attacking any tradition's doctrine. See the [Code of Conduct](CODE_OF_CONDUCT.md).
