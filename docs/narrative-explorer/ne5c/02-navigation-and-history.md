# NE-5C navigation and history

## Companion integration

The trail runs in the existing native resource host. Mobile uses the existing
Companion sheet; desktop uses the existing dock. NE-5C does not add another
reader, application shell, or browser-history listener. Its trail is included
in the existing `bhfStudyCompanion` history snapshot, with a twelve-node bound
and a small field allowlist.

Opening the Narrative Explorer initializes the trail in the current Companion
history entry. Opening evidence, following a CKL subject, or following a linked
passage pushes a new Companion entry. The existing browser Back and Forward
events restore the saved trail and focus. Trail Back uses that same browser
history. The visible breadcrumb identifies the current step; Return to the
origin resets the trail to its original passage.

## Passage switching and return

The origin snapshot preserves book, chapter, selected verses, selected text,
translation, selected word, and reference. A linked passage is validated
against the reader's canonical book and chapter list before navigation. It is
opened through `BHFReader.navigateToPassage`; the Companion and existing
reader-selection state remain in use.

Return to the origin navigates the existing reader to the original selection,
restores its verse set and translation, and reopens the original passage
projection. The trail never treats the linked passage as a replacement for
the origin identity. Back and Forward across a passage hop restore the
corresponding passage selection before restoring the trail view.

## Focus and keyboard use

Evidence, connection, Scripture, Back, and Return actions are native buttons.
The breadcrumb uses a labelled navigation landmark and identifies its current
step. Detail headings are programmatically focusable. After a trail change the
view focuses its heading; after Back or Forward it first attempts to restore
focus to the control that opened the destination, then falls back to the
heading. The original Companion and reader focus paths remain in place when
the resource closes.

The mobile stylesheet stacks evidence sections and makes navigation controls
full width with a 44-pixel minimum target. The same resource and history code is
used at both viewport sizes.
