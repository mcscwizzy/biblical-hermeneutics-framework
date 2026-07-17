# Local BHF Agent Evals

BHF evals score interpretive method, not doctrinal conclusions. The local eval
runner is deterministic and offline-friendly: it uses fixture-defined regex and
keyword checks, not an LLM judge.

## Saved Answer Mode

Use this when you already have an answer in a text file:

```bash
python tools/eval_local.py \
  --fixture tests/prompts/proverbs-context-basic.json \
  --answer-file output.txt
```

Add `--json` for machine-readable output.

## Regression Suite Mode

Use this when you want to run a repeatable CKL regression set with per-case
metadata assertions:

```bash
python tools/eval_local.py \
  --suite tests/prompts/ckl-regression-suite.json \
  --config local.config.json
```

Suite cases can carry `config_overrides` for CKL toggles such as
`enabled`, `allowed_statuses`, and `max_context_tokens`, plus
`metadata_checks` for object IDs, retrieval method, topic count, and prompt
token limits.

## Optional Model-Call Mode

Use this only when you want the eval runner to call the configured local BHF
Agent:

```bash
python tools/eval_local.py \
  --fixture tests/prompts/proverbs-context-basic.json \
  --config local.config.json
```

The fixture's `profile` and `answer_mode` override those fields from the config
for the eval run. This mode may require a running local OpenAI-compatible model
server, depending on the config.

## Fixture Shape

Fixtures are JSON objects with:

- `id`
- `question`
- `profile`
- `answer_mode`
- `expected_behaviors`
- `forbidden_behaviors`
- `pass_threshold`
- `config_overrides` is optional and can tweak agent settings for the case.
- `metadata_checks` is optional and can assert retrieval metadata from the agent.

Behavior checks can use `pattern` for regular expressions or `keywords` for a
list of required substrings. Forbidden matches subtract from the score.
Metadata checks can assert equality, membership, exclusion, or numeric bounds
against fields in the returned agent metadata.
