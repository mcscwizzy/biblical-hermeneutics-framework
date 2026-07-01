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

Behavior checks can use `pattern` for regular expressions or `keywords` for a
list of required substrings. Forbidden matches subtract from the score.
