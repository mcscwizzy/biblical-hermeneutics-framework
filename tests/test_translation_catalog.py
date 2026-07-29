import unittest

from bhf_agent.bible import load_kjv_bible
from bhf_agent.translation_catalog import (
    LICENSE_REQUIRED_EXPLANATION,
    PROTECTED_TRANSLATION_IDS,
    beblia_download_allowed,
    curated_english_catalog,
    github_download_allowed,
    github_download_metadata,
    import_translation,
    provider_access,
    resolve_selectable_translation,
    set_default_translation,
    translation_provider_access,
    translation_selector_sections,
)


class TranslationCatalogTests(unittest.TestCase):
    def test_only_eight_approved_english_catalog_entries_appear(self):
        catalog = curated_english_catalog(
            discovered_files=[
                "EnglishNIVBible.xml",
                "EnglishESVBible.xml",
                "EnglishNASBBible.xml",
                "SomeEnglishLookingFile.xml",
            ]
        )

        self.assertEqual(
            [entry["id"] for entry in catalog],
            ["asv", "kjv", "niv", "esv", "csb", "nasb", "lsb", "nlt"],
        )

    def test_asv_and_kjv_are_bundled(self):
        catalog = {entry["id"]: entry for entry in curated_english_catalog()}

        self.assertTrue(catalog["asv"]["bundled"])
        self.assertEqual(catalog["asv"]["availability"], "bundled")
        self.assertFalse(catalog["asv"]["download_enabled"])
        self.assertTrue(catalog["kjv"]["bundled"])
        self.assertEqual(catalog["kjv"]["availability"], "bundled")
        self.assertFalse(catalog["kjv"]["download_enabled"])
        self.assertFalse(github_download_allowed("kjv"))

    def test_kjv_is_present_in_the_selector_without_installation(self):
        sections = translation_selector_sections(installed_translation_ids=["asv"])

        installed = sections["sections"]["installed"]
        self.assertEqual([entry["id"] for entry in installed], ["asv", "kjv"])
        self.assertTrue(next(entry for entry in installed if entry["id"] == "kjv")["can_select"])

    def test_kjv_github_download_metadata_is_not_exposed_for_bundled_data(self):
        metadata = github_download_metadata("kjv")

        self.assertIsNone(metadata)

    def test_protected_translation_downloads_are_disabled(self):
        catalog = {entry["id"]: entry for entry in curated_english_catalog()}

        for translation_id in PROTECTED_TRANSLATION_IDS:
            with self.subTest(translation_id=translation_id):
                self.assertEqual(catalog[translation_id]["availability"], "license_required")
                self.assertFalse(catalog[translation_id]["download_enabled"])
                self.assertFalse(beblia_download_allowed(translation_id))
                self.assertFalse(github_download_allowed(translation_id))
                self.assertIsNone(github_download_metadata(translation_id))

    def test_protected_translations_display_license_required_explanation(self):
        sections = translation_selector_sections()
        protected = sections["sections"]["additional_english_translations"]

        self.assertEqual([entry["id"] for entry in protected], list(PROTECTED_TRANSLATION_IDS))
        for entry in protected:
            self.assertEqual(entry["license_explanation"], LICENSE_REQUIRED_EXPLANATION)
            self.assertIn("License required", entry["status_label"])

    def test_filename_discovery_does_not_add_catalog_entries(self):
        catalog = curated_english_catalog(discovered_files=["EnglishWEBBible.xml", "EnglishYLTBible.xml"])

        self.assertNotIn("web", [entry["id"] for entry in catalog])
        self.assertNotIn("ylt", [entry["id"] for entry in catalog])

    def test_no_protected_translation_is_downloaded_from_beblia(self):
        for translation_id in PROTECTED_TRANSLATION_IDS:
            self.assertFalse(beblia_download_allowed(translation_id))

    def test_kjv_dataset_is_available_as_a_built_in_translation(self):
        kjv = load_kjv_bible()

        self.assertEqual(kjv["translation"]["id"], "KJV")
        self.assertEqual(len(kjv["books"]), 66)

    def test_user_imported_translations_remain_private_and_local(self):
        imported = import_translation(
            "esv",
            confirmed=True,
            source_filename="legally-obtained-esv.xml",
        )

        self.assertTrue(imported["private"])
        self.assertTrue(imported["restrictions"]["local_only"])
        self.assertFalse(imported["restrictions"]["upload_to_bhf"])
        self.assertFalse(imported["restrictions"]["redistribute_to_users"])
        self.assertFalse(imported["restrictions"]["generate_public_download_link"])

    def test_protected_import_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(ValueError, "obtained the file lawfully"):
            import_translation("niv", confirmed=False, source_filename="niv.xml")

    def test_imported_protected_translations_never_enter_shared_catalog(self):
        imported = import_translation("nlt", confirmed=True, source_filename="nlt.xml")
        catalog_ids = [entry["id"] for entry in curated_english_catalog()]

        self.assertFalse(imported["add_to_shared_catalog"])
        self.assertIn("nlt", catalog_ids)
        self.assertEqual(len(catalog_ids), 8)

    def test_only_installed_translation_can_be_selected_or_defaulted(self):
        self.assertEqual(set_default_translation("kjv", ["asv", "kjv"]), "kjv")
        with self.assertRaisesRegex(ValueError, "Only an installed translation"):
            set_default_translation("esv", ["asv"])

    def test_asv_remains_fallback_when_translation_unavailable(self):
        self.assertEqual(resolve_selectable_translation("esv", ["asv"]), "asv")
        self.assertEqual(resolve_selectable_translation("kjv", ["asv", "kjv"]), "kjv")

    def test_provider_capabilities_default_to_false(self):
        provider = provider_access(
            {
                "provider_id": "example",
                "supports_streaming": True,
                "requires_api_key": True,
                "licensed_translation_ids": ["esv"],
            }
        )

        self.assertTrue(provider["supports_streaming"])
        self.assertTrue(provider["requires_api_key"])
        self.assertFalse(provider["can_display"])
        self.assertFalse(provider["can_store_offline"])

    def test_provider_streaming_does_not_grant_offline_storage(self):
        access = translation_provider_access(
            "esv",
            {
                "provider_id": "licensed_esv_provider",
                "supports_streaming": True,
                "supports_offline_storage": False,
                "licensed_translation_ids": ["esv"],
                "can_display": True,
                "can_search": True,
                "can_quote": True,
            },
            {
                "read_online": True,
                "download_offline": True,
                "full_text_search": True,
                "copy_limit": 500,
            },
        )

        self.assertTrue(access["read_online"])
        self.assertTrue(access["full_text_search"])
        self.assertFalse(access["download_offline"])
        self.assertFalse(access["can_store_offline"])
        self.assertTrue(access["online_access_required"])


if __name__ == "__main__":
    unittest.main()
