import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bhf_agent import translation_settings


class ReaderTranslationSettingsTests(unittest.TestCase):
    def _load_from(self, payload, installed):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reader-settings.json"
            if payload is not None:
                path.write_text(payload, encoding="utf-8")
            with patch.object(translation_settings, "SETTINGS_PATH", path), patch.object(
                translation_settings,
                "is_translation_installed",
                side_effect=lambda translation_id: translation_id in installed,
            ):
                return translation_settings.load_reader_settings(), path

    def test_no_preference_uses_kjv(self):
        settings, path = self._load_from(None, {"kjv", "asv"})

        self.assertEqual(settings, {"default_translation": "kjv"})
        self.assertFalse(path.exists())

    def test_invalid_or_uninstalled_preference_falls_back_to_kjv(self):
        for payload in (
            json.dumps({"default_translation": "not-installed"}),
            "not valid json",
        ):
            with self.subTest(payload=payload):
                settings, _path = self._load_from(payload, {"kjv", "asv"})
                self.assertEqual(settings["default_translation"], "kjv")

    def test_existing_valid_asv_preference_is_preserved(self):
        settings, _path = self._load_from(
            json.dumps({"default_translation": "ASV"}),
            {"kjv", "asv"},
        )

        self.assertEqual(settings["default_translation"], "asv")

    def test_existing_valid_imported_preference_is_preserved(self):
        settings, _path = self._load_from(
            json.dumps({"default_translation": "study-english"}),
            {"kjv", "asv", "study-english"},
        )

        self.assertEqual(settings["default_translation"], "study-english")


if __name__ == "__main__":
    unittest.main()
