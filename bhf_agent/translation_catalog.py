"""Curated Bible translation catalog and licensing rules."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable


DEFAULT_TRANSLATION_ID = "asv"
PROTECTED_TRANSLATION_IDS = ("niv", "esv", "csb", "nasb", "lsb", "nlt")
LICENSE_REQUIRED_EXPLANATION = (
    "This translation is copyrighted and is not currently available for direct "
    "download through BHF. Support may be added through an authorized provider "
    "or publisher agreement."
)
PROTECTED_IMPORT_NOTICE = (
    "This translation appears to be copyrighted. By importing it, you confirm "
    "that you obtained the file lawfully and have the right to use it on this "
    "device. BHF does not provide, distribute, or verify this file."
)
THIRD_PARTY_GITHUB_NOTICE = (
    "This translation is downloaded from a third-party GitHub repository. BHF "
    "does not maintain that repository or guarantee the translation's identity, "
    "completeness, accuracy, or licensing. Verify the source before relying on it."
)
PROTECTED_TRANSLATION_ACTIONS = (
    "Learn more",
    "Import legally obtained XML",
    "Configure licensed provider",
)
PRIVATE_IMPORT_RESTRICTIONS = {
    "local_only": True,
    "upload_to_bhf": False,
    "redistribute_to_users": False,
    "commit_to_repository": False,
    "include_in_public_backups": False,
    "add_to_remote_catalog": False,
    "generate_public_download_link": False,
}

CURATED_ENGLISH_TRANSLATION_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "asv",
        "name": "American Standard Version",
        "abbreviation": "ASV",
        "language": "English",
        "language_code": "en",
        "bundled": True,
        "availability": "bundled",
        "download_enabled": False,
        "license_status": "public_domain_us",
        "install_mode": "bundled",
        "third_party": False,
        "source": None,
        "validation": {
            "expected_book_count": 66,
            "expected_minimum_verse_count": 31103,
            "expected_maximum_verse_count": 31103,
        },
    },
    {
        "id": "kjv",
        "name": "King James Version",
        "abbreviation": "KJV",
        "language": "English",
        "language_code": "en",
        "bundled": True,
        "availability": "bundled",
        "download_enabled": False,
        "license_status": "public_domain_us",
        "install_mode": "bundled",
        "third_party": False,
        "source": {
            "provider_id": "beblia_github",
            "provider_name": "Beblia GitHub repository",
            "repository_url": "https://github.com/Beblia/Holy-Bible-XML-Format",
            "raw_url": (
                "https://raw.githubusercontent.com/Beblia/Holy-Bible-XML-Format/master/"
                "EnglishKJBible.xml"
            ),
            "filename": "EnglishKJBible.xml",
        },
        "validation": {
            "expected_book_count": 66,
            "expected_minimum_verse_count": 31000,
            "expected_maximum_verse_count": 31200,
        },
    },
    {
        "id": "niv",
        "name": "New International Version",
        "abbreviation": "NIV",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
    {
        "id": "esv",
        "name": "English Standard Version",
        "abbreviation": "ESV",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
    {
        "id": "csb",
        "name": "Christian Standard Bible",
        "abbreviation": "CSB",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
    {
        "id": "nasb",
        "name": "New American Standard Bible",
        "abbreviation": "NASB",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
    {
        "id": "lsb",
        "name": "Legacy Standard Bible",
        "abbreviation": "LSB",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
    {
        "id": "nlt",
        "name": "New Living Translation",
        "abbreviation": "NLT",
        "language": "English",
        "language_code": "en",
        "bundled": False,
        "availability": "license_required",
        "download_enabled": False,
        "license_status": "copyrighted",
        "install_mode": "licensed_provider",
        "third_party": True,
        "source": None,
        "validation": {
            "expected_book_count": 66,
        },
    },
)

AVAILABILITY_STATES = (
    "bundled",
    "installed",
    "direct_download",
    "manual_import",
    "licensed_provider",
    "unavailable",
)


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    supports_streaming: bool = False
    supports_offline_storage: bool = False
    requires_api_key: bool = False
    requires_user_account: bool = False
    licensed_translation_ids: tuple[str, ...] = ()
    can_display: bool = False
    can_search: bool = False
    can_cache_temporarily: bool = False
    can_store_offline: bool = False
    can_export: bool = False
    can_quote: bool = False

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ProviderCapabilities":
        return cls(
            provider_id=str(config.get("provider_id") or "").strip(),
            supports_streaming=bool(config.get("supports_streaming", False)),
            supports_offline_storage=bool(config.get("supports_offline_storage", False)),
            requires_api_key=bool(config.get("requires_api_key", False)),
            requires_user_account=bool(config.get("requires_user_account", False)),
            licensed_translation_ids=tuple(
                str(item).lower()
                for item in config.get("licensed_translation_ids", ())
                if str(item).strip()
            ),
            can_display=bool(config.get("can_display", False)),
            can_search=bool(config.get("can_search", False)),
            can_cache_temporarily=bool(config.get("can_cache_temporarily", False)),
            can_store_offline=bool(config.get("can_store_offline", False)),
            can_export=bool(config.get("can_export", False)),
            can_quote=bool(config.get("can_quote", False)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "supports_streaming": self.supports_streaming,
            "supports_offline_storage": self.supports_offline_storage,
            "requires_api_key": self.requires_api_key,
            "requires_user_account": self.requires_user_account,
            "licensed_translation_ids": list(self.licensed_translation_ids),
            "can_display": self.can_display,
            "can_search": self.can_search,
            "can_cache_temporarily": self.can_cache_temporarily,
            "can_store_offline": self.can_store_offline,
            "can_export": self.can_export,
            "can_quote": self.can_quote,
        }


def curated_english_catalog(*, discovered_files: list[str] | None = None) -> list[dict[str, Any]]:
    """Return only the reviewed English catalog entries.

    ``discovered_files`` is intentionally ignored so a repository tree scan cannot
    make a translation visible or downloadable without a reviewed catalog entry.
    """

    return deepcopy(list(CURATED_ENGLISH_TRANSLATION_CATALOG))


def catalog_by_id() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in curated_english_catalog()}


def catalog_entry_for_id(translation_id: str) -> dict[str, Any] | None:
    return catalog_by_id().get(str(translation_id or "").strip().lower())


def approved_beblia_mapping(translation_id: str) -> dict[str, Any] | None:
    entry = catalog_entry_for_id(translation_id)
    if not entry or entry.get("install_mode") != "direct_download":
        return None
    source = dict(entry.get("source") or {})
    return {
        "translation_id": entry["id"],
        "provider_id": source.get("provider_id"),
        "provider_name": source.get("provider_name"),
        "repository_url": source.get("repository_url"),
        "approved_source_path": source.get("filename"),
        "approved_source_url": source.get("raw_url"),
        "expected_name": entry.get("name"),
        "expected_language": entry.get("language_code") or entry.get("language"),
        "expected_book_count": entry.get("validation", {}).get("expected_book_count"),
        "expected_minimum_verse_count": entry.get("validation", {}).get("expected_minimum_verse_count"),
        "expected_maximum_verse_count": entry.get("validation", {}).get("expected_maximum_verse_count"),
        "review_status": "approved",
        "license_status": entry.get("license_status"),
        "expected_verse_count": 31103,
        "versification_note": (
            "BHF accepts the standard 66-book Protestant canon for this source."
        ),
        "review_requirements": (
            "confirm_translation_identity",
            "confirm_complete_expected_canon",
            "inspect_metadata_and_verse_counts",
            "validate_sample_passages_against_trusted_kjv_source",
            "record_repository_commit_sha_and_checksum",
        ),
        "reference_checksum_sha256": (
            "07b1321a92fb1af3b26a8963ee70e667a3572d03e872a32f38c2f5d5f0beba1e"
        ),
        "reference_checksum_source": "bhf_agent/data/kjv_bible.json",
    }


def beblia_download_allowed(translation_id: str) -> bool:
    entry = catalog_entry_for_id(translation_id)
    mapping = approved_beblia_mapping(translation_id)
    return bool(
        entry
        and mapping
        and entry.get("install_mode") == "direct_download"
        and entry.get("license_status") == "public_domain_us"
    )


def github_download_allowed(translation_id: str) -> bool:
    return beblia_download_allowed(translation_id)


def github_download_metadata(translation_id: str) -> dict[str, Any] | None:
    translation_id = str(translation_id or "").strip().lower()
    if not github_download_allowed(translation_id):
        return None
    mapping = approved_beblia_mapping(translation_id)
    if mapping is None:
        return None
    return {
        "translation_id": translation_id,
        "provider_id": mapping["provider_id"],
        "provider_name": mapping["provider_name"],
        "source": "github",
        "source_type": "beblia_xml",
        "repository_url": mapping["repository_url"],
        "approved_source_path": mapping["approved_source_path"],
        "approved_source_url": mapping["approved_source_url"],
        "expected_name": mapping["expected_name"],
        "expected_language": mapping["expected_language"],
        "expected_book_count": mapping["expected_book_count"],
        "expected_minimum_verse_count": mapping["expected_minimum_verse_count"],
        "expected_maximum_verse_count": mapping["expected_maximum_verse_count"],
        "expected_verse_count": mapping["expected_verse_count"],
        "license_status": mapping["license_status"],
        "review_status": mapping["review_status"],
        "third_party": True,
        "supported_by_bhf": False,
        "third_party_notice": THIRD_PARTY_GITHUB_NOTICE,
        "versification_note": mapping["versification_note"],
    }


def translation_selector_sections(
    *,
    installed_translation_ids: list[str] | tuple[str, ...] = (DEFAULT_TRANSLATION_ID,),
    default_translation_id: str = DEFAULT_TRANSLATION_ID,
) -> dict[str, Any]:
    catalog = curated_english_catalog()
    by_id = {item["id"]: item for item in catalog}
    installed_ids = {
        str(item).lower()
        for item in installed_translation_ids
        if str(item).lower() in by_id
    }
    installed_ids.update(
        entry["id"] for entry in catalog if entry.get("bundled")
    )
    default_id = str(default_translation_id or DEFAULT_TRANSLATION_ID).lower()
    if default_id not in installed_ids:
        default_id = DEFAULT_TRANSLATION_ID

    installed: list[dict[str, Any]] = []
    available_to_download: list[dict[str, Any]] = []
    license_required: list[dict[str, Any]] = []

    for entry in catalog:
        item = deepcopy(entry)
        item["installed"] = entry["id"] in installed_ids
        item["selected"] = entry["id"] == default_id
        item["can_select"] = bool(item["installed"])
        item["can_set_default"] = bool(item["installed"])
        item["can_remove"] = bool(item["installed"] and not entry.get("bundled", False))
        item["can_download"] = False
        item["status_label"] = "Built in" if entry.get("bundled") else "Installed locally"

        if entry["id"] in installed_ids:
            installed.append(item)
            continue

        if entry.get("install_mode") == "direct_download":
            item["can_download"] = True
            item["status_label"] = "Download from GitHub"
            item["third_party_notice"] = THIRD_PARTY_GITHUB_NOTICE
            item["download_source"] = "beblia_xml"
            item["approved_source_url"] = (entry.get("source") or {}).get("raw_url")
            item["repository_url"] = (entry.get("source") or {}).get("repository_url")
            available_to_download.append(item)
            continue

        item["status_label"] = "License required"
        item["license_explanation"] = LICENSE_REQUIRED_EXPLANATION
        item["actions"] = list(PROTECTED_TRANSLATION_ACTIONS)
        license_required.append(item)

    return {
        "catalog": catalog,
        "availability_states": list(AVAILABILITY_STATES),
        "default_translation_id": default_id,
        "fallback_translation_id": DEFAULT_TRANSLATION_ID,
        "sections": {
            "installed": installed,
            "available_to_download": available_to_download,
            "license_required": license_required,
            "additional_english_translations": license_required,
        },
    }


def translation_provider_access(
    translation_id: str,
    provider_config: dict[str, Any],
    translation_config: dict[str, Any],
) -> dict[str, Any]:
    provider = ProviderCapabilities.from_config(provider_config)
    translation_id = str(translation_id or "").lower()
    licensed = translation_id in provider.licensed_translation_ids
    access = {
        "translation_id": translation_id,
        "read_online": bool(licensed and translation_config.get("read_online", False)),
        "download_offline": bool(
            licensed
            and translation_config.get("download_offline", False)
            and provider.can_store_offline
        ),
        "full_text_search": bool(
            licensed
            and translation_config.get("full_text_search", False)
            and provider.can_search
        ),
        "copy_limit": int(translation_config.get("copy_limit") or 0)
        if licensed and provider.can_quote
        else 0,
        "provider_id": provider.provider_id,
        "can_display": bool(licensed and provider.can_display),
        "can_search": bool(licensed and provider.can_search),
        "can_cache_temporarily": bool(licensed and provider.can_cache_temporarily),
        "can_store_offline": bool(licensed and provider.can_store_offline),
        "can_export": bool(licensed and provider.can_export),
        "can_quote": bool(licensed and provider.can_quote),
    }
    access["online_access_required"] = bool(access["read_online"] and not access["download_offline"])
    return access


def provider_access(config: dict[str, Any]) -> dict[str, Any]:
    provider = ProviderCapabilities.from_config(config)
    capabilities = provider.as_dict()
    capabilities["online_access_required"] = bool(
        provider.can_display and not provider.can_store_offline
    )
    return capabilities


def import_translation(
    translation_id: str,
    *,
    confirmed: bool,
    source_filename: str,
) -> dict[str, Any]:
    translation_id = str(translation_id or "").lower()
    entry = catalog_entry_for_id(translation_id)
    protected = bool(entry and entry.get("license_status") == "copyrighted")
    if protected and not confirmed:
        raise ValueError(PROTECTED_IMPORT_NOTICE)
    return {
        "translation_id": translation_id,
        "source_filename": source_filename,
        "availability": "installed",
        "origin": "manual_xml_import",
        "private": True,
        "protected": protected,
        "notice": PROTECTED_IMPORT_NOTICE if protected else "",
        "restrictions": dict(PRIVATE_IMPORT_RESTRICTIONS),
        "add_to_shared_catalog": False,
    }


def set_default_translation(
    requested_translation_id: str,
    installed_translation_ids: list[str] | tuple[str, ...],
) -> str:
    requested = str(requested_translation_id or "").lower()
    installed = {str(item).lower() for item in installed_translation_ids}
    installed.add(DEFAULT_TRANSLATION_ID)
    if requested not in installed:
        raise ValueError("Only an installed translation can be selected or made default")
    return requested


def resolve_selectable_translation(
    requested_translation_id: str | None,
    installed_translation_ids: list[str] | tuple[str, ...],
) -> str:
    installed = {str(item).lower() for item in installed_translation_ids}
    installed.add(DEFAULT_TRANSLATION_ID)
    requested = str(requested_translation_id or DEFAULT_TRANSLATION_ID).lower()
    if requested in installed:
        return requested
    return DEFAULT_TRANSLATION_ID


def validate_beblia_source_for_install(
    translation_id: str,
    bible_data: dict[str, Any],
    *,
    repository_commit_sha: str,
    checksum_sha256: str,
    sample_validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    translation_id = str(translation_id or "").lower()
    if not beblia_download_allowed(translation_id):
        raise ValueError(f"{translation_id} is not approved for Beblia download")
    mapping = approved_beblia_mapping(translation_id)
    assert mapping is not None
    if not repository_commit_sha.strip():
        raise ValueError("repository commit SHA is required before installation")
    if not checksum_sha256.strip():
        raise ValueError("source checksum is required before installation")

    translation = bible_data.get("translation", {})
    actual_name = str(translation.get("name") or "").strip()
    actual_id = str(translation.get("id") or translation_id).strip().lower()
    if actual_id != translation_id and mapping["expected_name"].lower() not in actual_name.lower():
        raise ValueError("source metadata does not identify the expected translation")
    if mapping["expected_name"].lower() not in actual_name.lower():
        raise ValueError("source name does not identify the expected translation")

    books = list(bible_data.get("books", []) or [])
    if len(books) != int(mapping["expected_book_count"] or 0):
        raise ValueError("source does not contain the complete expected canon")
    verse_count = sum(
        len(chapter.get("verses", []))
        for book in books
        for chapter in book.get("chapters", [])
    )
    if not (
        int(mapping["expected_minimum_verse_count"] or 0)
        <= verse_count
        <= int(mapping["expected_maximum_verse_count"] or verse_count)
    ):
        raise ValueError("source verse count is outside the approved review range")
    if sample_validator is None or not sample_validator(bible_data):
        raise ValueError("trusted KJV sample passage validation is required")

    return {
        "translation_id": translation_id,
        "approved_source_path": mapping["approved_source_path"],
        "repository_commit_sha": repository_commit_sha,
        "checksum_sha256": checksum_sha256,
        "book_count": len(books),
        "verse_count": verse_count,
        "validated": True,
        "validation_steps": list(mapping["review_requirements"]),
        "versification_note": mapping["versification_note"],
    }


def install_remote_translation(
    translation_id: str,
    bible_data: dict[str, Any],
    *,
    repository_commit_sha: str,
    checksum_sha256: str,
    sample_validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    validation = validate_beblia_source_for_install(
        translation_id,
        bible_data,
        repository_commit_sha=repository_commit_sha,
        checksum_sha256=checksum_sha256,
        sample_validator=sample_validator,
    )
    return {
        "translation_id": str(translation_id or "").lower(),
        "availability": "installed",
        "offline_supported": True,
        "private_local_install": True,
        "validation": validation,
    }
