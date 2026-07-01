"""Local JSON session memory for BHF Agent continuity."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GenreContext, QuestionContext, ReferenceContext


DEFAULT_SESSION_ID = "default"
DEFAULT_MEMORY_DIR = Path(".bhf") / "sessions"
SUMMARY_LIMIT = 360


@dataclass(frozen=True)
class SessionTurn:
    question: str
    answer_summary: str
    reference_context: dict[str, Any]
    genre_context: dict[str, Any]
    question_type: str
    profile: str
    answer_mode: str
    timestamp: str


@dataclass
class SessionMemory:
    session_id: str
    turns: list[SessionTurn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": [asdict(turn) for turn in self.turns],
        }


def sanitize_session_id(session_id: str | None) -> str:
    candidate = (session_id or DEFAULT_SESSION_ID).strip()
    if not candidate:
        candidate = DEFAULT_SESSION_ID
    if candidate in {".", ".."}:
        raise ValueError("unsafe session_id")
    if "/" in candidate or "\\" in candidate:
        raise ValueError("unsafe session_id")
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "-", candidate)
    if sanitized in {".", "..", ""}:
        raise ValueError("unsafe session_id")
    return sanitized


def session_file_path(
    memory_path: str | None = None,
    session_id: str | None = None,
) -> Path:
    base = Path(memory_path) if memory_path else DEFAULT_MEMORY_DIR
    safe_id = sanitize_session_id(session_id)
    path = base / f"{safe_id}.json"
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    if resolved_base != resolved_path.parent:
        raise ValueError("unsafe session_id")
    return path


def load_session_memory(
    memory_path: str | None,
    session_id: str | None,
    max_turns: int,
) -> tuple[SessionMemory, list[str]]:
    safe_id = sanitize_session_id(session_id)
    path = session_file_path(memory_path, safe_id)
    if not path.exists():
        return SessionMemory(session_id=safe_id), []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        turns = [
            _turn_from_mapping(item)
            for item in data.get("turns", [])
            if isinstance(item, dict)
        ]
        return SessionMemory(session_id=safe_id, turns=turns[-max_turns:]), []
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return (
            SessionMemory(session_id=safe_id),
            [f"Memory file could not be read and was ignored: {exc}"],
        )


def save_session_memory(
    memory: SessionMemory,
    memory_path: str | None,
    max_turns: int,
) -> Path:
    path = session_file_path(memory_path, memory.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    memory.turns = memory.turns[-max_turns:]
    path.write_text(
        json.dumps(memory.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def append_session_turn(
    memory: SessionMemory,
    question: str,
    answer_text: str,
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question_context: QuestionContext,
    profile: str,
    answer_mode: str,
    max_turns: int,
) -> SessionMemory:
    memory.turns.append(
        SessionTurn(
            question=" ".join(question.strip().split()),
            answer_summary=summarize_answer(answer_text),
            reference_context=reference_context.to_dict(),
            genre_context=genre_context.to_dict(),
            question_type=question_context.question_type,
            profile=profile,
            answer_mode=answer_mode,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    memory.turns = memory.turns[-max_turns:]
    return memory


def summarize_answer(answer_text: str) -> str:
    compact = " ".join(answer_text.strip().split())
    if len(compact) <= SUMMARY_LIMIT:
        return compact
    return compact[: SUMMARY_LIMIT - 3].rstrip() + "..."


def format_session_memory_for_prompt(memory: SessionMemory | None) -> str:
    if not memory or not memory.turns:
        return ""
    lines = [
        "# Local Session Memory",
        "",
        "The following is local session context from prior turns. Use it only to maintain continuity.",
        "Do not treat previous answers as authoritative if they conflict with the biblical text, BHF method, or current question.",
    ]
    for index, turn in enumerate(memory.turns, start=1):
        reference = _format_reference(turn.reference_context)
        genre = turn.genre_context.get("primary_genre") or "not detected"
        lines.extend(
            [
                "",
                f"- Prior turn {index}",
                f"  - Question: {turn.question}",
                f"  - Summary: {turn.answer_summary}",
                f"  - Reference: {reference}",
                f"  - Genre: {genre}",
                f"  - Question type: {turn.question_type}",
                f"  - Profile: {turn.profile}",
                f"  - Answer mode: {turn.answer_mode}",
            ]
        )
    return "\n".join(lines)


def _turn_from_mapping(data: dict[str, Any]) -> SessionTurn:
    return SessionTurn(
        question=str(data.get("question", "")),
        answer_summary=str(data.get("answer_summary", "")),
        reference_context=dict(data.get("reference_context", {})),
        genre_context=dict(data.get("genre_context", {})),
        question_type=str(data.get("question_type", "")),
        profile=str(data.get("profile", "")),
        answer_mode=str(data.get("answer_mode", "")),
        timestamp=str(data.get("timestamp", "")),
    )


def _format_reference(reference: dict[str, Any]) -> str:
    if not reference.get("is_reference_based"):
        return f"topic-only ({reference.get('topic') or 'not detected'})"
    location = str(reference.get("book") or "unknown")
    if reference.get("chapter") is not None:
        location += f" {reference['chapter']}"
    if reference.get("verse") is not None:
        location += f":{reference['verse']}"
    return location
