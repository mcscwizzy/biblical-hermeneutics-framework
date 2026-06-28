import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from bhf_agent.study_db import (
    StudyDataError,
    create_highlight,
    create_note,
    create_saved_study,
    delete_highlight,
    delete_note,
    delete_saved_study,
    initialize_database,
    get_saved_study,
    list_highlights,
    list_notes,
    list_saved_studies,
    update_note,
)


class StudyDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "study.sqlite"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_database_initializes_schema_version(self):
        initialize_database(path=self.path)

        with sqlite3.connect(self.path) as connection:
            versions = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]

        self.assertEqual(versions, [1, 2])

        with sqlite3.connect(self.path) as connection:
            saved_studies = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'saved_studies'
                """
            ).fetchone()

        self.assertIsNotNone(saved_studies)

    def test_v1_database_migrates_to_saved_studies(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (1, '2026-01-01T00:00:00Z')"
            )

        initialize_database(path=self.path)

        with sqlite3.connect(self.path) as connection:
            versions = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
            saved_studies = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'saved_studies'
                """
            ).fetchone()

        self.assertEqual(versions, [1, 2])
        self.assertIsNotNone(saved_studies)

    def test_create_reload_and_filter_notes(self):
        note = create_note(_note_data(), path=self.path)

        self.assertTrue(note["id"])
        self.assertEqual(note["book"], "Romans")
        self.assertEqual(note["chapter"], 12)
        self.assertEqual(note["created_at"], note["updated_at"])
        self.assertEqual(list_notes("Romans", 12, path=self.path), [note])
        self.assertEqual(list_notes("John", 1, path=self.path), [])

    def test_update_preserves_created_at_and_changes_updated_at(self):
        note = create_note(_note_data(), path=self.path)
        time.sleep(0.001)

        updated = update_note(note["id"], {"body": "Updated note"}, path=self.path)

        self.assertEqual(updated["id"], note["id"])
        self.assertEqual(updated["created_at"], note["created_at"])
        self.assertNotEqual(updated["updated_at"], note["updated_at"])
        self.assertEqual(updated["body"], "Updated note")

    def test_delete_note(self):
        note = create_note(_note_data(), path=self.path)

        self.assertTrue(delete_note(note["id"], path=self.path))
        self.assertEqual(list_notes(path=self.path), [])

    def test_highlights_persist_and_filter(self):
        highlight = create_highlight(_highlight_data(), path=self.path)

        self.assertEqual(highlight["color"], "yellow")
        self.assertEqual(list_highlights("Romans", 12, path=self.path), [highlight])
        self.assertEqual(list_highlights("John", 1, path=self.path), [])

    def test_delete_highlight(self):
        highlight = create_highlight(_highlight_data(), path=self.path)

        self.assertTrue(delete_highlight(highlight["id"], path=self.path))
        self.assertEqual(list_highlights(path=self.path), [])

    def test_invalid_note_input_raises_clear_error(self):
        with self.assertRaisesRegex(StudyDataError, "note body is required"):
            create_note({**_note_data(), "body": " "}, path=self.path)

    def test_invalid_highlight_color_raises_clear_error(self):
        with self.assertRaisesRegex(StudyDataError, "highlight color must be one of"):
            create_highlight({**_highlight_data(), "color": "orange"}, path=self.path)

    def test_json_notes_file_is_not_imported(self):
        json_path = Path(self.tmpdir.name) / "notes.json"
        json_path.write_text(json.dumps([_stored_json_note()]), encoding="utf-8")

        self.assertEqual(list_notes("Romans", 12, path=self.path), [])

    def test_create_reload_and_delete_saved_study(self):
        study = create_saved_study(_saved_study_data(), path=self.path)

        self.assertTrue(study["id"])
        self.assertEqual(study["book"], "Romans")
        self.assertEqual(study["chapter"], 12)
        self.assertEqual(study["study_type"], "literary_context")
        self.assertEqual(list_saved_studies("Romans", 12, path=self.path), [study])

        fetched = get_saved_study(study["id"], path=self.path)
        self.assertEqual(fetched, study)

        self.assertTrue(delete_saved_study(study["id"], path=self.path))
        self.assertEqual(list_saved_studies(path=self.path), [])

    def test_saved_study_defaults_title(self):
        study = create_saved_study(
            {
                **_saved_study_data(),
                "title": " ",
            },
            path=self.path,
        )

        self.assertEqual(study["title"], "Romans 12:1-2 - Literary Context")

    def test_saved_study_requires_answer(self):
        with self.assertRaisesRegex(StudyDataError, "answer is required"):
            create_saved_study(
                {**_saved_study_data(), "answer": " "},
                path=self.path,
            )


def _note_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "I beseech you therefore...",
        "body": "Observe the appeal before application.",
    }


def _highlight_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "living sacrifice",
        "color": "yellow",
    }


def _stored_json_note():
    return {
        "id": "note-1",
        "book": "Romans",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "text",
        "body": "Stored note",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _saved_study_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "present your bodies a living sacrifice",
        "study_type": "literary_context",
        "question": "Using BHF, explain the literary context of ASV Romans 12:1-2.",
        "answer": "## Short Answer\nObserve the flow before interpretation.",
        "title": "Romans 12:1-2 - Literary Context",
    }


if __name__ == "__main__":
    unittest.main()
