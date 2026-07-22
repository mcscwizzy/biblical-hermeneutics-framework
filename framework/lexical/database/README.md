# Lexical database

This directory is the destination for a locally generated `lexicon.sqlite`.
The database is intentionally ignored by Git because it is derived from
externally supplied lexical source files.

Runtime expects the generated database at:

```text
framework/lexical/database/lexicon.sqlite
```

Build, validate, and smoke test it with
[`docs/compile-lexicon.md`](../../../docs/compile-lexicon.md).

Do not place raw XML, downloaded dictionaries, or other source exports in
this directory. If `lexicon.sqlite` is missing, Word Study must report
unavailable deterministic lexical data rather than substituting LLM guesses.
