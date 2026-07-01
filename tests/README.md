# Testing in BHF

BHF has two tiers of testing. The guiding rule: **we test method, never
doctrine.** A test never checks whether the model reached a particular
theological conclusion — only whether it interpreted *responsibly*. This keeps
the test suite denomination-neutral and works on any model.

## Tier A — Structural validation (automated, CI)

`tools/validate.py` checks every module against
[`../docs/module-spec.md`](../docs/module-spec.md): frontmatter schema,
id/type/folder agreement, required sections and ordering, dependency and
cross-reference resolution, acyclicity, and token-estimate plausibility.

```bash
python tools/validate.py framework/
```

Runs on every pull request via `.github/workflows/validate.yml`.

## Tier B — Behavioral evaluation (rubric-based)

A behavioral test is a *(passage + composed module set + question)* fixture in
[`prompts/`](prompts/), scored against a **rubric** in [`rubrics/`](rubrics/).
Rubrics list observable interpretive behaviors (e.g., "identified genre before
interpreting," "labeled speculation," "did not fabricate a citation," "presented
more than one responsible view on a debated passage").

### How to run one (manually, any model)

1. Compose the modules named in the fixture:
   `python tools/compose.py --modules book.romans`
2. Paste that prompt as the system prompt into any model (Claude, ChatGPT,
   Gemini, or a local model in Ollama / LM Studio / Open WebUI).
3. Send the fixture's user prompt.
4. Score the response against each rubric criterion (met / not met).

Because rubrics score process, the same fixture can be run across many models to
compare how well each follows the method — independent of any AI vendor.

### Optional automation

`.github/workflows/eval.yml` is a manual-dispatch workflow for running these
evaluations against a model API. It is **not** part of required CI, so the test
suite never depends on API keys or a specific vendor.

## Browser Smoke Tests

`tests/test_web_ui_selenium.py` covers browser-level smoke tests for the
workspace drawer and map browse flow. They are skipped unless `selenium` is
installed and a compatible Firefox + `geckodriver` setup is present locally.

Install the dependency with:

```bash
pip install -r tools/requirements.txt
```

## `golden/`

Reference annotations of good and poor responses for selected fixtures, used to
calibrate human scoring. (Populated as the suite grows.)
