# Consent and Privacy

## Read-aloud participant script

> We are trying out the BHF Bible study reader. We want to learn whether the
> interface helps people find contextual research and follow the evidence. We
> are testing the reader, not your Bible knowledge, beliefs, or interpretation.
>
> Taking part is your choice. You may skip any question or stop at any time,
> without giving a reason. The session should take about 20–30 minutes. I will
> take brief notes using an anonymous code. We do not need your name, email,
> church, denomination, or religious background. There are no accounts,
> analytics tracking, or external uploads in this study.
>
> We will not record your screen or voice. If a facilitator later asks to
> record a session, that will require a separate clear explanation and your
> separate explicit consent; saying no will not affect your participation.
>
> You can ask us to stop taking notes at any time. If you want notes removed
> after the session, keep your anonymous code and contact the facilitator
> before findings are combined into an aggregate report. We will not present
> your individual notes as a public result.
>
> Do you understand this and agree to take part?

Record only **yes** or **no** and the participant code. If the person says no,
thank them and do not begin the study. Do not infer consent from starting a task.

## Optional quotation consent

If a facilitator wants to use a short direct quotation in a private research
summary, ask separately after explaining that the quote will be de-identified.
Record `quote_consent: true` only after an explicit yes. A participant may
decline quotations and still take part. Do not quote comments about personal
faith, identity, or other sensitive experiences even when quote consent is
given. The notes template can record a paraphrase without quotation marks.

## Recording

Recording is not part of the normal protocol. If recording is proposed, obtain
separate explicit consent before turning on any device. Explain what is
recorded, why it is useful, who can access it, the exact restricted storage
location, and a deletion date. Store the file separately from study notes and
never in this repository, a public cloud folder, a chat, or a third-party
analytics service. If these details cannot be explained in advance, do not
record.

## Data minimization

- Use codes such as P01; do not write a participant's name into the notes.
- Do not collect an email, phone number, church, denomination, IP address,
  precise age, account ID, or identifying location in the dataset.
- If study experience is useful, use only the broad optional categories in the
  [record schema](session-record.schema.json); `prefer_not_to_say` is valid.
- Keep direct observations separate from facilitator interpretations.
- Obtain separate quotation consent for verbatim quotations.
- Store source notes and session records locally or in an access-restricted
  location. The importer defaults to `.bhf-data/ed6-reader-pilot/`, which Git
  ignores, and creates files with mode `0600`.
- Do not use analytics, participant accounts, screen capture, voice capture,
  or external uploads.

The facilitator should remove accidental identifiers from local notes before
import. The validator flags common email, phone, and IP patterns and forbidden
identifier fields; it cannot identify every person's name or indirect
identifier. Review all free text locally before importing.
