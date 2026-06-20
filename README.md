# Biblical Hermeneutics Framework (BHF)

**A model-agnostic, open-source framework that teaches AI models *how* to interpret Scripture responsibly — not *what* to believe.**

[![Validate](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/workflows/validate.yml/badge.svg)](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/workflows/validate.yml)
&nbsp; Content: **CC BY 4.0** · Code: **MIT** · Version: see [`VERSION`](VERSION)

---

## What BHF is

BHF is a library of small, composable Markdown **modules** that you load into
any AI model — Claude, ChatGPT, Gemini, or a local model via Ollama, LM Studio,
or Open WebUI — to make its biblical interpretation more careful. The modules
encourage a model to:

- Begin with the **original audience** and the text's historical/cultural setting.
- Identify the **literary genre** before interpreting.
- **Observe** the text before interpreting it, and interpret before applying it.
- Distinguish **scholarly consensus, majority views, minority views, and speculation.**
- **Admit uncertainty** when the evidence is thin.
- Avoid **hallucinating** historical facts, language claims, or scholarly opinions.
- Respect differing Christian traditions without forcing one theological system.

## What BHF is **not**

> [!IMPORTANT]
> BHF is **not** a theology engine, a doctrinal statement, or a denomination's
> prompt. It never tells anyone what to conclude. It teaches *method* —
> how to ask better questions of a text — and deliberately leaves the answers
> open. See [`docs/philosophy.md`](docs/philosophy.md) and
> [`GOVERNANCE.md`](GOVERNANCE.md) (the neutrality charter).

---

## Quick start

### Option A — use the hosted GPT (nothing to install)

Try BHF instantly in the
[**Biblical Hermeneutics Framework (BHF) GPT**](https://chatgpt.com/g/g-6a36d3641a1c8191afa101ed50a927e9-biblical-hermeneutics-framework-bhf)
— a public ChatGPT custom GPT preloaded with the full-depth
[`scholar`](profiles/scholar.md) profile. Just open it and ask your question.
(Requires a ChatGPT account; powered by the same open modules in this repo.)

### Option B — copy/paste a ready-made profile (no tools needed)

1. Open a pre-assembled prompt in [`profiles/`](profiles/):
   - [`profiles/minimal-7b.md`](profiles/minimal-7b.md) — smallest, for tiny local models.
   - [`profiles/standard.md`](profiles/standard.md) — balanced, for most use.
   - [`profiles/scholar.md`](profiles/scholar.md) — full-depth, for frontier models with large context windows (this powers the hosted GPT above).
2. Paste it into your model's **system prompt** / **custom instructions** /
   **Modelfile** / **Project** instructions.
3. Ask your question. See [`docs/how-to-use/`](docs/how-to-use/) for per-runtime guides.

### Option C — compose your own from modules (light tooling)

```bash
pip install -r tools/requirements.txt

# Validate the module library
python tools/validate.py framework/

# Build a single prompt from chosen modules (dependencies auto-included)
python tools/compose.py --modules genre.epistle,book.romans

# Or build a named profile
python tools/compose.py --profile standard
```

---

## Repository layout

| Path | What's there |
|------|--------------|
| [`framework/`](framework/) | The product: `core/`, `genres/`, `books/`, `context/`, `language/` modules (CC BY 4.0) |
| [`profiles/`](profiles/) | Pre-assembled, copy/paste-ready prompt bundles |
| [`docs/`](docs/) | Philosophy, architecture, the authoritative [module spec](docs/module-spec.md), style guide, how-to guides |
| [`tools/`](tools/) | `validate.py`, `compose.py` (MIT) |
| [`tests/`](tests/) | Behavioral rubrics + fixtures (test *method*, never doctrine) |
| [`examples/`](examples/) | Walkthroughs of the method in action |

## How modules compose

Each module declares its `requires` (hard dependencies) and `recommends` in
YAML frontmatter, plus an approximate `tokens` cost. `compose.py` resolves
dependencies and orders modules (core first) into one coherent prompt that fits
your model's budget — the same library serves a 7B phone model and a frontier
model. See [`docs/architecture.md`](docs/architecture.md).

## Contributing

New genre, book, context, and language modules are welcome — there are 66
books to cover. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the relevant
`_TEMPLATE.md`. Every contribution must pass `validate.py` and the
**neutrality + sourcing** review.

## License

- **Content** (`framework/`, `docs/`, `profiles/`, `examples/`): [CC BY 4.0](LICENSE-CONTENT)
- **Code** (`tools/`, CI): [MIT](LICENSE)
