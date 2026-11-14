# Study Task Bank

The facilitator assigns four tasks per participant: the self-selected familiar
passage task, the common Deuteronomy 32:8–9 verification task, and two tasks
from the assigned group. This gives all participants a comparable discovery
and textual-evidence task while exposing the pilot to varied passages.

The group labels below are assignment slots, not completed participant data.
They do not claim that anyone has participated. For the minimum six sessions,
use slots A1, D1, B1, D2, C1, A2 in that order; for sessions seven and eight,
use B2 and C2. This gives the negative case two observations even if the
pilot ends after six participants. Assign an anonymous code P01–P08 only to an
actual consenting participant.

## Assignment matrix

| Assignment slots | Task 1 | Task 2 | Task 3 (common) | Task 4 |
|---|---|---|---|---|
| A1–A2 | Discover a familiar passage | Understand Genesis 12:1–3 | Verify Deuteronomy 32:8–9 | Continue Jonah 1:17 → Matthew 12:40 |
| B1–B2 | Discover a familiar passage | Interpret Genesis 6:1–4 | Verify Deuteronomy 32:8–9 | Verify Psalm 145:13 |
| C1–C2 | Discover a familiar passage | Interpret Psalm 82 | Verify Deuteronomy 32:8–9 | Verify 1 Corinthians 11:3 |
| D1–D2 | Discover a familiar passage | Retrieve 1 John 3:19–24 | Verify Deuteronomy 32:8–9 | Negative case: 1 Kings 2 |

Participants may receive fewer tasks if they stop early. Record assigned tasks
and mark any unobserved task explicitly. Do not replace an unfinished task
with an improvised passage.

## Participant-facing prompts and facilitator references

Do not read the stable CKL IDs aloud. The IDs and source IDs below are for the
facilitator to verify the current task before the session.

### Task A — Discover a familiar passage

**Prompt:** “Choose a Bible passage you already know. Open it in BHF and explore
what contextual research is available. Please think aloud as you decide what
to open and what seems relevant.”

The participant chooses the passage; record its reference as `starting_passage`.
Do not assume a familiar passage has BHF research. If coverage is empty, note
whether the participant understands the message as BHF coverage rather than a
statement about the passage's significance.

**Task ID:** `discover-familiar-passage` — type `discover`.

### Task B — Understand Genesis 12:1–3

**Prompt:** “Look at Genesis 12:1–3. In your own words, describe one thing BHF
communicates about the passage's context or audience. What does the text say,
and what is presented as a scholarly proposal?”

**Expected record:** `ckl:genesis#claim:genesis-blessing-for-families`; passage
anchor Genesis 12:1–3; source IDs `genesis-1-50` and
`hamilton-genesis-1-17`.

**Task ID:** `understand-genesis12` — type `understand`.

### Task C — Interpret Genesis 6:1–4

**Prompt:** “Explore Genesis 6:1–4. What does BHF show about the phrase ‘sons of
God’? Which parts are observations about the passage, and which are proposed
interpretations? What uncertainty do you notice?”

**Expected record:**
`ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions`;
source IDs `g2r2-local-sarna-genesis` and `g2-doedens-sons-god`; dispute status
`major_scholarly_disagreement`.

**Task ID:** `interpret-genesis6` — type `interpret`.

### Task D — Interpret Psalm 82

**Prompt:** “Explore Psalm 82. What does BHF say about the poem's heavenly
assembly language? Can you tell what is directly observed in the wording and
what is a comparison or interpretation?”

**Expected ED-5 record:** `ckl:ancient-divine-assembly-imagery#claim:psalm-82-assembly-text`;
textual-observation record `ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language`;
comparative record `ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison`.
Source identities include `psalm-82-hebrew-text`,
`lewis-origin-character-god-2020`, and `smith-ugaritic-baal-cycle-1994`.

**Task ID:** `interpret-psalm82` — type `interpret`.

### Task E — Verify Deuteronomy 32:8–9

**Prompt:** “Find one claim about the wording of Deuteronomy 32:8–9 and locate
its supporting evidence. What source is named? Which claim does it support?
Can you identify a source locator, uncertainty notice, and review status?”

**Expected record:**
`ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant`;
source IDs `deuteronomy-32-text` and `ulrich-biblical-qumran-scrolls-2010`;
the reader identifies the manuscript witness rather than treating a
reconstruction as an extant reading.

**Task ID:** `verify-deuteronomy32` — type `verify`.

### Task F — Verify Psalm 145:13

**Prompt:** “Find the contextual research for Psalm 145:13. Locate its source
and explain, in your own words, what textual variation the reader reports and
what uncertainty remains.”

**Expected record:** `ckl:psalms#evidence:psalm-145-nun-verse-witness`; source
IDs `sanders-11qpsa-1965` and `rahlfs-hanhart-septuaginta-2006`; dispute status
`textual_variant`.

**Task ID:** `verify-psalm145` — type `verify`.

### Task G — Continue Jonah 1:17 → Matthew 12:40

**Prompt:** “Starting at Jonah 1:17, follow a verified biblical connection if
you find one. Describe which passage is the source and which passage refers
back to it, then return to where you started.”

**Expected route:** `jonah-1-17-matthew-12-40-sign-of-jonah`, direction Jonah
1:17 → Matthew 12:40, with supporting record
`ckl:jonah#claim:jonah-three-days`. Do not substitute a held candidate. Observe
whether the participant understands the direction and can return to origin.

**Task ID:** `continue-jonah-matthew` — type `continue`.

### Task H — Verify 1 Corinthians 11:3

**Prompt:** “Look at 1 Corinthians 11:3. Find the lexical research connected
with the Greek term. What source or sources can you locate, and how does BHF
communicate that the interpretation is disputed?”

**Expected record:** `ckl:1-corinthians#claim:1cor-kephale`; source IDs `bdag`
and `thiselton-1cor`; certainty `disputed`; dispute status
`lexical_uncertainty`.

**Task ID:** `verify-1corinthians11` — type `verify`.

### Task I — Retrieve 1 John 3:19–24

**Prompt:** “Use the Canonical Knowledge Library search for the question,
‘What does 1 John 3:19-24 say about a condemning heart?’ Open the result that
seems relevant. Can you connect it to the passage and find the cited support?”

**Expected record:** `ckl:1-john#claim:1jn-heart`; source IDs `1jn-greek`,
`brown`, and `smalley`. The current browser check confirms this
passage-grounded natural-language question surfaces the 1 John result. The
broader ED-5 scripted retrieval query remains a separate evaluator. This is
not a claim that every reader must choose a particular interpretation.

**Task ID:** `retrieve-1john3` — type `retrieve`.

### Task J — Negative case: 1 Kings 2

**Prompt:** “Open 1 Kings 2 and explore the available BHF research. What does
the reader tell you about its current coverage?”

**Expected result:** complete CKL lookup, zero eligible CKL items, and
`not_represented` coverage. The interface explains that this is a limit in
BHF's current coverage and does not imply that the passage lacks historical
significance. Do not coach the participant toward this understanding.

**Task ID:** `empty-1kings2` — type `negative`.

## Navigation guidance

Participants may navigate as they choose. For Task I, BHF's Canonical
Knowledge Library search is in the Context workspace. For Task G, confirm the
reader begins at Jonah 1:17 and observe whether the participant can return to
that origin. Never direct a participant to a held or unverified relationship.

These task IDs and source identities are reused from [ED-5's journey bank](../ed5/reader-journeys.md)
and its tested evaluator. No new scholarly evidence is part of this pilot.
