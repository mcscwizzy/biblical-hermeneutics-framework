# Ask BHF assistant handoff

BHF owns the local study experience: Scripture, Narrative Explorer evidence,
CKL, lexical tools, archaeology, maps, Tyndale Open Study Notes, private study
records, and supported offline features. Conversational synthesis happens in
the configured external assistant; the web runtime does not make a provider
request for ordinary reader or evidence navigation.

When a reader chooses **Ask BHF**, the handoff composer uses the current
passage and any selected verse range, prepares concise text, copies it when
clipboard access is available, and opens the configured assistant in a new
tab. The user can review and edit the prepared question. BHF does not embed or
automate the external assistant.

Set `BHF_ASSISTANT_URL` to choose the destination. If automatic clipboard
access is unavailable, the prepared question remains selectable for manual
copy. If the browser blocks the new tab, the explicit **Open BHF** action
remains available.

The handoff is an online convenience. It does not affect passage navigation,
CKL evidence, Tyndale notes, translations, maps, archaeology, notes, highlights,
or locally cached study resources. Private notes and highlights are not added
to the handoff automatically.

Generated BHF Commentary was retired in NE7R3. Tyndale Open Study Notes remains
an active, separate source and is included only through its documented source
provider behavior. See [Tyndale Open Study Notes](tyndale-study-notes.md) and
[Narrative Explorer](narrative-explorer/README.md).
