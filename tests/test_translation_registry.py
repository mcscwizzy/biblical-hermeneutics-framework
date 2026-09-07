import tempfile
import unittest
from pathlib import Path

from bhf_agent.translation_registry import (
    default_translation_id,
    initialize_registry,
    list_translations,
    set_default_translation,
)


class TranslationRegistryDefaultTests(unittest.TestCase):
    def test_fresh_registry_seeds_kjv_as_default_and_keeps_asv_selectable(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "translations.sqlite"
            initialize_registry(path)
            rows = list_translations(path=path)
            self.assertEqual(default_translation_id(path), "kjv")
            self.assertEqual({row["id"] for row in rows}, {"asv", "kjv"})
            self.assertTrue(next(row for row in rows if row["id"] == "kjv")["default"])
            self.assertFalse(next(row for row in rows if row["id"] == "asv")["default"])

    def test_existing_registry_default_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "translations.sqlite"
            initialize_registry(path)
            set_default_translation("asv", path=path)
            initialize_registry(path)

            self.assertEqual(default_translation_id(path), "asv")


if __name__ == "__main__":
    unittest.main()
