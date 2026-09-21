# Ask BHF assistant handoff

BHF's web application owns the deterministic study experience: Scripture,
Commentary v1.2, CKL evidence, lexicons, archaeology, maps, cross-references,
notes, highlights, and offline study data. It does not run conversational model
inference at runtime.

When a reader wants conversation or follow-up interpretation, **Ask BHF** opens
a compact handoff composer. The composer uses the current book and chapter (and
an existing verse/range selection when available), builds concise text, copies
it to the clipboard, and opens the configured external assistant in a new tab.
It never embeds or automates the assistant.

The destination is configured with `BHF_ASSISTANT_URL`. The current default is
the BHF assistant hosted in ChatGPT, but the setting is intentionally generic so
it can later point to a BHF Plugin or another supported assistant destination
without changing the reader.

If automatic clipboard access is unavailable, the prepared question remains
visible and selectable. The user can copy it manually and use the explicit
**Open BHF** fallback. Popup opening is initiated by the direct button click;
if a browser blocks it, the same explicit fallback remains available.

The handoff is an online convenience. It does not affect Bible reading,
Commentary, CKL/evidence, lexicons, notes, highlights, maps, or other offline
capabilities.

Maintainer-side model adapters and generation tooling remain separate from the
web runtime for future corpus/release work. They are not exposed through BHF
user settings or browser requests.
