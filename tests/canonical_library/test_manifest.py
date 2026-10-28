from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path, PurePosixPath

from bhf_agent.references import BOOKS
from framework.canonical_library import CATEGORY_FOLDERS, CanonicalLibrary, normalize_id, validate_object


REPO_ROOT = Path(__file__).resolve().parents[2]
CKL_ROOT = REPO_ROOT / "framework" / "canonical_library"
OBJECTS_ROOT = CKL_ROOT / "objects"
MANIFEST_PATH = CKL_ROOT / "manifest.json"
EXPECTED_FOLDERS = set(CATEGORY_FOLDERS.values())
IDENTITY_DRAFTS = {
    "abana",
    "archelaus",
    "azekah",
    "cnidus",
    "crete",
    "cyprus",
    "fair-havens",
    "italy",
    "judah-territory",
    "lasea",
    "myra",
    "pharpar",
    "socoh-1",
    "sychar",
}
EXPECTED_EMPTY_STRING_FIELDS = (
    "summary",
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
    "literary_context",
    "covenantal_significance",
)
EXPECTED_EMPTY_LIST_FIELDS = (
    "generated_by",
    "edited_by",
    "intertextuality",
    "timeline",
    "maps",
    "archaeology",
    "hebrew_words",
    "greek_words",
    "related_people",
    "related_places",
    "related_events",
    "cross_references",
    "new_testament_connections",
    "interpretive_notes",
    "common_questions",
    "sources",
    "scripture_references",
    "reviewed_by",
    "related_objects",
)
EXPECTED_GOVERNANCE_VALUES = {
    "content_status": "placeholder",
    "review_status": "unreviewed",
    "last_reviewed": None,
    "confidence": "unrated",
    "human_review_required": True,
}
EXPECTED_CONTEXT_APPLICABILITY = {
    "historical": False,
    "ancient_near_east": False,
    "hebraic_worldview": False,
    "second_temple": False,
    "canonical": False,
    "later_christian_reception": False,
}
AI_IMPORT_PREFIXES = {
    "anthropic",
    "chromadb",
    "faiss",
    "langchain",
    "llama_index",
    "openai",
    "sentence_transformers",
    "tensorflow",
    "torch",
    "transformers",
}
LEGACY_PROVENANCE_REGISTRY_PATH = (
    REPO_ROOT / "docs" / "maintenance" / "ckl-legacy-provenance-exceptions.json"
)
LEGACY_ATTRIBUTION_UNVERIFIED = "legacy_attribution_unverified"
VERIFIED_GENERATION_PROVENANCE = "verified_generation_provenance"
LEGACY_EXCEPTION_REGISTRY_KEYS = {"schema_version", "exceptions"}
LEGACY_EXCEPTION_ENTRY_KEYS = {
    "object_id",
    "path",
    "sha256",
    "introduced_in_commit",
    "transaction",
    "audit_manifest",
    "reason",
    "status",
    "required_review_status",
    "human_review_required",
}
LEGACY_EXCEPTION_REASON = (
    "Original generator attribution was not documented in the retained transaction evidence; "
    "generator identity remains unverified."
)

# This test-owned allowlist makes the exception set reviewable and rejects any
# new, stale, or invented registry entries until their evidence is audited.
AUDITED_LEGACY_PROVENANCE_RECORDS = {
    "genesis-flood-postflood-context": {
        "path": "framework/canonical_library/objects/cultural_background/genesis-flood-postflood-context.json",
        "sha256": "d22862694a5b6a9799074703a36d4a572d14731a51ab4e8ed70a574734e7c44b",
        "introduced_in_commit": "ce3a58e195a82af086fbce7dfecccbcc80ad99ae",
        "transaction": "GENESIS_G2R2_ISOLATED_EVIDENCE_CONTAINER",
        "audit_manifest": ".bhf-data/bhf-commentary-candidates/genesis-g2-flood-postflood-evidence-expansion/g2-production-apply-manifest.json",
    },
    "genesis-nations-babel-context": {
        "path": "framework/canonical_library/objects/cultural_background/genesis-nations-babel-context.json",
        "sha256": "ee22202a8bfc1be62469d1e710ae2383149ecad445dc4d721008a18d42a22f23",
        "introduced_in_commit": "3991acf388822065eac171fa4cf2b81834726968",
        "transaction": "GENESIS_G3_NATIONS_BABEL_EVIDENCE_EXPANSION",
        "audit_manifest": ".bhf-data/bhf-commentary-candidates/genesis-g3-nations-babel-evidence-expansion/g3-production-apply-manifest.json",
    },
    "genesis-abraham-call-covenant-context": {
        "path": "framework/canonical_library/objects/cultural_background/genesis-abraham-call-covenant-context.json",
        "sha256": "02aeceb005539c7175afa4631cffc808ef377b73185b760f582e48119fb38aa9",
        "introduced_in_commit": "42c821a7639366a2338963b11a475958f586d2fa",
        "transaction": "GENESIS_G4A_ABRAHAM_CALL_COVENANT_EVIDENCE_EXPANSION",
        "audit_manifest": ".bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-production-apply-manifest.json",
    },
    "genesis-abraham-late-cycle-context": {
        "path": "framework/canonical_library/objects/cultural_background/genesis-abraham-late-cycle-context.json",
        "sha256": "95413e73224c3242589c0d9891444f3c7b438bd562d70cdb6ae239d7fd5d7408",
        "introduced_in_commit": "52a77843ae0be8c94ca33494278be7b209911ac6",
        "transaction": "GENESIS_G4B_ABRAHAM_LATE_CYCLE_EVIDENCE_EXPANSION",
        "audit_manifest": ".bhf-data/bhf-commentary-candidates/genesis-g4b-abraham-late-cycle-evidence-expansion/g4b-production-apply-manifest.json",
    },
    "genesis-isaac-jacob-transition-context": {
        "path": "framework/canonical_library/objects/cultural_background/genesis-isaac-jacob-transition-context.json",
        "sha256": "22f8d2d0b6c7625b1267193ab1fb4e500981ad95713f702b83466b031bcb28cb",
        "introduced_in_commit": "76c5beabd4ba98093f02d22d2eb95ed9a9372acb",
        "transaction": "GENESIS_G5A_ISAAC_JACOB_TRANSITION_EVIDENCE_EXPANSION",
        "audit_manifest": ".bhf-data/bhf-commentary-candidates/genesis-g5a-isaac-jacob-transition-evidence-expansion/g5a-production-apply-manifest.json",
    },
}


def load_legacy_provenance_registry() -> dict[str, dict[str, object]]:
    raw_registry = json.loads(
        LEGACY_PROVENANCE_REGISTRY_PATH.read_text(encoding="utf-8")
    )
    return validate_legacy_provenance_registry(raw_registry)


def validate_legacy_provenance_registry(
    registry: object,
) -> dict[str, dict[str, object]]:
    """Strictly validate the legacy exception schema, pins, and evidence."""

    if type(registry) is not dict or set(registry) != LEGACY_EXCEPTION_REGISTRY_KEYS:
        raise ValueError("legacy provenance registry schema keys are invalid")
    if type(registry["schema_version"]) is not int or registry["schema_version"] != 1:
        raise ValueError("legacy provenance registry schema_version must be integer 1")
    entries = registry["exceptions"]
    if type(entries) is not list:
        raise ValueError("legacy provenance registry exceptions must be an array")

    validated: dict[str, dict[str, object]] = {}
    seen_paths: set[str] = set()
    for entry in entries:
        if type(entry) is not dict or set(entry) != LEGACY_EXCEPTION_ENTRY_KEYS:
            raise ValueError("legacy provenance exception schema keys are invalid")
        object_id = entry["object_id"]
        if type(object_id) is not str or not object_id:
            raise ValueError("legacy provenance exception object_id must be a nonempty string")
        if object_id in validated:
            raise ValueError(f"duplicate legacy provenance exception for {object_id}")
        if object_id not in AUDITED_LEGACY_PROVENANCE_RECORDS:
            raise ValueError(f"invented legacy provenance exception for {object_id}")

        for key in LEGACY_EXCEPTION_ENTRY_KEYS - {"human_review_required"}:
            if type(entry[key]) is not str or not entry[key]:
                raise ValueError(f"legacy provenance exception {key} must be a nonempty string")
        if type(entry["human_review_required"]) is not bool:
            raise ValueError("legacy provenance exception human-review requirement must be boolean")

        expected = {
            **AUDITED_LEGACY_PROVENANCE_RECORDS[object_id],
            "object_id": object_id,
            "reason": LEGACY_EXCEPTION_REASON,
            "status": LEGACY_ATTRIBUTION_UNVERIFIED,
            "required_review_status": "in_review",
            "human_review_required": True,
        }
        if entry != expected:
            raise ValueError(f"legacy provenance exception contract mismatch for {object_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(entry["sha256"])):
            raise ValueError(f"invalid SHA-256 pin for {object_id}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(entry["introduced_in_commit"])):
            raise ValueError(f"invalid introduction commit for {object_id}")

        relative_path = PurePosixPath(str(entry["path"]))
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or not str(relative_path).startswith("framework/canonical_library/objects/")
        ):
            raise ValueError(f"unsafe CKL object path for {object_id}")
        if str(entry["path"]) in seen_paths:
            raise ValueError(f"duplicate legacy provenance object path {entry['path']}")
        seen_paths.add(str(entry["path"]))

        object_path = REPO_ROOT / str(entry["path"])
        if not object_path.is_file():
            raise ValueError(f"stale legacy provenance object path for {object_id}")
        object_bytes = object_path.read_bytes()
        digest = hashlib.sha256(object_bytes).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"legacy provenance SHA-256 mismatch for {object_id}")
        record = json.loads(object_bytes)
        if record.get("id") != object_id:
            raise ValueError(f"legacy provenance object ID mismatch for {object_id}")
        _validate_legacy_record_state(record, object_id)

        manifest_path = PurePosixPath(str(entry["audit_manifest"]))
        if (
            manifest_path.is_absolute()
            or ".." in manifest_path.parts
            or not str(manifest_path).startswith(".bhf-data/bhf-commentary-candidates/")
        ):
            raise ValueError(f"unsafe audit manifest path for {object_id}")
        manifest_file = REPO_ROOT / str(entry["audit_manifest"])
        if not manifest_file.is_file():
            raise ValueError(f"missing retained transaction manifest for {object_id}")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest_strings = _nested_manifest_strings(manifest)
        if manifest.get("transaction") != entry["transaction"]:
            raise ValueError(f"transaction name mismatch for {object_id}")
        if object_id not in manifest_strings or str(entry["path"]) not in manifest_strings:
            raise ValueError(f"transaction manifest does not identify {object_id} and its path")

        validated[object_id] = dict(entry)

    expected_ids = set(AUDITED_LEGACY_PROVENANCE_RECORDS)
    if set(validated) != expected_ids:
        missing = sorted(expected_ids - set(validated))
        stale = sorted(set(validated) - expected_ids)
        raise ValueError(f"legacy provenance registry inventory mismatch; missing={missing}, stale={stale}")
    return validated


def validate_in_review_provenance(
    record: dict[str, object],
    *,
    object_path: str,
    object_bytes: bytes,
    exception: dict[str, object] | None,
) -> str:
    """Preserve ordinary generator checks and narrowly allow audited legacy records."""

    if record.get("review_status") != "in_review":
        raise ValueError("legacy attribution exceptions require review_status in_review")
    if record.get("human_review_required") is not True:
        raise ValueError("legacy attribution exceptions require human review")

    generated_by = record.get("generated_by")
    if type(generated_by) is not list:
        raise ValueError("generated_by must be an array")
    if generated_by:
        if exception is not None:
            raise ValueError("legacy exception cannot be used when generated_by is populated")
        return VERIFIED_GENERATION_PROVENANCE

    if exception is None:
        raise ValueError("no registered provenance exception for empty generated_by")
    object_id = record.get("id")
    expected = AUDITED_LEGACY_PROVENANCE_RECORDS.get(str(object_id))
    if expected is None:
        raise ValueError(f"no registered provenance exception for empty generated_by: {object_id}")
    expected_entry = {
        **expected,
        "object_id": object_id,
        "reason": LEGACY_EXCEPTION_REASON,
        "status": LEGACY_ATTRIBUTION_UNVERIFIED,
        "required_review_status": "in_review",
        "human_review_required": True,
    }
    if type(exception) is not dict or set(exception) != LEGACY_EXCEPTION_ENTRY_KEYS:
        raise ValueError("legacy provenance exception schema keys are invalid")
    if exception != expected_entry:
        raise ValueError(f"legacy provenance exception contract mismatch for {object_id}")
    if object_path != expected["path"]:
        raise ValueError(f"legacy provenance path mismatch for {object_id}")
    if hashlib.sha256(object_bytes).hexdigest() != expected["sha256"]:
        raise ValueError(f"legacy provenance SHA-256 mismatch for {object_id}")
    if record.get("content_status") != "draft":
        raise ValueError("legacy attribution exceptions cannot be used by completed records")
    if record.get("reviewed_by") != []:
        raise ValueError("legacy attribution exceptions cannot imply human review")
    if record.get("generated_by") != []:
        raise ValueError("legacy attribution exceptions require empty generated_by")
    return LEGACY_ATTRIBUTION_UNVERIFIED


def _validate_legacy_record_state(record: dict[str, object], object_id: str) -> None:
    if record.get("content_status") != "draft":
        raise ValueError(f"legacy exception record {object_id} is stale or completed")
    if record.get("review_status") != "in_review":
        raise ValueError(f"legacy exception record {object_id} must remain in_review")
    if record.get("generated_by") != []:
        raise ValueError(f"legacy exception record {object_id} no longer has empty generated_by")
    if record.get("reviewed_by") != []:
        raise ValueError(f"legacy exception record {object_id} cannot have a reviewer")
    if record.get("human_review_required") is not True:
        raise ValueError(f"legacy exception record {object_id} must still require human review")


def _nested_manifest_strings(value: object) -> set[str]:
    if isinstance(value, dict):
        return {
            string
            for nested in value.values()
            for string in _nested_manifest_strings(nested)
        }
    if isinstance(value, list):
        return {
            string
            for nested in value
            for string in _nested_manifest_strings(nested)
        }
    return {value} if isinstance(value, str) else set()


class CanonicalInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = CanonicalLibrary.load_default()

    def assert_identity_draft(self, obj) -> None:
        self.assertEqual(obj.content_status, "draft", obj.id)
        self.assertEqual(obj.review_status, "unreviewed", obj.id)
        self.assertEqual(obj.importance, 0, obj.id)
        self.assertEqual(obj.confidence, "unrated", obj.id)
        self.assertTrue(obj.human_review_required, obj.id)
        self.assertEqual(obj.generated_by, [], obj.id)
        self.assertEqual(obj.reviewed_by, [], obj.id)
        self.assertIsNone(obj.last_reviewed, obj.id)
        self.assertNotEqual(obj.summary, "", obj.id)
        self.assertNotEqual(obj.sources, [], obj.id)
        self.assertNotEqual(obj.scripture_references, [], obj.id)

    def test_all_inventory_json_files_validate_and_receive_governance_defaults(self) -> None:
        legacy_exceptions = load_legacy_provenance_registry()
        used_legacy_exceptions: set[str] = set()
        seen_ids: set[str] = set()
        counts: Counter[str] = Counter()

        for path in sorted(OBJECTS_ROOT.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            obj = validate_object(data, path=path.relative_to(CKL_ROOT).as_posix())

            self.assertNotIn(obj.id, seen_ids)
            seen_ids.add(obj.id)
            self.assertEqual(path.stem, obj.id)
            self.assertIn(path.parent.name, EXPECTED_FOLDERS)
            self.assertEqual(obj.framework_version, "1.0")
            self.assertEqual(obj.object_version, "1")
            if obj.content_status == "placeholder":
                self.assertEqual(obj.importance, 0)

                for field_name in EXPECTED_EMPTY_STRING_FIELDS:
                    self.assertEqual(getattr(obj, field_name), "")
                for field_name in EXPECTED_EMPTY_LIST_FIELDS:
                    self.assertEqual(getattr(obj, field_name), [])
                for field_name, expected in EXPECTED_GOVERNANCE_VALUES.items():
                    self.assertEqual(getattr(obj, field_name), expected)
                self.assertEqual(obj.context_applicability, EXPECTED_CONTEXT_APPLICABILITY)
            elif obj.content_status in {"draft", "complete"}:
                if obj.id in IDENTITY_DRAFTS:
                    self.assert_identity_draft(obj)
                    counts[obj.type] += 1
                    continue
                self.assertGreater(obj.importance, 0)
                self.assertNotEqual(obj.summary, "")
                self.assertNotEqual(obj.sources, [])
                self.assertNotEqual(obj.scripture_references, [])
                self.assertNotEqual(obj.review_status, "unreviewed")
                if obj.review_status == "in_review":
                    provenance_state = validate_in_review_provenance(
                        data,
                        object_path=path.relative_to(REPO_ROOT).as_posix(),
                        object_bytes=path.read_bytes(),
                        exception=legacy_exceptions.get(obj.id),
                    )
                    if provenance_state == LEGACY_ATTRIBUTION_UNVERIFIED:
                        used_legacy_exceptions.add(obj.id)
                    self.assertTrue(obj.human_review_required)
                else:
                    self.assertGreaterEqual(len(obj.reviewed_by), 1)
                    self.assertFalse(obj.human_review_required)
                if obj.content_status == "complete":
                    self.assertIsNotNone(obj.last_reviewed)
                else:
                    self.assertIsNone(obj.last_reviewed)
                    self.assertEqual(obj.review_status, "in_review")
                    self.assertTrue(obj.human_review_required)
                self.assertNotEqual(obj.confidence, "unrated")
            else:
                self.fail(f"unexpected content status {obj.content_status!r} for {obj.id}")

            counts[obj.type] += 1

        self.assertEqual(len(seen_ids), len(self.library.objects_by_id))
        self.assertTrue(IDENTITY_DRAFTS.issubset(seen_ids))
        self.assertEqual(used_legacy_exceptions, set(legacy_exceptions))
        self.assertEqual(counts["book"], 66)
        self.assertEqual(sum(counts.values()), len(self.library.objects_by_id))

    def test_category_directories_are_valid(self) -> None:
        top_level_folders = {path.name for path in OBJECTS_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(top_level_folders, EXPECTED_FOLDERS)

    def test_all_biblical_books_exist(self) -> None:
        expected_book_ids = {normalize_id(title) for title in BOOKS}
        actual_book_ids = set(self.library.objects_by_type["book"])

        self.assertEqual(len(expected_book_ids), 66)
        self.assertEqual(actual_book_ids, expected_book_ids)

    def test_all_biblical_books_include_wave2_metadata(self) -> None:
        for book_id in self.library.objects_by_type["book"]:
            book = self.library.objects_by_id[book_id]

            self.assertTrue(book.authorship_positions, book_id)
            self.assertTrue(book.date_ranges, book_id)
            self.assertTrue(book.original_audience.strip(), book_id)
            self.assertTrue(book.historical_setting.strip(), book_id)
            self.assertTrue(book.genre, book_id)
            self.assertTrue(book.structure, book_id)
            self.assertTrue(book.major_themes, book_id)
            self.assertTrue(book.canonical_placement.strip(), book_id)
            self.assertTrue(book.key_people, book_id)
            self.assertTrue(book.key_places, book_id)
            self.assertTrue(book.key_events, book_id)
            self.assertTrue(book.interpretive_disputes, book_id)
            self.assertTrue(book.primary_sources, book_id)

    def test_wave3_people_places_events_and_institutions_are_populated(self) -> None:
        for category in ("people", "places", "events", "institutions"):
            for path in sorted((OBJECTS_ROOT / category).glob("*.json")):
                obj = validate_object(
                    json.loads(path.read_text(encoding="utf-8")),
                    path=path.relative_to(CKL_ROOT).as_posix(),
                )

                if category == "events" and obj.title.startswith("Event Placeholder"):
                    self.assertEqual(obj.content_status, "placeholder", obj.id)
                    self.assertEqual(obj.review_status, "unreviewed", obj.id)
                    continue

                if obj.id in IDENTITY_DRAFTS:
                    self.assert_identity_draft(obj)
                    continue

                self.assertEqual(obj.content_status, "complete", obj.id)
                self.assertNotEqual(obj.summary, "", obj.id)
                self.assertNotEqual(obj.scripture_references, [], obj.id)
                self.assertNotEqual(obj.sources, [], obj.id)
                self.assertNotEqual(obj.review_status, "unreviewed", obj.id)
                if obj.review_status == "in_review":
                    self.assertGreaterEqual(len(obj.generated_by), 1, obj.id)
                    self.assertTrue(obj.human_review_required, obj.id)
                else:
                    self.assertGreaterEqual(len(obj.reviewed_by), 1, obj.id)
                    self.assertFalse(obj.human_review_required, obj.id)
                self.assertIsNotNone(obj.last_reviewed, obj.id)
                self.assertGreater(obj.importance, 0, obj.id)

    def test_wave4_theology_themes_prophecy_word_studies_archaeology_and_faq_are_populated(
        self,
    ) -> None:
        for category in ("theology", "themes", "prophecy", "word_studies", "archaeology", "faq"):
            for path in sorted((OBJECTS_ROOT / category).glob("*.json")):
                obj = validate_object(
                    json.loads(path.read_text(encoding="utf-8")),
                    path=path.relative_to(CKL_ROOT).as_posix(),
                )

                self.assertEqual(obj.content_status, "complete", obj.id)
                self.assertNotEqual(obj.summary, "", obj.id)
                self.assertNotEqual(obj.sources, [], obj.id)
                self.assertNotEqual(obj.scripture_references, [], obj.id)
                self.assertNotEqual(obj.common_questions, [], obj.id)
                self.assertNotEqual(obj.interpretive_notes, [], obj.id)
                self.assertNotEqual(obj.review_status, "unreviewed", obj.id)
                if obj.review_status == "in_review":
                    self.assertGreaterEqual(len(obj.generated_by), 1, obj.id)
                    self.assertTrue(obj.human_review_required, obj.id)
                else:
                    self.assertGreaterEqual(len(obj.reviewed_by), 1, obj.id)
                    self.assertFalse(obj.human_review_required, obj.id)
                self.assertIsNotNone(obj.last_reviewed, obj.id)
                self.assertGreater(obj.importance, 0, obj.id)

    def test_manifest_counts_match_inventory(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        actual_counts = Counter(obj.type for obj in self.library.objects_by_id.values())
        expected_manifest_counts = {
            manifest_category: actual_counts.get(category, 0)
            for category, manifest_category in CATEGORY_FOLDERS.items()
        }

        self.assertEqual(manifest["framework_version"], "1.0")
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["object_count"], len(self.library.objects_by_id))
        self.assertEqual(manifest["categories"], expected_manifest_counts)

    def test_no_ai_dependencies_are_imported(self) -> None:
        for path in sorted(CKL_ROOT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module_name: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".", 1)[0]
                        self.assertNotIn(
                            module_name,
                            AI_IMPORT_PREFIXES,
                            msg=f"unexpected AI dependency import in {path}: {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".", 1)[0]
                    self.assertNotIn(
                        module_name,
                        AI_IMPORT_PREFIXES,
                        msg=f"unexpected AI dependency import in {path}: {node.module}",
                    )


class LegacyProvenanceExceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_path = REPO_ROOT / "docs" / "maintenance" / "ckl-legacy-provenance-exceptions.json"
        cls.raw_registry = json.loads(cls.registry_path.read_text(encoding="utf-8"))
        cls.exceptions = validate_legacy_provenance_registry(cls.raw_registry)

    def test_exact_historical_records_pass_without_being_marked_reviewed(self) -> None:
        self.assertEqual(len(self.exceptions), 5)
        for object_id, exception in self.exceptions.items():
            with self.subTest(object_id=object_id):
                path = REPO_ROOT / exception["path"]
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    validate_in_review_provenance(
                        data,
                        object_path=exception["path"],
                        object_bytes=path.read_bytes(),
                        exception=exception,
                    ),
                    LEGACY_ATTRIBUTION_UNVERIFIED,
                )
                self.assertEqual(data["generated_by"], [])
                self.assertEqual(data["reviewed_by"], [])
                self.assertEqual(data["content_status"], "draft")
                self.assertEqual(data["review_status"], "in_review")
                self.assertIs(data["human_review_required"], True)

    def test_identical_unlisted_record_is_not_exempt(self) -> None:
        registered = next(iter(self.exceptions.values()))
        source_path = REPO_ROOT / registered["path"]
        record = json.loads(source_path.read_text(encoding="utf-8"))
        record["id"] = "genesis-unlisted-lookalike"
        unlisted_path = "framework/canonical_library/objects/cultural_background/genesis-unlisted-lookalike.json"

        with self.assertRaisesRegex(ValueError, "no registered provenance exception"):
            validate_in_review_provenance(
                record,
                object_path=unlisted_path,
                object_bytes=json.dumps(record, sort_keys=True).encode("utf-8"),
                exception=None,
            )

    def test_modified_object_bytes_fail_the_pinned_sha256(self) -> None:
        exception = next(iter(self.exceptions.values()))
        path = REPO_ROOT / exception["path"]
        data = json.loads(path.read_text(encoding="utf-8"))

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_in_review_provenance(
                data,
                object_path=exception["path"],
                object_bytes=path.read_bytes() + b" ",
                exception=exception,
            )

    def test_registry_rejects_wrong_id_or_path(self) -> None:
        for field, value in (
            ("object_id", "invented-object-id"),
            ("path", "framework/canonical_library/objects/cultural_background/invented.json"),
        ):
            with self.subTest(field=field):
                registry = copy.deepcopy(self.raw_registry)
                registry["exceptions"][0][field] = value
                with self.assertRaises(ValueError):
                    validate_legacy_provenance_registry(registry)

    def test_registry_rejects_duplicate_exceptions(self) -> None:
        registry = copy.deepcopy(self.raw_registry)
        registry["exceptions"].append(copy.deepcopy(registry["exceptions"][0]))

        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_legacy_provenance_registry(registry)

    def test_registry_requires_retained_transaction_evidence(self) -> None:
        for remove_field in ("transaction", "audit_manifest"):
            with self.subTest(field=remove_field):
                registry = copy.deepcopy(self.raw_registry)
                registry["exceptions"][0].pop(remove_field)
                with self.assertRaises(ValueError):
                    validate_legacy_provenance_registry(registry)

    def test_registry_rejects_unknown_or_malformed_fields(self) -> None:
        registry = copy.deepcopy(self.raw_registry)
        registry["exceptions"][0]["generator"] = "codex"

        with self.assertRaisesRegex(ValueError, "schema"):
            validate_legacy_provenance_registry(registry)

    def test_completed_or_reviewed_record_cannot_use_legacy_exception(self) -> None:
        exception = next(iter(self.exceptions.values()))
        path = REPO_ROOT / exception["path"]
        original = json.loads(path.read_text(encoding="utf-8"))
        object_bytes = path.read_bytes()
        invalid_states = (
            {"content_status": "complete"},
            {"review_status": "reviewed"},
            {"reviewed_by": ["reviewer"]},
            {"human_review_required": False},
        )

        for updates in invalid_states:
            with self.subTest(updates=updates):
                record = {**original, **updates}
                with self.assertRaises(ValueError):
                    validate_in_review_provenance(
                        record,
                        object_path=exception["path"],
                        object_bytes=object_bytes,
                        exception=exception,
                    )

    def test_new_draft_with_empty_generator_provenance_fails(self) -> None:
        record = {
            "id": "new-unattributed-draft",
            "content_status": "draft",
            "review_status": "in_review",
            "generated_by": [],
            "reviewed_by": [],
            "human_review_required": True,
        }

        with self.assertRaisesRegex(ValueError, "no registered provenance exception"):
            validate_in_review_provenance(
                record,
                object_path="framework/canonical_library/objects/cultural_background/new-unattributed-draft.json",
                object_bytes=json.dumps(record, sort_keys=True).encode("utf-8"),
                exception=None,
            )

    def test_populated_in_review_object_with_generation_provenance_passes_normally(self) -> None:
        path = OBJECTS_ROOT / "archaeology" / "arad-ostraca.json"
        record = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            validate_in_review_provenance(
                record,
                object_path=path.relative_to(REPO_ROOT).as_posix(),
                object_bytes=path.read_bytes(),
                exception=None,
            ),
            VERIFIED_GENERATION_PROVENANCE,
        )


if __name__ == "__main__":
    unittest.main()
