# BHF Book Module Expansion — Maintainer Mode (working plan)

> Resume aid for the multi-section Book-module expansion. Saved in-repo so the
> work can be picked up across sessions. Mirrors the approved planning doc.
> Progress is tracked in the "Execution log" at the bottom — update it after each
> section.

## Context

The BHF framework has all five layers proven: Core (7), Genre (7), Context (7),
Language (1: `language.greek`), Book (5: Genesis, Psalms, Matthew, Romans,
Revelation). This phase extends the **Book layer** to the remaining **61
canonical books**, acting as a long-term maintainer: matching the existing Book
Modules' structure, voice, length, and cross-reference style exactly, never
teaching theology or conclusions — only *how to approach* each book.

`book.genesis` and `book.revelation` are the verbatim style/voice anchors.

**Confirmed decisions:**
1. **One module per book** — strict one-book-one-id for all 61; no merging.
2. **Create missing prerequisite modules first**, then reference them.
3. **Stop after each canonical section** — push and pause for review.

## Authoritative standard (must match)

- **Book section contract** (`tools/validate.py` `BOOK_REQUIRED_SECTIONS`, in
  order): `## Purpose` · `## When to apply` · `## Genre signals` ·
  `## Historical anchors` · `## Literary features` · `## Key interpretive questions` ·
  `## Common misreadings` · `## Handling uncertainty` · `## Cross-references`.
- **Frontmatter** (match `book.genesis`): `id: book.<slug>`, `title: NAME (Book Module)`,
  `type: book`, `version: 0.1.0`, `status: stable`, `tokens: <measured>`,
  `requires: [core.core-framework, <primary genre>]`, `recommends: [...]`,
  `tags: [...]`, `sources_required: true`, `maintainers: []`, `license: CC-BY-4.0`.
- **Voice:** direct, academic, second-person to the AI; "hermeneutic profile, not
  a commentary"; **Key interpretive questions posed, never answered**; Common
  misreadings describe the mistake neutrally (never criticize a tradition);
  contested books explicitly "present the major approaches… leave the conclusion
  to the reader." Body ~700–870 measured tokens.
- **Cross-references:** only `[[id]]`s that exist; reference Context modules in
  Historical anchors rather than restating; `requires` = core + primary genre,
  `recommends` = secondary genres + context + language + `core.intertextuality`.
- **Token rule:** declared `tokens` within 35% of measured (`estimate_tokens` =
  chars/4). Patch to measured after writing.
- Non-book modules (new genre/context/language) use the OTHER contract: Purpose ·
  When to apply · Interpretive moves · Common errors to avoid · Handling
  uncertainty · Cross-references (match `context.roman-empire`, `language.greek`).

## Step 0 — Prerequisite modules (create first)

6 new non-book modules (method-only, neutral):

| New module | Type | Justification |
|---|---|---|
| `language.hebrew` | language | Every OT book; parallels `language.greek`. |
| `genre.law` | genre | Exodus/Leviticus/Numbers/Deuteronomy; fills the "Law" genre `core.genre-awareness` already names. |
| `context.israelite-monarchy` | context | Samuel, Kings, Chronicles, royal psalms, pre-exilic prophets. |
| `context.exile-and-restoration` | context | Kings(end), Chronicles, Ezra, Nehemiah, Esther, Daniel, Lamentations, Ezekiel, Jeremiah, Isaiah 40–66, Haggai, Zechariah, Malachi, Obadiah, Joel. |
| `context.greco-roman-world` | context | Acts + 13 Pauline + 8 General Epistles. Complements `context.roman-empire`. |
| `context.wisdom-tradition` | context | Job, Proverbs, Ecclesiastes (+ James). *Most discretionary — cut if leaning on `genre.wisdom` + `context.ancient-near-east`.* |

Then update the `scholar` profile (`profiles/profiles.yml`) to add `genre.law` +
the 4 new context + `language.hebrew`; regenerate `profiles/scholar.md`.
`minimal-7b`/`standard` unchanged. Validate, push, pause for review.

## Steps 1–8 — Book modules by section (one section per turn; push + pause)

`requires` = `[core.core-framework, <primary genre>]`; `recommends` = secondary
genre(s) + Context modules named in Historical anchors + `language.hebrew`/
`language.greek` + `core.intertextuality` where the book heavily reuses Scripture.

1. **Torah (4):** Exodus (`genre.narrative`+`genre.law`; ANE, covenant, temple),
   Leviticus (`genre.law`; temple, covenant, ANE), Numbers (`genre.narrative`+law;
   ANE, covenant), Deuteronomy (`genre.law`; covenant/treaty form, ANE). +`language.hebrew`.
2. **Historical Books (12):** Joshua, Judges, Ruth, 1–2 Samuel, 1–2 Kings,
   1–2 Chronicles, Ezra, Nehemiah, Esther. Primary `genre.narrative`;
   `context.israelite-monarchy` (Samuel/Kings/Chronicles), `context.exile-and-restoration`
   (Kings-end/Chronicles/Ezra/Nehemiah/Esther), ANE, `language.hebrew`. Ruth →
   honor-shame (kinship/levirate); Esther → exile/diaspora (note lack of explicit
   divine reference).
3. **Wisdom (4):** Job (`genre.wisdom`+`genre.poetry`; wisdom-tradition, ANE),
   Proverbs (`genre.wisdom`; wisdom-tradition), Ecclesiastes (`genre.wisdom`;
   wisdom-tradition), Song of Songs (`genre.poetry`; ANE — note allegorization as
   misreading). +`language.hebrew`.
4. **Major Prophets (5):** Isaiah, Jeremiah (`genre.prophecy`+`genre.poetry`;
   monarchy, exile), Lamentations (`genre.poetry`; exile — poetry not prophecy),
   Ezekiel (`genre.prophecy`+`genre.apocalyptic`; exile, temple), Daniel
   (`genre.apocalyptic`+`genre.narrative`; exile, second-temple). +`language.hebrew`,
   `core.intertextuality`.
5. **Minor Prophets (12):** Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum,
   Habakkuk, Zephaniah, Haggai, Zechariah, Malachi. Primary `genre.prophecy`
   (+`genre.poetry`); pre-exilic → monarchy; post-exilic (Haggai/Zechariah/
   Malachi/Obadiah/Joel) → exile-and-restoration; Zechariah → `genre.apocalyptic`;
   **Jonah** → primary `genre.narrative` (note irony). +`language.hebrew`,
   `core.intertextuality`.
6. **Gospels & Acts (4):** Mark, Luke, John (`genre.gospel`+`genre.narrative`;
   second-temple, roman-empire, greco-roman-world, `language.greek`), Acts
   (`genre.narrative`; roman-empire, greco-roman-world, second-temple). John —
   distinct style. +`core.intertextuality`.
7. **Pauline (12):** 1–2 Corinthians, Galatians, Ephesians, Philippians,
   Colossians, 1–2 Thessalonians, 1–2 Timothy, Titus, Philemon. Primary
   `genre.epistle`; roman-empire, greco-roman-world, patronage/honor-shame,
   second-temple (Galatians), `language.greek`, `core.intertextuality`. Note
   authorship debates (Ephesians, Colossians, Pastorals); Philemon → slavery/patronage.
8. **General Epistles (8):** Hebrews (`genre.epistle`; homiletic; temple,
   second-temple, heavy intertextuality), James (`genre.epistle`+`genre.wisdom`;
   honor-shame), 1–2 Peter, 1–3 John, Jude (second-temple; note non-canonical
   source use). greco-roman-world, `language.greek`.

## Per-module quality checklist (verify before each commit)

Teaches method not conclusions · no Core duplication · no Genre duplication ·
references Context modules · observation before interpretation · historical
awareness · literary awareness · labels uncertainty · usable across traditions ·
model-agnostic/future-proof · Key interpretive questions unanswered · contested
books explicitly neutral.

## Verification (after each section)

```bash
# patch tokens to measured
.venv/bin/python - <<'PY'
import re, pathlib, sys; sys.path.insert(0,'tools')
from bhf_lib import load_modules, estimate_tokens
for m in load_modules(pathlib.Path('framework')).values():
    t=estimate_tokens(m.body); s=m.path.read_text()
    n=re.sub(r'^tokens:.*$',f'tokens: {t}',s,count=1,flags=re.M)
    if n!=s: m.path.write_text(n)
PY
.venv/bin/python tools/validate.py framework/          # frontmatter, sections+order, deps, [[id]], tokens
# inline markdown link checker (all resolve)
# programmatic check: each new book has the 9 sections in order
.venv/bin/python tools/compose.py --profile scholar --write   # Step 0 only
```

Update `CHANGELOG.md` `[Unreleased]` once per section. No `tools/*.py` logic
changes expected.

## Out of scope
- No theology/doctrine/commentary. Books not added to minimal-7b/standard profiles.
- Optional later: add `genre.law` to `core.genre-awareness` xrefs; add
  `language.hebrew` to OT genre modules' `recommends`.

---

## Execution log (update as work proceeds)

- [x] Step 0 — prerequisite modules (`language.hebrew`, `genre.law`,
      `context.israelite-monarchy`, `context.exile-and-restoration`,
      `context.greco-roman-world`, `context.wisdom-tradition`) + scholar profile
      — done 2026-06-20; 33 modules valid, scholar.md regenerated (~16k tokens).
- [x] Step 1 — Torah (Exodus, Leviticus, Numbers, Deuteronomy)
      — done 2026-06-20; 37 modules valid.
- [x] Step 2 — Historical Books (Joshua … Esther, 12)
      — done 2026-06-20; 49 modules valid.
- [x] Step 3 — Wisdom (Job, Proverbs, Ecclesiastes, Song of Songs)
      — done 2026-06-20; 53 modules valid.
- [x] Step 4 — Major Prophets (Isaiah, Jeremiah, Lamentations, Ezekiel, Daniel)
      — done 2026-06-20; 58 modules valid.
- [x] Step 5 — Minor Prophets (Hosea … Malachi, 12)
      — done 2026-06-20; 70 modules valid.
- [ ] Step 6 — Gospels & Acts (Mark, Luke, John, Acts)
- [ ] Step 7 — Pauline Letters (1 Corinthians … Philemon, 12)
- [ ] Step 8 — General Epistles (Hebrews … Jude, 8)

Reference anchors: `framework/books/genesis.md`, `framework/books/revelation.md`.
Tooling: activate venv (`source .venv/bin/activate`) or use `.venv/bin/python`.
