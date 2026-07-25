from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalContextBuilder, CanonicalLibrary, CanonicalValidationError
from framework.canonical_library.database_builder import build_database, database_info, verify_database
from framework.canonical_library.database_schema import CKL_DATABASE_SCHEMA_VERSION, REQUIRED_INDEXES
from framework.canonical_library.repository import CKLRepositoryConfig, load_canonical_repository
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary, SQLiteCanonicalRepository

from .helpers import make_object, write_library


class SQLiteCKLStorageTests(unittest.TestCase):
    def test_build_verify_and_query_plan_use_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(
                root,
                [
                    make_object("john", "book", "John", ["Gospel of John"], summary="John context"),
                    make_object(
                        "covenant-theme",
                        "theme",
                        "Covenant Theme",
                        ["covenant motif"],
                        related_objects=[
                            {"id": "john", "relationship": "canonical-context", "weight": 2, "notes": ""}
                        ],
                    ),
                ],
            )

            result = build_database(root, database)
            report = verify_database(database, root=root)

            self.assertEqual(result.object_count, 2)
            self.assertEqual(report["database_schema_version"], CKL_DATABASE_SCHEMA_VERSION)
            self.assertEqual(database_info(database)["object_count"], 2)

            conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            try:
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'"
                    )
                }
                self.assertTrue(REQUIRED_INDEXES.issubset(indexes))
                plan = " ".join(
                    row[3]
                    for row in conn.execute(
                        "EXPLAIN QUERY PLAN SELECT object_id FROM canonical_aliases WHERE normalized_alias = ?",
                        ("gospel of john",),
                    )
                )
                self.assertIn("USING", plan)
                self.assertNotIn("SCAN canonical_aliases", plan)
            finally:
                conn.close()

    def test_invalid_build_does_not_replace_existing_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(root, [make_object("alpha", "person", "Alpha", ["alpha"])])
            original = build_database(root, database).inventory_fingerprint

            alpha_path = root / "objects" / "people" / "alpha.json"
            data = json.loads(alpha_path.read_text(encoding="utf-8"))
            data["id"] = "wrong-id"
            alpha_path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaises(CanonicalValidationError):
                build_database(root, database)

            self.assertEqual(database_info(database)["inventory_fingerprint"], original)

    def test_missing_relationship_target_fails_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(
                root,
                [
                    make_object(
                        "alpha",
                        "person",
                        "Alpha",
                        ["alpha"],
                        related_objects=[
                            {"id": "missing", "relationship": "related", "weight": 1, "notes": ""}
                        ],
                    )
                ],
            )
            with self.assertRaisesRegex(CanonicalValidationError, "references unknown canonical id"):
                build_database(root, database)

    def test_json_and_sqlite_retrieval_parity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(
                root,
                [
                    make_object(
                        "john",
                        "book",
                        "John",
                        ["Gospel of John"],
                        summary="John emphasizes witness and new creation.",
                        scripture_references=[
                            {"reference": "John 1:1", "relationship": "primary", "notes": ""}
                        ],
                        knowledge_layers={
                            "primary": "biblical_text",
                            "secondary": ["literary"],
                        },
                        section_status={"core_summary": "draft"},
                        claims=[
                            {
                                "id": "john-witness-emphasis",
                                "claim": "John emphasizes witness.",
                                "claim_type": "literary",
                                "certainty": "textually_explicit",
                                "dispute_status": "not_disputed",
                                "scripture_references": ["John 1:6-8"],
                                "rationale": "Witness language recurs in the prologue.",
                            }
                        ],
                    ),
                    make_object(
                        "witness-theme",
                        "theme",
                        "Witness Theme",
                        ["witness motif"],
                        summary="Witness is an important theme.",
                        related_objects=[
                            {"id": "john", "relationship": "canonical-context", "weight": 3, "notes": ""}
                        ],
                    ),
                ],
            )
            build_database(root, database)
            json_library = CanonicalLibrary(root=root).load()
            sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)

            self.assertEqual(json_library.retrieve_by_id("john").object.id, sqlite_library.retrieve_by_id("john").object.id)
            self.assertEqual(json_library.retrieve_exact("Gospel of John").object.id, sqlite_library.retrieve_exact("Gospel of John").object.id)
            self.assertEqual(json_library.resolve_entity(("John",), ("book",)).object.id, sqlite_library.resolve_entity(("John",), ("book",)).object.id)
            self.assertEqual(
                [r.object.id for r in json_library.retrieve_by_scripture_reference("John 1:1", limit=5)],
                [r.object.id for r in sqlite_library.retrieve_by_scripture_reference("John 1:1", limit=5)],
            )
            self.assertEqual(
                [r.object.id for r in json_library.retrieve_by_keywords("witness", limit=2)],
                [r.object.id for r in sqlite_library.retrieve_by_keywords("witness", limit=2)],
            )
            self.assertEqual(json_library.inventory_fingerprint(), sqlite_library.inventory_fingerprint())
            sqlite_john = sqlite_library.retrieve_by_id("john").object
            self.assertEqual(sqlite_john.knowledge_layers["primary"], "biblical_text")
            self.assertEqual(sqlite_john.section_status["core_summary"], "draft")
            self.assertEqual(sqlite_john.claims[0].id, "john-witness-emphasis")

    def test_read_only_and_concurrent_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
            build_database(root, database)
            os.chmod(database, 0o444)
            repository = SQLiteCanonicalRepository(database, read_only=True)
            try:
                self.assertEqual(repository.get_by_id("john").title, "John")
                errors: list[BaseException] = []

                def read() -> None:
                    try:
                        self.assertEqual(repository.get_by_title("John")[0].id, "john")
                    except BaseException as exc:  # noqa: BLE001 - test captures thread errors
                        errors.append(exc)

                threads = [threading.Thread(target=read) for _ in range(8)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                self.assertEqual(errors, [])
            finally:
                repository.close()
                os.chmod(database, 0o644)

    def test_stale_database_policies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(root, [make_object("alpha", "person", "Alpha", ["alpha"], summary="one")])
            build_database(root, database)
            alpha_path = root / "objects" / "people" / "alpha.json"
            data = json.loads(alpha_path.read_text(encoding="utf-8"))
            data["summary"] = "two"
            alpha_path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "stale"):
                load_canonical_repository(
                    CKLRepositoryConfig(
                        backend="sqlite",
                        database_path=str(database),
                        json_root=str(root),
                        stale_database_policy="error",
                    )
                )
            fallback = load_canonical_repository(
                CKLRepositoryConfig(
                    backend="sqlite",
                    database_path=str(database),
                    json_root=str(root),
                    stale_database_policy="fallback_to_json",
                )
            )
            self.assertEqual(fallback.get_by_id("alpha").summary, "two")
            rebuilt = load_canonical_repository(
                CKLRepositoryConfig(
                    backend="sqlite",
                    database_path=str(database),
                    json_root=str(root),
                    stale_database_policy="rebuild",
                )
            )
            self.assertEqual(rebuilt.get_by_id("alpha").summary, "two")

    def test_precision_john_context_matches_single_book(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "ckl.sqlite"
            root = Path("framework/canonical_library")
            build_database(root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
            context = CanonicalContextBuilder(sqlite_library).build("What is the context of the book of John?", limit=3)
            ids = [topic["id"] for topic in context["retrieved_topics"]]

        self.assertEqual(ids[:1], ["john"])
        self.assertNotIn("luke", ids)
        self.assertNotIn("revelation", ids)


if __name__ == "__main__":
    unittest.main()
