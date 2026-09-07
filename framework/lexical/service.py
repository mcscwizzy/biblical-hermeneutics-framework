"""Small lookup and prompt-formatting API for the lexical engine."""

from __future__ import annotations

import os
import re
import logging
import gzip
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .models import LexicalEntry
from .repository import LexicalRepository


DEFAULT_LEXICAL_DATABASE_PATH = str(Path(__file__).resolve().parent / "database" / "lexicon.sqlite")
PACKAGED_LEXICAL_DATABASE_ARCHIVE_PATH = Path(f"{DEFAULT_LEXICAL_DATABASE_PATH}.gz")
_STRONGS_RE = re.compile(r"\b(?P<value>[HG]\s*0*\d{1,5}[A-Za-z]?)\b", re.IGNORECASE)
LOGGER = logging.getLogger(__name__)


def bundled_lexical_database_path() -> Path:
    """Return the packaged database, materializing its compressed copy if needed.

    Vercel functions can read packaged source files but may only write to ``/tmp``.
    The generated database is therefore shipped compressed and expanded atomically
    into the deployment's writable runtime directory on first use.
    """

    packaged_path = Path(DEFAULT_LEXICAL_DATABASE_PATH)
    if packaged_path.is_file():
        return packaged_path

    archive_path = PACKAGED_LEXICAL_DATABASE_ARCHIVE_PATH
    if not archive_path.is_file():
        return packaged_path

    runtime_dir = Path(
        os.environ.get("BHF_DATA_DIR")
        or ("/tmp/bhf-data" if os.environ.get("VERCEL") else ".bhf-data")
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = runtime_dir / packaged_path.name
    if runtime_path.is_file():
        return runtime_path

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".lexicon.", suffix=".sqlite", dir=runtime_dir, delete=False
        ) as temporary:
            temporary_path = temporary.name
            with gzip.open(archive_path, "rb") as source:
                shutil.copyfileobj(source, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, runtime_path)
    except Exception:
        if temporary_path:
            try:
                Path(temporary_path).unlink()
            except FileNotFoundError:
                pass
        raise
    return runtime_path


def lexical_database_build_command(database_path: str | Path = DEFAULT_LEXICAL_DATABASE_PATH) -> str:
    """Return the canonical local build command for the runtime database."""

    return (
        "python -m framework.lexical.tools.build_lexicon_database "
        "--hebrew <path-to-open-scriptures-hebrew-xml> "
        "--greek <path-to-open-scriptures-greek-xml> "
        f"--output {Path(database_path)}"
    )


def lexical_database_missing_message(database_path: str | Path = DEFAULT_LEXICAL_DATABASE_PATH) -> str:
    """Return a clear remediation message for a missing runtime database."""

    path = Path(database_path)
    return (
        f"Lexical SQLite database not found at {path}. "
        "Word Study lexical definitions are unavailable until Open Scriptures "
        "sources are imported. Build it with: "
        f"{lexical_database_build_command(path)}"
    )


def format_lexical_unavailable_context(database_path: str | Path) -> str:
    """Prompt guardrail used when a word-study request has no runtime database."""

    return "\n".join(
        [
            "# LEXICAL DATA UNAVAILABLE",
            lexical_database_missing_message(database_path),
            "Do not provide Hebrew/Greek definitions, Strong's numbers, or lexical range from model memory.",
            "Tell the user the deterministic lexical database must be built before Word Study can answer from source data.",
        ]
    )


class LexicalLookupService:
    """Application-facing lexical retrieval with bounded prompt output."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: LexicalRepository | None = None,
    ) -> None:
        self.database_path = Path(
            database_path
            or os.environ.get("BHF_LEXICAL_DATABASE_PATH")
            or bundled_lexical_database_path()
        )
        self._repository = repository
        self.startup_diagnostics = self._log_startup_diagnostics()

    @property
    def repository(self) -> LexicalRepository:
        if self._repository is None:
            self._repository = LexicalRepository(self.database_path)
        return self._repository

    def close(self) -> None:
        if self._repository is not None:
            self._repository.close()

    def diagnostics(self) -> dict[str, Any]:
        """Return non-fatal startup diagnostics for the configured database."""

        diagnostics: dict[str, Any] = {
            "path": str(self.database_path),
            "lexical_database_found": self.database_path.is_file(),
            "lexical_entry_count": 0,
            "hebrew_entries": 0,
            "greek_entries": 0,
            "build_command": lexical_database_build_command(self.database_path),
        }
        if not diagnostics["lexical_database_found"]:
            diagnostics["message"] = lexical_database_missing_message(self.database_path)
            return diagnostics
        try:
            counts = self.repository.counts_by_language()
            diagnostics["lexical_entry_count"] = self.repository.count()
            diagnostics["hebrew_entries"] = counts.get("hebrew", 0)
            diagnostics["greek_entries"] = counts.get("greek", 0)
        except (OSError, sqlite3.Error, ValueError) as exc:
            diagnostics["error"] = str(exc)
        return diagnostics

    def _log_startup_diagnostics(self) -> dict[str, Any]:
        diagnostics = self.diagnostics()
        LOGGER.info(
            "lexical database found=%s path=%s lexical entry count=%d Hebrew entries=%d Greek entries=%d",
            diagnostics["lexical_database_found"],
            diagnostics["path"],
            diagnostics["lexical_entry_count"],
            diagnostics["hebrew_entries"],
            diagnostics["greek_entries"],
        )
        if not diagnostics["lexical_database_found"]:
            LOGGER.warning("%s", diagnostics["message"])
        if diagnostics.get("error"):
            LOGGER.warning("lexical database diagnostics unavailable: %s", diagnostics["error"])
        return diagnostics

    def lookup(
        self,
        *,
        language: str,
        strongs: str | None = None,
        lemma: str | None = None,
        transliteration: str | None = None,
    ) -> list[LexicalEntry]:
        language = str(language or "").strip().lower()
        if language not in {"hebrew", "greek", "aramaic"}:
            return []
        if strongs:
            results = self.repository.lookup_by_strongs(language, strongs)
            if results:
                return results
        if lemma:
            results = self.repository.lookup_by_lemma(language, lemma)
            if results:
                return results
        if transliteration:
            return self.repository.lookup_by_transliteration(language, transliteration)
        return []

    def lookup_question(
        self,
        *,
        language: str | None,
        terms: Iterable[str] = (),
        question: str = "",
        max_results: int = 3,
        max_prompt_tokens: int = 350,
    ) -> tuple[list[LexicalEntry], str]:
        """Resolve only explicit original-language targets in a question."""

        normalized_language = str(language or "").strip().lower()
        if normalized_language not in {"hebrew", "greek"}:
            normalized_language = ""
        candidates: list[LexicalEntry] = []
        seen: set[tuple[str, str, str]] = set()
        strongs_numbers = [match.group("value") for match in _STRONGS_RE.finditer(question or "")]
        for strongs_number in strongs_numbers:
            current_language = normalized_language or (
                "hebrew" if strongs_number.upper().startswith("H") else "greek"
            )
            for entry in self.lookup(language=current_language, strongs=strongs_number):
                _append_unique(candidates, seen, entry)
        if normalized_language:
            for term in terms:
                for entry in self.lookup(
                    language=normalized_language,
                    lemma=term,
                    transliteration=term,
                ):
                    _append_unique(candidates, seen, entry)
        candidates = candidates[: max(0, int(max_results))]
        return candidates, format_lexical_context(candidates, max_prompt_tokens=max_prompt_tokens)


def lookup_word(
    *,
    language: str,
    strongs: str | None = None,
    lemma: str | None = None,
    transliteration: str | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Return one compact lexical record for an exact lookup."""

    service = LexicalLookupService(database_path)
    try:
        entries = service.lookup(
            language=language,
            strongs=strongs,
            lemma=lemma,
            transliteration=transliteration,
        )
        if not entries:
            return None
        return entries[0].to_dict()
    finally:
        service.close()


def format_lexical_context(entries: Iterable[LexicalEntry], *, max_prompt_tokens: int = 350) -> str:
    selected = list(entries)
    if not selected:
        return ""
    lines = [
        "# VERIFIED LEXICAL CONTEXT",
        "Use the supplied lexical records as source data. Explain contextually; do not invent or expand lexical definitions from memory.",
    ]
    for entry in selected:
        lines.extend(["", f"Word: {entry.lemma}", f"Language: {entry.language}"])
        if entry.transliteration:
            lines.append(f"Transliteration: {entry.transliteration}")
        if entry.strongs_number:
            lines.append(f"Strong's: {entry.strongs_number}")
        lines.append(f"Source: {entry.source}; License: {entry.license}")
        lines.append(f"Definition: {entry.short_definition or entry.definition}")
        if entry.morphology:
            lines.append(f"Morphology: {entry.morphology}")
        if entry.usage_notes:
            lines.append(f"Usage notes: {entry.usage_notes}")
    words = "\n".join(lines).split()
    if len(words) > max(1, int(max_prompt_tokens)):
        return " ".join(words[: int(max_prompt_tokens)]).rstrip() + " ..."
    return "\n".join(lines)


def _append_unique(
    entries: list[LexicalEntry],
    seen: set[tuple[str, str, str]],
    entry: LexicalEntry,
) -> None:
    key = (entry.language, entry.strongs_number or "", entry.lemma)
    if key not in seen:
        seen.add(key)
        entries.append(entry)
