# Testing BHF

BHF tests implementation behavior and responsible interpretive method, not a
required doctrinal conclusion.

## Run the test suite

Create the development environment from the
[local build guide](../docs/local-development.md), then run:

```bash
python -m pytest
```

Run a focused file or directory while iterating:

```bash
python -m pytest tests/test_runner.py
python -m pytest tests/canonical_library/
```

The suite includes agent, adapter, reference, prompt, validation, web/API, PWA,
map, translation, storage, CKL schema/retrieval/content, CLI, and Docker Compose
coverage. Tests should use deterministic adapters and fixtures rather than live
provider calls.

## Structural framework validation

`tools/validate.py` checks module frontmatter, file/id/type agreement, required
sections and ordering, dependency and cross-reference resolution, acyclicity,
and token-estimate plausibility:

```bash
python tools/validate.py framework/
```

This is a required CI gate in `.github/workflows/validate.yml`.

## Behavioral evaluation

Behavioral fixtures live in [`prompts/`](prompts/) and are scored against
[`rubrics/`](rubrics/). Rubrics check observable method—for example, handling
genre, distinguishing evidence from inference, qualifying uncertainty, and not
fabricating sources—without requiring one theological conclusion.

Manual workflow:

1. Compose the modules named by a fixture.
2. Use the composed text as a model system prompt.
3. Send the fixture's user prompt.
4. Score the response against the linked rubric.

`.github/workflows/eval.yml` provides optional manual-dispatch automation. It is
not part of required CI and requires an explicitly configured model provider.
See [Evaluation](../docs/evals.md) for the local deterministic evaluator.

## Browser tests

`tests/test_web_ui_selenium.py` contains direct browser smoke coverage and is
skipped unless Selenium plus a compatible Firefox/geckodriver setup are present.

The stable GUI regression suite is in `tests/gui/` and uses `data-testid` hooks,
isolated databases, and `BHF_TEST_MODE=true` responses:

```bash
python -m pytest tests/gui -m "not slow"
```

The reproducible container path is:

```bash
docker compose -f docker-compose.yml -f docker-compose.selenium.yml up \
  --build --abort-on-container-exit --exit-code-from gui-tests gui-tests
```

Clean it up with:

```bash
docker compose -f docker-compose.yml -f docker-compose.selenium.yml down -v
```

Failed Selenium tests should retain screenshots and browser logs. New major UI
controls should have stable `data-testid` hooks and regression coverage.

## Golden annotations

[`golden/`](golden/) stores reference annotations used to calibrate human rubric
scoring. They document which method criteria a response met; they are not an
answer key for theological conclusions.
