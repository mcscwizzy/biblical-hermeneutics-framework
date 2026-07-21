import sqlite3
import tempfile
import unittest
from pathlib import Path

from framework.lexical import LexicalLookupService, lookup_word
from framework.lexical.tools.build_lexicon_database import build_lexicon_database
from framework.lexical.tools.validate_lexicon import validate_database
from bhf_agent.config import AgentConfig
from bhf_agent.models import PipelineContext
from bhf_agent.question_types import classify_question_type
from bhf_agent.references import detect_reference
from bhf_agent.runner import BHFAgent


class BiblicalLexicalEngineTests(unittest.TestCase):
    def _sources(self, root: Path) -> tuple[Path, Path]:
        hebrew = root / "hebrew.xml"
        hebrew.write_text(
            """<lexicon>
              <entry id="H2617">
                <lemma>חֶסֶד</lemma><transliteration>ḥesed</transliteration>
                <definition>Steadfast covenant love and loyalty.</definition>
                <part_of_speech>noun</part_of_speech>
              </entry>
            </lexicon>""",
            encoding="utf-8",
        )
        greek = root / "greek.xml"
        greek.write_text(
            """<dictionary xmlns="urn:test">
              <entry strongs="G3056">
                <word>λόγος</word><translit>logos</translit>
                <strongs_def>A word, message, or account.</strongs_def>
                <morphology>noun</morphology><usage_note>Meaning is contextual.</usage_note>
              </entry>
            </dictionary>""",
            encoding="utf-8",
        )
        return hebrew, greek

    def test_database_creation_and_xml_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hebrew, greek = self._sources(root)
            result = build_lexicon_database(
                hebrew=hebrew, greek=greek, output=root / "lexicon.sqlite"
            )

            self.assertEqual(result["hebrew"], 1)
            self.assertEqual(result["greek"], 1)
            self.assertEqual(validate_database(root / "lexicon.sqlite")["entries"], 2)

    def test_startup_diagnostics_report_lexical_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hebrew, greek = self._sources(root)
            database = root / "lexicon.sqlite"
            build_lexicon_database(hebrew=hebrew, greek=greek, output=database)

            service = LexicalLookupService(database)
            try:
                diagnostics = service.startup_diagnostics
            finally:
                service.close()

            self.assertTrue(diagnostics["lexical_database_found"])
            self.assertEqual(diagnostics["lexical_entry_count"], 2)
            self.assertEqual(diagnostics["hebrew_entries"], 1)
            self.assertEqual(diagnostics["greek_entries"], 1)

    def test_lookup_by_strongs_lemma_and_transliteration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hebrew, greek = self._sources(root)
            database = root / "lexicon.sqlite"
            build_lexicon_database(hebrew=hebrew, greek=greek, output=database)

            by_strongs = lookup_word(language="greek", strongs="G03056", database_path=database)
            by_lemma = lookup_word(language="greek", lemma="λόγος", database_path=database)
            by_transliteration = lookup_word(
                language="hebrew", transliteration="hesed", database_path=database
            )

            self.assertEqual(by_strongs["lemma"], "λόγος")
            self.assertEqual(by_lemma["strongs_number"], "G3056")
            self.assertEqual(by_transliteration["strongs_number"], "H2617")

    def test_invalid_source_handling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.xml"
            invalid.write_text("<lexicon><entry>", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_lexicon_database(hebrew=invalid, output=root / "lexicon.sqlite")

    def test_missing_source_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                build_lexicon_database(
                    greek=root / "does-not-exist.xml", output=root / "lexicon.sqlite"
                )

    def test_attribution_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hebrew, _ = self._sources(root)
            database = root / "lexicon.sqlite"
            build_lexicon_database(hebrew=hebrew, output=database)

            entry = lookup_word(language="hebrew", strongs="H2617", database_path=database)
            self.assertEqual(entry["source"], "Open Scriptures Hebrew Lexicon")
            self.assertEqual(entry["license"], "CC BY-SA")
            self.assertEqual(entry["attribution"], "Open Scriptures Hebrew Bible Project")
            with sqlite3.connect(database) as connection:
                source = connection.execute(
                    "SELECT attribution, source_file FROM lexical_sources"
                ).fetchone()
            self.assertEqual(source[0], "Open Scriptures Hebrew Bible Project")
            self.assertTrue(source[1].endswith("hebrew.xml"))

    def test_service_returns_bounded_prompt_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, greek = self._sources(root)
            database = root / "lexicon.sqlite"
            build_lexicon_database(greek=greek, output=database)
            service = LexicalLookupService(database)
            try:
                entries, prompt = service.lookup_question(
                    language="greek",
                    terms=["logos"],
                    question="What does Greek logos mean?",
                    max_prompt_tokens=40,
                )
            finally:
                service.close()
            self.assertEqual(len(entries), 1)
            self.assertLessEqual(len(prompt.split()), 41)
            self.assertIn("Source:", prompt)

    def test_bhf_agent_retrieves_standalone_lexical_context_before_prompting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, greek = self._sources(root)
            database = root / "lexicon.sqlite"
            build_lexicon_database(greek=greek, output=database)
            config = AgentConfig.from_mapping(
                {
                    "adapter": "ollama",
                    "base_url": "http://localhost:11434",
                    "model": "test-model",
                    "profile": "standard",
                    "canonical_library": {"enabled": False},
                    "lexicon": {"runtime_database_path": str(database)},
                }
            )
            service = LexicalLookupService(database)
            try:
                agent = BHFAgent(config, adapter=object(), lexical_engine=service)
                question = "What does the Greek word logos mean?"
                context = PipelineContext(
                    original_question=question,
                    question_context=classify_question_type(
                        question, detect_reference(question)
                    ),
                )
                agent._lookup_lexical_engine(context)
            finally:
                service.close()
            self.assertIn("VERIFIED LEXICAL CONTEXT", context.lexical_context_prompt)
            self.assertIn("Source: Open Scriptures Greek Lexicon", context.lexical_context_prompt)
