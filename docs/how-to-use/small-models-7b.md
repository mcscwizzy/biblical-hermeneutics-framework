# Using BHF on small models (≈3B–7B)

Small local models — the kind that run on a phone or laptop — have limited
context and follow long, complex instructions less reliably. BHF is designed to
degrade gracefully to this setting.

## Use the minimal profile

Start with [`../../profiles/minimal-7b.md`](../../profiles/minimal-7b.md). It
loads only the core posture (context-first, observe/interpret/apply, label
confidence, and basic intertextual discipline) and is deliberately short.

```bash
python tools/compose.py --profile minimal-7b
```

## Token budgeting

Each module declares an approximate `tokens` cost in its frontmatter, and
`compose.py` reports the total for any selection:

```bash
python tools/compose.py --modules core.core-framework,core.epistemic-humility
# header reports module count and ~token total
```

Keep the system prompt comfortably within the model's context window, leaving
room for the passage and the model's answer.

## Practical tips for small models

- **Prefer fewer modules.** Two or three focused modules beat a giant prompt a
  small model can't track.
- **Ask one thing at a time.** Break a study into smaller questions.
- **Reinforce in the user turn.** A short reminder ("First identify the genre,
  then observe before interpreting") helps a small model stay on method.
- **Expect more hallucination risk.** Small models invent facts more readily;
  lean on `core.anti-hallucination` and verify factual claims yourself.
- **Scale up gradually.** If the model handles the minimal profile well, add the
  `standard` profile or a single genre module.
