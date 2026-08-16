from __future__ import annotations

import contextlib
import io
import json
import unittest
from importlib import metadata
from pathlib import Path
from unittest.mock import patch

from framework.canonical_library import __version__ as canonical_library_version
from framework.canonical_library.__main__ import main
from framework.canonical_library.public_cache import load_framework_version


class CanonicalReleaseTests(unittest.TestCase):
    def test_load_framework_version_prefers_installed_distribution_metadata(self) -> None:
        with patch(
            "framework.canonical_library.public_cache.metadata.version",
            return_value="9.9.9",
        ):
            self.assertEqual(load_framework_version(), "9.9.9")

    def test_load_framework_version_falls_back_to_checkout_version_file(self) -> None:
        version_path = Path(__file__).resolve().parents[2] / "VERSION"
        with patch(
            "framework.canonical_library.public_cache.metadata.version",
            side_effect=metadata.PackageNotFoundError,
        ):
            self.assertEqual(
                load_framework_version(),
                version_path.read_text(encoding="utf-8").strip(),
            )

    def test_package_version_exports_track_framework_version(self) -> None:
        self.assertEqual(canonical_library_version, load_framework_version())

    def test_ckl_version_cli_reports_release_metadata(self) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--json"])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["distribution_name"],
            "biblical-hermeneutics-framework",
        )
        self.assertEqual(payload["framework_version"], load_framework_version())
        self.assertEqual(payload["ckl_manifest_framework_version"], "1.0")
        self.assertEqual(payload["ckl_manifest_schema_version"], "1.0")
        self.assertEqual(payload["ckl_object_count"], 635)
        self.assertIn("ckl_inventory_fingerprint", payload)


if __name__ == "__main__":
    unittest.main()
