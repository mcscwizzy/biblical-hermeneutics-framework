#!/usr/bin/env python3
"""Render one frozen v1.2 pilot batch through isolated Codex exchanges.

Each chapter gets exactly one model exchange.  Its final response bytes are
preserved even when they are malformed; the driver never scores or retries.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from framework.commentary.production.models import ArtifactCollisionError, write_immutable
from tools import commentary_v12_scale_pilot as pilot


CODEX = Path("/home/johnwalker/.local/bin/codex")


def render_batch(batch: int) -> dict[str, object]:
    context = pilot.build_context()
    root = context["root"]
    manifest = context["manifest"]
    stored = pilot._read(root / "manifest.json")
    pilot._verify_identity(stored, "manifest_identity", "scale pilot manifest")
    if stored != manifest:
        raise pilot.ScalePilotError("frozen scale-pilot inputs changed")
    rows = [row for row in manifest["chapters"] if row["batch"] == batch]
    generated = []
    for index, row in enumerate(rows, 1):
        response_path = root / f"batch-{batch:03d}" / "responses/raw" / row["response_filename"]
        if response_path.exists():
            raw = response_path.read_bytes()
            generated.append({
                "reference": row["reference"],
                "response_path": str(response_path.relative_to(pilot.ROOT)),
                "generation_count": 1,
                "renderer_exit_code": 0,
                "syntactically_valid_json": _valid_json(raw),
                "resume_disposition": "PRESERVED_EXISTING_FIRST_RESPONSE",
            })
            print(f"batch {batch}: {index}/{len(rows)} {row['reference']} preserved", flush=True)
            continue
        input_root = root / f"batch-{batch:03d}" / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
        system_prompt = (input_root / "system_prompt.txt").read_text(encoding="utf-8")
        user_prompt = (input_root / "user_prompt.txt").read_text(encoding="utf-8")
        exchange = (
            "You are the selected GPT-5.6 Sol prose renderer at medium effort. "
            "Do not call tools, inspect files, browse, or add explanation. Treat the exact "
            "SYSTEM PROMPT and USER PROMPT below as the complete generation contract. "
            "Return the requested raw JSON object only, with no Markdown fence or preamble.\n\n"
            "SYSTEM PROMPT\n" + system_prompt + "\n\nUSER PROMPT\n" + user_prompt
        )
        with tempfile.TemporaryDirectory(prefix="bhf-v12-render-") as temp_dir:
            output = Path(temp_dir) / "response.txt"
            completed = subprocess.run(
                [
                    str(CODEX), "exec", "--ephemeral", "--ignore-user-config",
                    "-m", pilot.RENDERER, "-c", 'model_reasoning_effort="medium"',
                    "-s", "read-only", "-C", temp_dir, "--skip-git-repo-check",
                    "--output-last-message", str(output), "-",
                ],
                input=exchange,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            if not output.is_file():
                raise pilot.ScalePilotError(
                    f"renderer produced no bytes for {row['reference']} (exit {completed.returncode}): "
                    f"{completed.stderr[-1000:]}"
                )
            raw = output.read_bytes()
        try:
            write_immutable(response_path, raw)
            disposition = "GENERATED_BY_ISOLATED_EXCHANGE"
        except ArtifactCollisionError:
            # A resumed batch-level renderer may finish the same target while
            # this isolated exchange is in flight. Preserve the first bytes;
            # never replace the immutable response with the later return.
            raw = response_path.read_bytes()
            disposition = "PRESERVED_CONCURRENT_FIRST_RESPONSE"
        generated.append({
            "reference": row["reference"],
            "response_path": str(response_path.relative_to(pilot.ROOT)),
            "generation_count": 1,
            "renderer_exit_code": completed.returncode,
            "syntactically_valid_json": _valid_json(raw),
            "resume_disposition": disposition,
        })
        print(f"batch {batch}: {index}/{len(rows)} {row['reference']}", flush=True)
    result = {
        "artifact_version": f"{pilot.ARTIFACT_VERSION}-batch-generation",
        "batch": batch,
        "renderer": pilot.RENDERER,
        "renderer_effort": pilot.RENDERER_EFFORT,
        "runtime_self_attestation": False,
        "one_generation_per_chapter": True,
        "retries": 0,
        "generated_count": len(generated),
        "chapters": generated,
    }
    pilot._write_json(root / f"batch-{batch:03d}" / "batch-generation.json", result)
    return result


def _valid_json(raw: bytes) -> bool:
    try:
        return isinstance(json.loads(raw.decode("utf-8")), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=int, required=True, choices=range(1, 7))
    args = parser.parse_args()
    try:
        result = render_batch(args.batch)
    except (pilot.ScalePilotError, ArtifactCollisionError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
