# BHF Agent v2.1: Optional Repair Pass

BHF Agent v2.1 adds an optional repair pass for weak model answers.

The agent already validates answers and reports warnings when required method
elements are missing. The repair pass lets the agent act on those warnings by
asking the same configured local model to revise the answer once.

Repair is off by default because it requires an additional local model call and
may be slower on small NAS hardware.

## What It Does

When enabled, repair runs after the first answer is cleaned and validated.

The agent:

1. Reviews the validation result.
2. Decides whether repair is needed.
3. Builds a short targeted repair prompt.
4. Calls the same local OpenAI-compatible adapter again.
5. Cleans the repaired output.
6. Validates the repaired answer.
7. Keeps the repaired answer only if it improves validation or meets the
   configured acceptance threshold.

Repair is intentionally conservative. It is for fixing missing structure,
cautions, uncertainty labels, or method warnings. It is not a second chance to
invent new content.

## CLI Usage

Enable repair for one run:

```bash
python -m bhf_agent \
  --base-url http://localhost:11434/v1 \
  --profile minimal-7b \
  --model llama3.2:3b \
  --repair \
  "What is the Hebrew word for spirit or wind?"
```

Disable repair for one run, even if a config file enables it:

```bash
python -m bhf_agent --config examples/config.ollama-v1.json --no-repair "What does ruach mean?"
```

Override repair settings:

```bash
python -m bhf_agent \
  --base-url http://localhost:11434/v1 \
  --model llama3.2:3b \
  --repair \
  --max-repair-attempts 1 \
  --repair-threshold 80 \
  "What is the Hebrew word for spirit or wind?"
```

## Config Fields

```json
{
  "auto_repair": false,
  "max_repair_attempts": 1,
  "repair_threshold": 80
}
```

`auto_repair` controls whether repair runs automatically.

`max_repair_attempts` limits extra model calls. Version 2.1 supports `0` or `1`
cleanly and does not implement an agent loop.

`repair_threshold` is the validation score below which repair should be
attempted.

Old config files without these fields still load. The defaults keep repair
disabled.

## Decision Rules

Repair does not run when:

- `auto_repair` is false.
- `max_repair_attempts` is `0`.
- validation is missing.
- validation passed and the score meets `repair_threshold`.

Repair runs when:

- the validation score is below `repair_threshold`.
- validation failed and warnings are present.

## Acceptance Rules

The repaired answer replaces the original only when it is better enough to keep:

- the repaired validation score is higher than the original score,
- the repaired answer passes when the original did not, or
- the repaired score meets the threshold without lowering the score.

If the repair output is empty, malformed, or weaker, the original cleaned answer
is returned.

## Limits

The repair prompt tells the model to preserve correct content and fix only the
validation warnings. It also tells the model not to invent references, dates,
scholars, Hebrew or Greek claims, archaeology, or historical claims.

Repair does not use cloud services, hosted APIs, external Bible APIs, or
external lexicon APIs. It uses the same configured local adapter as the first
answer.

## Future Mobile Agent

The repair metadata is stored in the pipeline result so future app and mobile
surfaces can show whether repair was attempted, accepted, or rejected without
exposing raw provider responses or prompts by default.
