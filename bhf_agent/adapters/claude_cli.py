"""Claude Code CLI adapter for local offline commentary generation.

Uses the installed `claude` command-line tool with existing authentication.
No ANTHROPIC_API_KEY required; relies on Claude Code's stored credentials.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

from .base import ChatAdapter


LOGGER = logging.getLogger(__name__)


class ClaudeCliAdapter(ChatAdapter):
    """Invoke Claude via the `claude` CLI in non-interactive print mode."""

    def __init__(self, timeout_seconds: int = 120):
        """Initialize with timeout for CLI subprocess."""
        self.timeout_seconds = timeout_seconds
        self.claude_path = shutil.which("claude")

        if not self.claude_path:
            raise RuntimeError(
                "claude command-line tool not found. "
                "Install Claude Code or ensure it is on PATH."
            )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> dict[str, str]:
        """Send messages to Claude via CLI and return response."""

        # Build the prompt from messages
        if not messages:
            raise ValueError("messages required for chat")

        # Combine system + user message
        prompt_parts = []
        if system:
            prompt_parts.append(f"[SYSTEM]\n{system}\n")

        # Take the last user message as the main prompt
        for msg in messages:
            if msg.get("role") == "user":
                prompt_parts.append(msg.get("content", ""))

        prompt = "\n".join(prompt_parts)

        if not prompt.strip():
            raise ValueError("No user message in chat messages")

        try:
            # Call claude CLI in non-interactive mode
            # --output-format json ensures structured response
            result = subprocess.run(
                [self.claude_path, "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if not stderr and result.stdout.strip():
                    try:
                        error_payload = json.loads(result.stdout)
                        stderr = str(
                            error_payload.get("result")
                            or error_payload.get("error")
                            or ""
                        ).strip()
                    except json.JSONDecodeError:
                        stderr = result.stdout.strip()
                if (
                    "not authenticated" in stderr.lower()
                    or "not logged in" in stderr.lower()
                    or "auth" in stderr.lower()
                ):
                    raise RuntimeError(
                        f"Claude CLI authentication failed. "
                        f"Please authenticate via: claude auth"
                    )
                raise RuntimeError(
                    f"Claude CLI call failed with code {result.returncode}: {stderr}"
                )

            # Parse the JSON response
            try:
                response_data = json.loads(result.stdout)
                # Extract the content from the Claude response structure
                # The result field contains the model's response text
                content = response_data.get("result") or response_data.get("content") or response_data.get("text") or ""
                if not content:
                    raise ValueError("No content in Claude response")
                return {"content": str(content)}
            except json.JSONDecodeError as exc:
                # If JSON parsing fails, treat stdout as plain text
                LOGGER.warning(f"Failed to parse Claude CLI JSON response: {exc}")
                return {"content": result.stdout.strip()}

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Claude CLI call timed out after {self.timeout_seconds} seconds"
            )
        except Exception as exc:
            raise RuntimeError(f"Claude CLI call failed: {exc}") from exc


def verify_claude_cli_available() -> bool:
    """Check if claude CLI is available and authenticated."""
    claude_path = shutil.which("claude")
    if not claude_path:
        return False

    try:
        # Make a minimal non-destructive test call
        result = subprocess.run(
            [claude_path, "-p", "respond with: ready", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False
