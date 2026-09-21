# Using BHF prompt profiles with local models

This guide covers the standalone prompt framework only. The BHF web
application does not connect to Ollama, LM Studio, Open WebUI, or another model
runtime. In the application, use **Ask BHF** to hand a study question to the
configured external BHF assistant.

If you are using BHF's generated profiles outside the application, compose a
profile and load it as the local model's system prompt.

## Ollama

Bake the method into a custom model with a **Modelfile**:

```dockerfile
FROM llama3.1
SYSTEM """
<paste the contents of profiles/standard.md here>
"""
```

```bash
python tools/compose.py --profile standard > /tmp/bhf.txt   # then paste into the Modelfile
ollama create bhf-standard -f Modelfile
ollama run bhf-standard
```

Alternatively, paste the prompt as your first message in `ollama run`.

## LM Studio

- Open the **System Prompt** field for your chat and paste a composed profile
  (`profiles/standard.md` or `profiles/minimal-7b.md`).
- Smaller quantized models do better with the smaller profile — see
  [`small-models-7b.md`](small-models-7b.md).

## Open WebUI

- Create a **Model** (or a **Prompt preset**) and paste the composed prompt into
  its **System Prompt**.
- You can also save it as a reusable prompt template and prepend it per chat.

## Picking a profile by model size

| Model size | Suggested starting profile |
|------------|----------------------------|
| ~3B–7B | `profiles/minimal-7b.md` |
| ~8B–13B | `profiles/standard.md` |
| larger | `standard` + a specific genre/book module composed in |

Smaller models follow shorter, more directive prompts more reliably. Start small
and add modules only as the model handles them well.
