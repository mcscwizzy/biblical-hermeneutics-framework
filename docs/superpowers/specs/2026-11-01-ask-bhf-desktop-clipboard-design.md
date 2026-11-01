# Ask BHF desktop clipboard handoff design

## Intent

Start clipboard writing during the Ask BHF click before opening the external assistant, because opening a tab can shift focus and cause desktop clipboard permission failures. Keep the prepared question selectable and provide a clear Copy Question then Open BHF recovery path.

## Goals and constraints

- Preserve the current passage context, configured GPT destination, mobile interaction, and `noopener noreferrer` protections.
- Do not report a copy as successful until `writeText` resolves successfully.
- Treat a `null` result from `window.open` as ambiguous; keep the explicit Open BHF link available after an attempt.
- Limit changes to the Ask BHF handoff, its tests, cache key, and handoff documentation.

## Approaches

- Open first, then copy: preserves current ordering but can lose desktop clipboard focus.
- Await clipboard, then open: allows clipboard status before navigation but can consume user activation and trigger popup blocking.
- Start clipboard synchronously, immediately attempt the secure popup without awaiting, and expose Open BHF as a fallback: preserves user activation for both operations while handling permission failure and ambiguous popup results. This is the selected approach because it addresses the reported focus failure without weakening link protections.

## Implementation outline

Update the handoff controller and frontend tests, add a desktop browser regression that makes clipboard completion fail after a simulated focus loss, bump the `assistant-handoff.js` query version, and update the existing Ask BHF handoff documentation with the recovery behavior and verification results.
