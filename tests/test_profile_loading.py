import tempfile
import unittest
from pathlib import Path

from bhf_agent.profiles import ProfileError, ProfileLoader


class ProfileLoadingTests(unittest.TestCase):
    def test_loads_existing_repo_profiles(self):
        loader = ProfileLoader()

        profile = loader.load("minimal-7b")

        self.assertEqual(profile.name, "minimal-7b")
        self.assertIn("Biblical Hermeneutics Framework", profile.content)

    def test_available_profiles_include_required_profiles(self):
        profiles = ProfileLoader().available_profiles()

        self.assertIn("minimal-7b", profiles)
        self.assertIn("standard", profiles)
        self.assertIn("scholar", profiles)

    def test_missing_profile_error_lists_available_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp)
            (profiles_dir / "standard.md").write_text("standard", encoding="utf-8")
            loader = ProfileLoader(profiles_dir)

            with self.assertRaisesRegex(ProfileError, "Available: standard"):
                loader.load("missing")


if __name__ == "__main__":
    unittest.main()
