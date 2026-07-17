"""Persisted reader settings for translation defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .translation_storage import normalize_translation_id, write_json_atomic
from .translation_installer import get_translation_installation


DEFAULT_READER_TRANSLATION_ID = "asv"
SETTINGS_PATH = Path(os.environ.get("BHF_READER_SETTINGS_PATH", ".bhf/reader-settings.json"))


def load_reader_settings() -> dict[str, Any]:
    default_translation = DEFAULT_READER_TRANSLATION_ID
    try:
        raw = SETTINGS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"default_translation": default_translation}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"default_translation": default_translation}
    requested = str(payload.get("default_translation") or DEFAULT_READER_TRANSLATION_ID)
    try:
        normalized = normalize_translation_id(requested)
    except ValueError:
        normalized = DEFAULT_READER_TRANSLATION_ID
    if not is_translation_installed(normalized):
        normalized = DEFAULT_READER_TRANSLATION_ID
    return {"default_translation": normalized}


def save_reader_settings(settings: dict[str, Any]) -> dict[str, Any]:
    default_translation = str(settings.get("default_translation") or DEFAULT_READER_TRANSLATION_ID)
    normalized = normalize_translation_id(default_translation)
    if not is_translation_installed(normalized):
        raise ValueError("Only an installed translation can be set as default")
    payload = {"default_translation": normalized}
    write_json_atomic(SETTINGS_PATH, payload)
    return payload


def get_default_reader_translation() -> str:
    return str(load_reader_settings().get("default_translation") or DEFAULT_READER_TRANSLATION_ID)


def set_default_reader_translation(translation_id: str) -> str:
    normalized = normalize_translation_id(translation_id)
    if not is_translation_installed(normalized):
        raise ValueError("Only an installed translation can be set as default")
    save_reader_settings({"default_translation": normalized})
    return normalized


def is_translation_installed(translation_id: str) -> bool:
    normalized = normalize_translation_id(translation_id)
    if normalized == DEFAULT_READER_TRANSLATION_ID:
        return True
    installation = get_translation_installation(normalized)
    return bool(installation.get("installed"))

