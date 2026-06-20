# Using BHF with Claude, ChatGPT, and Gemini

BHF is model-agnostic. The pattern is the same everywhere: put a composed BHF
prompt where the model reads persistent instructions, then ask your question.

## Get a prompt

Either copy a ready-made profile from [`../../profiles/`](../../profiles/)
(e.g. `standard.md`), or compose your own:

```bash
python tools/compose.py --modules book.romans      # core + epistle + romans, resolved
python tools/compose.py --profile standard          # genre-agnostic core method
```

Copy the output.

## Claude

- **Claude Projects:** create a Project and paste the composed prompt into the
  Project's **custom instructions / knowledge**. All chats in that Project inherit
  the method.
- **One-off chat:** paste the prompt as your first message, then ask your
  question in the next.
- **API:** pass the composed prompt as the `system` prompt.

## ChatGPT

- **Custom GPT:** paste the prompt into the GPT's **Instructions**.
- **Custom instructions:** paste a small profile (e.g. `minimal-7b`) into the
  "How would you like ChatGPT to respond?" box (mind the length limit).
- **One-off chat / API:** paste as the first message, or set as the `system`
  message via the API.

## Gemini

- **Gem (custom):** paste the prompt into the Gem's instructions.
- **One-off chat / API:** provide the prompt as a system instruction or first
  message.

## Tips

- For a specific book, compose with that book module
  (`--modules book.romans`); the genre, historical, and language dependencies it
  recommends can be added explicitly for more depth.
- Keep an eye on context limits — see
  [`small-models-7b.md`](small-models-7b.md) for trimming guidance, which also
  helps when instruction fields have tight length caps.
