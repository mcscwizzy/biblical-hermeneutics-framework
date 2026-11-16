# Data Management

## Local record workflow

The schema and standard-library utility support de-identified JSONL. Keep
source notes and completed records outside Git in a restricted local location.
The default ignored store is `.bhf-data/ed6-reader-pilot/sessions.jsonl`.
Confirm that this directory remains ignored before adding data.

1. Obtain consent before assigning a participant code or starting a task.
2. Create a private copy of [the notes template](participant-notes-template.md).
3. Review every free-text entry and remove names, contact information, and
   indirect identifiers before structuring the record.
4. Create one JSON object per participant session, with
   `record_origin: "participant_session"`; use only `P01`, `P02`, etc. Do not
   reuse a code.
5. Validate the private JSONL file:

   ```bash
   .venv/bin/python tools/ed6_reader_pilot.py validate /restricted/path/sessions-to-import.jsonl
   ```

6. Import a fully valid batch atomically into the ignored local store:

   ```bash
   .venv/bin/python tools/ed6_reader_pilot.py import /restricted/path/sessions-to-import.jsonl
   ```

   The importer rejects malformed or invalid records and duplicate codes; it
   will not append a partial batch. It creates files with owner-only mode
   where supported. A previous store must itself validate before append.
7. Generate aggregate JSON locally:

   ```bash
   .venv/bin/python tools/ed6_reader_pilot.py report --output /restricted/path/ed6-aggregate-report.json
   ```

The report contains aggregate counts and explicit denominators, but no raw
free-text observations, quotations, participant codes, or direct identifiers.
Review aggregate outputs before sharing because small groups can still make a
person identifiable through context.

## Validation behavior and limitations

The validator checks the record shape, task IDs and task types, duplicate
codes, status values, common direct-identifier fields and patterns, and quote
consent. Invalid lines are reported without echoing their contents. It does
not recognize every name, indirect identifier, or sensitive disclosure;
human review of free text remains necessary. Do not place personal records in
the repository, issue tracker, pull request, chat, or test fixtures.

Incomplete and stopped sessions remain in aggregate denominators with
unobserved task states. If an assigned task has no observation, leave it out
of `tasks`; the report counts that assignment as `not_observed`. If the
facilitator observed that it was not attempted, include an explicit task entry
with `completion: "not_attempted"`. Missing values are not silently converted
to success or failure. Reports describe this convenience sample only and do
not estimate all Bible readers.

## Synthetic separation and retention

The checked-in file `tests/fixtures/ed6_reader_pilot/synthetic_sessions.jsonl`
is invented regression data. It is marked `synthetic_test_fixture` and normal
CLI operations reject it. Do not copy it to the real local store or use its
contents in study findings. Synthetic tests run with temporary directories.

No analytics, accounts, automatic upload, or recording is used. If recording
is separately proposed, follow [consent and privacy](consent-and-privacy.md)
and retain recordings separately under restricted access with an explained
deletion date. Delete raw notes when the facilitator no longer needs them for
the documented analysis; retain only de-identified aggregates needed for the
pilot handoff. The maintainer should record an actual retention date before
recruitment rather than inventing one in advance.
