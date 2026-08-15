from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from bhf_agent.coverage import evaluate_answer_coverage
from bhf_agent.models import GenreContext, QuestionContext, ReferenceContext
from framework.canonical_library import (
    CKL_DATABASE_SCHEMA_VERSION,
    CKL_RETRIEVAL_INDEX_VERSION,
    CanonicalContextBuilder,
    CanonicalLibrary,
    SQLiteCanonicalLibrary,
    build_canonical_prompt_context,
)
from framework.canonical_library.database_builder import build_database, verify_database
from framework.canonical_library.quality_report import build_quality_report
from framework.canonical_library.query_analysis import analyze_query

from .helpers import make_object, write_library


def evidence_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "ruth",
            "book",
            "Ruth",
            ["Megillat Ruth"],
            summary="Ruth concerns household restoration.",
            historical_context="Land redemption and family inheritance meet at the town gate.",
            scripture_references=[
                {"reference": "Ruth 4:1-12", "relationship": "primary", "notes": "gate transaction"}
            ],
            claims=[
                {
                    "id": "ruth-opening-loss",
                    "claim": "Ruth opens with famine and bereavement.",
                    "claim_type": "literary",
                    "certainty": "textually_explicit",
                    "dispute_status": "not_disputed",
                    "scripture_references": ["Ruth 1:1-5"],
                    "source_ids": ["source-opening"],
                    "rationale": "The opening scene states these losses.",
                },
                {
                    "id": "ruth-inheritance-risk",
                    "claim": "The nearer redeemer links redemption with danger to his inheritance.",
                    "claim_type": "biblical_text",
                    "certainty": "textually_explicit",
                    "dispute_status": "major_scholarly_disagreement",
                    "scripture_references": ["Ruth 4:5-6"],
                    "source_ids": ["source-gate"],
                    "rationale": "The reason is explicit; the exact economic reconstruction remains disputed.",
                },
            ],
            sources=[
                {
                    "id": "source-opening",
                    "title": "Ruth 1",
                    "author": "",
                    "publisher": "",
                    "year": None,
                    "locator": "Ruth 1:1-5",
                    "url": "",
                    "source_type": "scripture",
                    "supports": ["ruth-opening-loss"],
                    "notes": "",
                },
                {
                    "id": "source-gate",
                    "title": "Ruth 4",
                    "author": "",
                    "publisher": "",
                    "year": None,
                    "locator": "Ruth 4:5-6",
                    "url": "",
                    "source_type": "scripture",
                    "supports": ["historical_context", "ruth-inheritance-risk"],
                    "notes": "",
                },
            ],
            related_objects=[
                {"id": "kinship-redemption", "relationship": "cultural-background", "weight": 9, "notes": "one hop"},
                {"id": "unrelated-feast", "relationship": "background", "weight": 9, "notes": "guarded"},
            ],
        ),
        make_object(
            "kinship-redemption",
            "cultural_background",
            "Kinship Redemption",
            ["land redemption"],
            summary="Kinship redemption concerns land, inheritance, and family continuity.",
        ),
        make_object(
            "unrelated-feast",
            "cultural_background",
            "Unrelated Feast",
            ["festival meal"],
            summary="A festival meal unrelated to land or kinship.",
        ),
    ]


class EvidenceArchitectureTests(unittest.TestCase):
    def build_fixture(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp) / "ckl"
        database = Path(tmp) / "ckl.sqlite"
        write_library(root, evidence_objects())
        build_database(root, database)
        return root, database

    def test_claim_source_normalization_and_support_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            report = verify_database(database, root=root)
            self.assertEqual(report["database_schema_version"], CKL_DATABASE_SCHEMA_VERSION)
            self.assertEqual(CKL_RETRIEVAL_INDEX_VERSION, "3")
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM canonical_claims").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM canonical_sources").fetchone()[0], 2)
                self.assertEqual(
                    connection.execute("SELECT reference_text FROM canonical_claim_scripture_references WHERE claim_id = 'ruth-inheritance-risk'").fetchone()[0],
                    "Ruth 4:5-6",
                )
                relationships = connection.execute(
                    "SELECT relationship FROM canonical_claim_sources WHERE claim_id = 'ruth-inheritance-risk' ORDER BY relationship"
                ).fetchall()
                self.assertEqual(relationships, [("source_id",), ("supports",)])
                supports = connection.execute(
                    "SELECT supported_item FROM canonical_source_supports WHERE source_id = 'source-gate' ORDER BY supported_item"
                ).fetchall()
                self.assertEqual(supports, [("historical-context",), ("ruth-inheritance-risk",)])
            finally:
                connection.close()

    def test_query_aware_claim_ranking_and_exact_source_hydration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            library = SQLiteCanonicalLibrary.from_path(database, root=root)
            evidence = library.retrieve_claim_evidence(
                "Why would redeeming Ruth endanger his inheritance?",
                ["ruth"],
                parent_scores={"ruth": 1.0},
                requested_dimensions=("direct textual explanation", "cultural practice"),
                scripture_references=("Ruth 4:5",),
            )["ruth"]
            library.close()
        self.assertEqual(evidence[0].claim_id, "ruth-inheritance-risk")
        self.assertEqual([source["id"] for source in evidence[0].sources], ["source-gate"])
        self.assertEqual(evidence[0].sources[0]["locator"], "Ruth 4:5-6")
        self.assertIn("Ruth 4:5-6", evidence[0].scripture_references)
        self.assertTrue(evidence[0].retrieval_reason)

    def test_json_and_sqlite_claim_ranking_are_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            question = "Why would redeeming Ruth endanger his inheritance?"
            arguments = {
                "parent_scores": {"ruth": 1.0},
                "requested_dimensions": ("direct textual explanation", "cultural practice"),
                "scripture_references": ("Ruth 4:5",),
            }
            json_library = CanonicalLibrary(root=root).load()
            sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
            json_evidence = json_library.retrieve_claim_evidence(question, ["ruth"], **arguments)["ruth"]
            sqlite_evidence = sqlite_library.retrieve_claim_evidence(question, ["ruth"], **arguments)["ruth"]
            sqlite_library.close()
        self.assertEqual(
            [(item.claim_id, item.retrieval_score, item.sources) for item in json_evidence],
            [(item.claim_id, item.retrieval_score, item.sources) for item in sqlite_evidence],
        )

    def test_schema_mismatch_has_clear_rebuild_error_and_build_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            connection = sqlite3.connect(database)
            try:
                signature = connection.execute(
                    "SELECT value FROM ckl_metadata WHERE key = 'source_inventory_signature'"
                ).fetchone()
                self.assertIsNotNone(signature)
                connection.execute(
                    "UPDATE ckl_metadata SET value = '2' WHERE key = 'database_schema_version'"
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaisesRegex(RuntimeError, "Rebuild the database"):
                SQLiteCanonicalLibrary.from_path(database, root=root)

    def test_prompt_packet_uses_selected_claim_sources_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            library = SQLiteCanonicalLibrary.from_path(database, root=root)
            context = CanonicalContextBuilder(library).build(
                "Why would redeeming Ruth endanger his inheritance?", limit=2
            )
            prompt = build_canonical_prompt_context(context, max_entries=1, max_context_tokens=220)
            library.close()
        entry = prompt["entries"][0]
        self.assertEqual(entry["selected_claims"][0]["claim_id"], "ruth-inheritance-risk")
        self.assertEqual([source["id"] for source in entry["sources"]], ["source-gate"])
        self.assertIn("Ruth 4:5-6", entry["scripture_references"])
        self.assertLessEqual(prompt["metadata"]["estimated_tokens"], 220)

    def test_fts_bm25_hybrid_exact_alias_and_scripture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, database = self.build_fixture(tmp)
            library = SQLiteCanonicalLibrary.from_path(database, root=root)
            fts = library.repository.search_fts("family inheritance continuity")
            hybrid = library.retrieve_hybrid("family inheritance continuity", limit=3, apply_thresholds=False)
            alias = library.retrieve_exact("Megillat Ruth")
            scripture = library.retrieve_by_scripture_reference("Ruth 4:5", limit=3)
            library.close()
        self.assertEqual(fts[0][0], "kinship-redemption")
        self.assertEqual(hybrid[0].object.id, "kinship-redemption")
        self.assertIn("fts5", hybrid[0].matched_fields)
        self.assertEqual(alias.object.id, "ruth")
        self.assertEqual(scripture[0].object.id, "ruth")

    def test_structured_query_and_guarded_one_hop_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            write_library(root, evidence_objects())
            library = CanonicalLibrary(root=root).load()
            analysis = analyze_query(
                "What cultural background explains Ruth 4 and its inheritance risk?",
                book_alias_lookup=library._book_alias_lookup,
            )
            context = CanonicalContextBuilder(
                library,
                max_relationship_depth=1,
                max_expanded_topics=3,
                min_relationship_weight=6,
            ).build("What cultural background explains Ruth 4 and its inheritance risk?", limit=1)
        self.assertIn("Ruth", analysis.detected_books)
        self.assertIn("inheritance", analysis.concepts)
        self.assertIn("cultural practice", analysis.requested_evidence_dimensions)
        self.assertEqual(analysis.question_intent, "contextual_explanation")
        self.assertTrue(analysis.relationship_expansion_intent)
        ids = [topic["id"] for topic in context["retrieved_topics"]]
        self.assertEqual(ids, ["ruth", "kinship-redemption"])
        self.assertEqual(context["retrieved_topics"][1]["relationship_depth"], 1)

    def test_evidence_coverage_map_drives_targeted_missing_dimension(self) -> None:
        context = {
            "retrieved_topics": [
                {
                    "id": "ruth",
                    "title": "Ruth",
                    "summary": "The gate transaction preserves the family name.",
                    "evidence_coverage": {
                        "direct textual explanation": {
                            "status": "covered",
                            "claim_ids": ["ruth-inheritance-risk"],
                            "scripture_references": ["Ruth 4:5-6"],
                            "source_ids": ["source-gate"],
                        }
                    },
                }
            ]
        }
        assessment = evaluate_answer_coverage(
            question="Why, and what evidence supports the major interpretations of this passage?",
            reference_context=ReferenceContext(book="Ruth", chapter=4, is_reference_based=True, confidence=0.9),
            genre_context=GenreContext(primary_genre="narrative", confidence=0.9),
            question_context=QuestionContext("passage_study", confidence=0.9),
            canonical_context=context,
            canonical_strong_match=True,
            ckl_coverage_gap=None,
        )
        self.assertEqual(assessment.coverage_map["direct textual explanation"]["status"], "covered")
        self.assertEqual(assessment.coverage_map["archaeology"]["status"], "not_requested")
        self.assertIn("major scholarly interpretations", assessment.missing_dimensions)
        self.assertEqual(assessment.mode, "targeted_gap_expansion")

    def test_coverage_map_preserves_not_applicable_status(self) -> None:
        context = {
            "retrieved_topics": [
                {
                    "id": "ruth",
                    "evidence_coverage": {
                        "archaeology": {
                            "status": "not_applicable",
                            "claim_ids": [],
                            "scripture_references": [],
                            "source_ids": [],
                        }
                    },
                }
            ]
        }
        assessment = evaluate_answer_coverage(
            question="What archaeological evidence is applicable to this passage?",
            reference_context=None,
            genre_context=None,
            question_context=QuestionContext("historical_context", confidence=0.9),
            canonical_context=context,
            canonical_strong_match=True,
            ckl_coverage_gap=None,
        )
        self.assertEqual(assessment.coverage_map["archaeology"]["status"], "not_applicable")
        self.assertNotIn("archaeology", assessment.missing_dimensions)

    def test_quality_report_includes_category_depth_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            write_library(root, evidence_objects())
            report = build_quality_report(root)
        self.assertEqual(report["report_version"], "1.3")
        self.assertIn("evidence_audit", report)
        self.assertEqual(report["category_depth"]["categories"]["cultural_background"]["object_count"], 2)
        self.assertTrue(report["category_depth"]["high_value_gaps"])


if __name__ == "__main__":
    unittest.main()
