"""Capture redacted Docker Compose startup diagnostics for GUI CI failures."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    "docker",
    "compose",
    "-f",
    "docker-compose.yml",
    "-f",
    "docker-compose.selenium.yml",
]
MAX_CONSOLE_CHARS = 120_000

_BHF_SETTING = re.compile(
    r"(?i)(\bBHF_[A-Z0-9_]+[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)"
)
_BEARER = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]+=*")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:access[_-]?token|api[_-]?key|authorization|client[_-]?(?:id|secret)|credential|database[_-]?url|password|private[_-]?key|redirect[_-]?uri|secret|token)\b[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)"
)
_URL_CREDENTIALS = re.compile(r"(?i)(https?://[^/:\s]+:)[^@/\s]+(@)")
_QUERY_CREDENTIAL = re.compile(r"(?i)([?&](?:access[_-]?token|api[_-]?key|password|secret|token)=)[^&#\s]+")


def redact_sensitive_output(value: str) -> str:
    """Remove runtime setting values and common credential forms from logs."""

    redacted = _BEARER.sub(r"\1[REDACTED]", str(value))
    redacted = _BHF_SETTING.sub(r"\1[REDACTED]", redacted)
    redacted = _SENSITIVE_ASSIGNMENT.sub(r"\1[REDACTED]", redacted)
    redacted = _URL_CREDENTIALS.sub(r"\1[REDACTED]\2", redacted)
    return _QUERY_CREDENTIAL.sub(r"\1[REDACTED]", redacted)


def _run(command: Sequence[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}\n"
    return result.returncode, f"{result.stdout}{result.stderr}"


def _record(artifact_dir: Path, name: str, command: Sequence[str]) -> None:
    exit_code, output = _run(command)
    safe_output = redact_sensitive_output(output)
    content = f"Command: {' '.join(command)}\nExit code: {exit_code}\n{safe_output}"
    artifact_path = artifact_dir / name
    artifact_path.write_text(content, encoding="utf-8")
    artifact_path.chmod(0o600)

    console_output = content
    if len(console_output) > MAX_CONSOLE_CHARS:
        console_output = "[earlier diagnostic output truncated]\n" + console_output[-MAX_CONSOLE_CHARS:]
    print(f"--- {name} ---", flush=True)
    print(console_output, end="" if console_output.endswith("\n") else "\n", flush=True)


def capture(artifact_dir: Path | None = None) -> None:
    """Capture compose state, application logs, and health-check output."""

    output_dir = artifact_dir or Path(
        os.environ.get("BHF_GUI_ARTIFACTS_DIR", REPOSITORY_ROOT / "tests/gui/artifacts")
    )
    if not output_dir.is_absolute():
        output_dir = REPOSITORY_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    _record(output_dir, "docker-compose-ps.txt", [*COMPOSE, "ps", "-a"])
    _record(output_dir, "bhf-web.log", [*COMPOSE, "logs", "--no-color", "bhf-web"])

    _record(
        output_dir,
        "docker-health.txt",
        [
            "docker",
            "inspect",
            "--format",
            "{{.Name}} status={{.State.Status}} exit_code={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} error={{.State.Error}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{if .State.Health}}{{range .State.Health.Log}}{{printf \"health_start=%s health_exit=%d health_output=%s\\n\" .Start .ExitCode .Output}}{{end}}{{end}}",
            *filter(None, _run([*COMPOSE, "ps", "-aq"])[1].splitlines()),
        ],
    )


if __name__ == "__main__":
    capture()
