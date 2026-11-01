# Ask BHF assistant handoff

BHF owns the local study experience: Scripture, Narrative Explorer evidence,
CKL, lexical tools, archaeology, maps, Tyndale Open Study Notes, private study
records, and supported offline features. Conversational synthesis happens in
the configured external assistant; the web runtime does not make a provider
request for ordinary reader or evidence navigation.

When a reader chooses **Ask BHF**, the handoff composer uses the current
passage and any selected verse range, prepares concise text, and keeps it
visible for review. The **Copy Question & Open BHF** action starts clipboard
writing in the click handler, then attempts to open the configured assistant
in a new tab with `noopener noreferrer`. BHF does not embed or automate the
external assistant.

Set `BHF_ASSISTANT_URL` to choose the destination. If automatic clipboard
access fails, the UI reports the failure, selects the prepared question for
manual copying, and offers **Copy prepared question** and **Open BHF** actions.
The **Open BHF** link remains available after every handoff attempt. Browsers
may return `null` from `window.open` when `noopener` is enabled even when the
new tab opened, so BHF does not treat that return value as proof that the
browser blocked the tab. If the new tab did not open, choose **Open BHF** to
continue.

## Desktop handoff verification

The desktop browser regression simulates `window.open` shifting focus before
the clipboard promise settles. It verifies that clipboard writing starts
first, a rejected write never reports success, the prepared question remains
selected, and manual copy plus the protected **Open BHF** link recover the
handoff. The frontend controller tests also cover a `null` popup return and
manual copy recovery.

On 2026-11-01, `node tests/frontend/assistant-handoff.test.js` passed all 12
tests. The focused desktop Ask BHF suite plus the existing mobile handoff case
passed 6 tests. The full `tests/gui/test_ask.py` run also exposed an existing
Escape/Maps timeout that occurs before Ask BHF opens; the same failure
reproduced on unchanged `master`, so it was excluded from the focused handoff
acceptance run.

The handoff is an online convenience. It does not affect passage navigation,
CKL evidence, Tyndale notes, translations, maps, archaeology, notes, highlights,
or locally cached study resources. Private notes and highlights are not added
to the handoff automatically.

Generated BHF Commentary was retired in NE7R3. Tyndale Open Study Notes remains
an active, separate source and is included only through its documented source
provider behavior. See [Tyndale Open Study Notes](tyndale-study-notes.md) and
[Narrative Explorer](narrative-explorer/README.md).
