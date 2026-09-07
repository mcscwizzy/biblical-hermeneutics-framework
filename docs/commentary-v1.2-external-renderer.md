# Commentary v1.2 external renderer round-trip

Commentary v1.2 keeps rendering provider-neutral. The repository exports one exact prompt packet per chapter and accepts one isolated response envelope per packet. It does not call a renderer during this workflow.

## Response envelope

Place each response in `.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary/responses/raw/` as JSON:

```json
{
  "reference": "Genesis 1",
  "packet_id": "commentary-v1.2-packet:<sha256>",
  "prompt_version": "1.2",
  "evidence_hash": "<locked evidence hash>",
  "synthesis_hash": "<locked synthesis hash>",
  "renderer_label": "Luna Medium",
  "response_payload": {
    "reference": "Genesis 1",
    "book": "Genesis",
    "chapter": 1,
    "status": "pending",
    "sections": [
      {
        "kind": "chapter_overview",
        "title": "Overview",
        "blocks": [
          {
            "id": "block_1",
            "text": "Renderer-authored explanation grounded in the packet.",
            "verse_refs": ["Genesis 1:1"],
            "evidence_ids": ["an-evidence-id-from-the-cited-unit"],
            "synthesis_ids": ["a-synthesis-id-from-the-packet"],
            "confidence": "medium",
            "interpretation_level": "fact"
          }
        ]
      }
    ],
    "generated_metadata": null
  }
}
```

`response_payload` is the renderer-authored commentary object only. The renderer label is informational. BHF ignores renderer-supplied lifecycle and generation metadata, stamps authoritative provenance, then runs the normal Commentary v1.2 validator.

## Commands

```sh
.venv/bin/python tools/commentary_v12_canary.py prepare
.venv/bin/python tools/commentary_v12_canary.py export
.venv/bin/python tools/commentary_canary_import.py
.venv/bin/python tools/commentary_v12_canary.py compare
.venv/bin/python tools/commentary_v12_canary.py gate
```

The export is ordered by chapter and gives the packet ID, reference, prompt path, and expected raw-response path. Render all 13 packets as separate transactions; never combine chapters in one request.

Raw responses are immutable inputs. Fully validated BHF candidates are written to `canary/responses/accepted/`; diagnostic rejection records are written to `canary/responses/rejected/`. A `CANARY_PASS` only marks the architecture ready for human review and never authorizes bulk generation.
