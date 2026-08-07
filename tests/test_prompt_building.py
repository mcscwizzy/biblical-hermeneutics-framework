import unittest

from bhf_agent.ckl import build_canonical_context, format_canonical_context_for_prompt, load_canonical_library
from bhf_agent.bible import build_interpretation_context
from bhf_agent.genre import classify_genre
from bhf_agent.knowledge import lookup_lexical_entries, lookup_local_knowledge
from bhf_agent.memory import SessionMemory, SessionTurn
from bhf_agent.prompts import build_prompt, build_prompt_result
from bhf_agent.question_types import classify_question_type
from bhf_agent.references import detect_reference


class PromptBuildingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = detect_reference("What does Proverbs 3 mean?")
        self.genre = classify_genre(self.reference)

    def test_build_prompt_uses_compact_runtime_framework_by_default(self):
        system_prompt, user_prompt = build_prompt(
            "standard",
            "PROFILE CONTENT",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertNotIn("PROFILE CONTENT", system_prompt)
        self.assertIn("# SYSTEM INSTRUCTIONS", system_prompt)
        self.assertIn("Compact BHF Runtime Framework", system_prompt)
        self.assertNotIn("BHF Agent Runtime Instructions", system_prompt)
        self.assertIn("# Final Answer Format", system_prompt)
        self.assertIn("thoughtful, informed conversation", system_prompt)
        self.assertIn("not a sermon", system_prompt)
        self.assertIn("Do not sound scholastic", system_prompt)
        self.assertIn("Begin with `## Answer`", system_prompt)
        self.assertIn("## Biblical Evidence", system_prompt)
        self.assertNotIn("Standard Runtime Strategy", system_prompt)
        self.assertIn("Use supplied Scripture, curated local knowledge", system_prompt)
        self.assertIn("Book: Proverbs", system_prompt)
        self.assertIn("Primary genre: wisdom literature", system_prompt)
        self.assertTrue(user_prompt.endswith("What does Proverbs 3 mean?"))

    def test_runtime_profile_mode_is_accepted_but_ignored(self):
        system_prompt, user_prompt = build_prompt(
            "standard",
            "PROFILE CONTENT",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
            runtime_profile_mode="full",
        )

        self.assertNotIn("PROFILE CONTENT", system_prompt)
        self.assertNotIn("BHF Agent Runtime Instructions", system_prompt)
        self.assertIn("Compact BHF Runtime Framework", system_prompt)
        self.assertTrue(user_prompt.endswith("What does Proverbs 3 mean?"))

    def test_profiles_share_the_unified_answer_format(self):
        system_prompt, _ = build_prompt(
            "minimal-7b",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertNotIn("Minimal Runtime Strategy", system_prompt)
        self.assertNotIn("Genre; Original Audience", system_prompt)

    def test_unified_format_prioritizes_answer_and_qualification(self):
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("first paragraph", system_prompt)
        self.assertIn("Important Qualification", system_prompt)
        self.assertIn("Do not force every section", system_prompt)
        self.assertIn("Do not add personal application unless", system_prompt)

    def test_unified_format_covers_required_question_regressions(self):
        questions = (
            "Why did the Lord keep Hannah from conceiving?",
            "Why did Ruth uncover Boaz's feet and lie down?",
            "What do the seven stars represent in Revelation 1?",
            "Why did God allow this suffering when Scripture gives no explicit reason?",
            "Who was Samuel?",
        )
        for question in questions:
            with self.subTest(question=question):
                system_prompt, user_prompt = build_prompt(
                    "standard",
                    "PROFILE",
                    detect_reference(question),
                    classify_genre(detect_reference(question)),
                    question,
                )
                self.assertIn("Begin with `## Answer`", system_prompt)
                self.assertIn("## Biblical Evidence", system_prompt)
                self.assertIn("## Literary Context", system_prompt)
                self.assertIn("## Historical and Cultural Context", system_prompt)
                self.assertIn("## How We Arrived at the Answer", system_prompt)
                self.assertIn("## Important Qualification", system_prompt)
                self.assertIn("Clearly distinguish explicit statements", system_prompt)
                self.assertIn("Do not add personal application unless", system_prompt)
                self.assertTrue(user_prompt.endswith(question))

    def test_framework_guidance_sets_interpretive_order_and_boundaries(self):
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
            runtime_profile_mode="full",
        )

        self.assertIn("Compact BHF Runtime Framework", system_prompt)
        self.assertIn("immediate literary context", system_prompt)
        self.assertIn("Second Temple", system_prompt)
        self.assertIn("Christological interpretation", system_prompt)
        self.assertIn("modern application", system_prompt)
        self.assertIn("Read the Old Testament as Israel's Scriptures", system_prompt)
        self.assertIn("Preserve the distinction between Israel and the Church", system_prompt)
        self.assertIn("Do not portray Judaism as merely legalistic", system_prompt)
        self.assertIn("do not frame the Old Testament as works-based", system_prompt)

    def test_compact_runtime_framework_preserves_core_bhf_guardrails(self):
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("Compact BHF Runtime Framework", system_prompt)
        self.assertIn("Identify the literary genre", system_prompt)
        self.assertIn("Observe what the text says before moving to interpretation", system_prompt)
        self.assertIn("original audience", system_prompt)
        self.assertIn("covenant patterns", system_prompt)
        self.assertIn("Do not invent historical, linguistic, geographical", system_prompt)
        self.assertIn("Do not force a denominational conclusion", system_prompt)
        self.assertIn("Preserve the distinction between Israel and the Church", system_prompt)
        self.assertIn("Do not portray Judaism as merely legalistic", system_prompt)
        self.assertIn("do not frame the Old Testament as works-based", system_prompt)

    def test_reference_prompt_requires_entire_chapter_and_adjacent_passages(self):
        question = "Explain John 3:16"
        reference = detect_reference(question)
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            reference,
            classify_genre(reference),
            classify_question_type(question, reference),
            question,
            scripture_context=build_interpretation_context("John", 3, 16),
        )

        self.assertIn("# REQUIRED SCRIPTURE CONTEXT", system_prompt)
        self.assertIn(
            "Before interpreting any focal verse, examine the entire chapter",
            system_prompt,
        )
        self.assertIn("Entire chapter (required reading):", system_prompt)
        self.assertIn("Passage immediately before focal text (John 3:13-15)", system_prompt)
        self.assertIn("Passage immediately after focal text (John 3:17-19)", system_prompt)

    def test_prompt_result_reports_section_token_estimates(self):
        result = build_prompt_result(
            "standard",
            "PROFILE CONTENT",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
            response_contract_prompt="# RESPONSE CONTRACT\n\nReturn prose.",
        )

        estimates = result.metadata["prompt_token_estimates"]
        characters = result.metadata["prompt_character_counts"]
        self.assertEqual(result.metadata["runtime_profile_mode"], "unified")
        self.assertFalse(result.metadata["full_profile_injected"])
        self.assertEqual(estimates["profile"], 0)
        self.assertGreater(estimates["runtime_framework"], 0)
        self.assertEqual(estimates["strategy"], 0)
        self.assertGreater(estimates["detected_context"], 0)
        self.assertEqual(estimates["canonical_context"], 0)
        self.assertGreater(estimates["response_contract"], 0)
        self.assertGreater(estimates["system_prompt"], 0)
        self.assertGreater(estimates["user_prompt"], 0)
        self.assertEqual(
            estimates["total_prompt"],
            estimates["system_prompt"] + estimates["user_prompt"],
        )
        self.assertEqual(
            characters["total_prompt"],
            characters["system_prompt"] + characters["user_prompt"],
        )

    def test_prompt_result_reports_retired_runtime_profile(self):
        result = build_prompt_result(
            "standard",
            "PROFILE CONTENT",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
            runtime_profile_mode="full",
        )

        self.assertEqual(result.metadata["runtime_profile_mode"], "unified")
        self.assertEqual(result.metadata["legacy_runtime_profile_mode"], "full")
        self.assertFalse(result.metadata["full_profile_injected"])
        self.assertEqual(result.metadata["prompt_token_estimates"]["profile"], 0)

    def test_answer_modes_are_accepted_but_share_one_prompt(self):
        prompts = []
        for answer_mode in ("concise", "study", "teaching", "scholar"):
            with self.subTest(answer_mode=answer_mode):
                prompts.append(build_prompt(
                    "standard",
                    "PROFILE",
                    self.reference,
                    self.genre,
                    "What does Proverbs 3 mean?",
                    answer_mode=answer_mode,
                ))
        self.assertTrue(all(prompt == prompts[0] for prompt in prompts))

    def test_scholar_profile_does_not_change_the_answer_shape(self):
        system_prompt, _ = build_prompt(
            "scholar",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertNotIn("Scholar Runtime Strategy", system_prompt)

    def test_unknown_profile_uses_the_unified_answer_format(self):
        system_prompt, _ = build_prompt(
            "unknown-profile",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertNotIn("Minimal Runtime Strategy", system_prompt)
        self.assertNotIn("Scholar Runtime Strategy", system_prompt)

    def test_hide_method_notes_adds_concise_instruction(self):
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            detect_reference("Explain John 3:16"),
            classify_genre(detect_reference("Explain John 3:16")),
            "Explain John 3:16",
            show_method_notes=False,
        )

        self.assertIn("Keep method notes concise", system_prompt)

    def test_minimal_word_study_includes_strict_format(self):
        question = "What is the hebrew word for the word spirit or wind?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)

        system_prompt, user_prompt = build_prompt(
            "minimal-7b",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertIn("Clearly distinguish explicit statements", system_prompt)
        self.assertTrue(user_prompt.endswith(question))

    def test_minimal_word_study_cautions_instruction_is_explicit(self):
        question = "What does logos mean?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)

        _, user_prompt = build_prompt(
            "minimal-7b",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
        )

        self.assertIn("User's exact question:", user_prompt)
        self.assertTrue(user_prompt.endswith(question))

    def test_word_study_prompt_includes_local_curated_knowledge(self):
        question = "What is the hebrew word for the word spirit or wind?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        entries = lookup_lexical_entries(question_context)

        system_prompt, _ = build_prompt(
            "minimal-7b",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
            lexical_entries=entries,
        )

        self.assertIn("Local Curated Knowledge", system_prompt)
        self.assertIn("רוּחַ / ruach", system_prompt)
        self.assertIn("Glosses: wind, breath, spirit", system_prompt)
        self.assertIn("Meaning depends on context.", system_prompt)
        self.assertIn("Holy Spirit", system_prompt)
        self.assertIn("nephesh", system_prompt)
        self.assertIn("qol", system_prompt)
        self.assertIn("not the normal Hebrew word for wind", system_prompt)
        self.assertIn("not the normal Hebrew word for spirit or wind", system_prompt)

    def test_prompt_includes_local_book_and_genre_context_when_book_detected(self):
        question = "What does Proverbs 3 mean?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        bundle = lookup_local_knowledge(reference, genre, question_context)

        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
            local_knowledge=bundle,
        )

        self.assertIn("Local Curated Knowledge", system_prompt)
        self.assertIn("Use this local curated knowledge as grounding", system_prompt)
        self.assertIn("Do not treat it as a doctrinal conclusion", system_prompt)
        self.assertIn("Book context (book:Proverbs)", system_prompt)
        self.assertIn("Genre: wisdom literature", system_prompt)
        self.assertIn("Genre guide (genre:wisdom literature)", system_prompt)
        self.assertIn("not automatic formulas", system_prompt)

    def test_prompt_includes_canonical_library_context_before_local_knowledge(self):
        question = "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        bundle = lookup_local_knowledge(reference, genre, question_context)
        canonical_context = build_canonical_context(
            load_canonical_library(),
            question,
            reference_context=reference,
            question_context=question_context,
            max_results=4,
            include_placeholders=True,
            allowed_statuses=("unreviewed", "in_review", "reviewed", "approved"),
        )
        canonical_prompt = format_canonical_context_for_prompt(canonical_context, max_context_tokens=1200)

        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
            local_knowledge=bundle,
            canonical_context_prompt=canonical_prompt,
        )

        self.assertIn("# CANONICAL KNOWLEDGE CONTEXT", system_prompt)
        self.assertIn("You are the explanation layer for the Biblical Hermeneutics Framework.", system_prompt)
        self.assertIn("Use that context as your primary factual source.", system_prompt)
        self.assertIn("Entry: Shechem", system_prompt)
        self.assertIn("Source ID: shechem", system_prompt)
        self.assertIn("Abraham", system_prompt)
        self.assertIn("Joshua 24", system_prompt)
        self.assertLess(
            system_prompt.index("# CANONICAL KNOWLEDGE CONTEXT"),
            system_prompt.index("Local Curated Knowledge"),
        )
        self.assertIn("# Final Answer Format", system_prompt)

    def test_prompt_uses_scripture_reverse_lookup_for_joshua_24(self):
        question = "Which objects relate to Joshua 24?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        canonical_context = build_canonical_context(
            load_canonical_library(),
            question,
            reference_context=reference,
            question_context=question_context,
            max_results=6,
            include_placeholders=True,
            allowed_statuses=("unreviewed", "in_review", "reviewed", "approved"),
        )
        canonical_prompt = format_canonical_context_for_prompt(canonical_context, max_context_tokens=1200)

        self.assertIn("## Entry: Joshua", canonical_prompt)
        self.assertIn("Source ID: joshua", canonical_prompt)
        self.assertIn("Joshua 1-24", canonical_prompt)
        self.assertIn("covenant", canonical_prompt.lower())
        self.assertNotIn("Retrieved object IDs:", canonical_prompt)
        self.assertNotIn("Score:", canonical_prompt)
        self.assertNotIn("Match:", canonical_prompt)
        self.assertNotIn("Status:", canonical_prompt)
        self.assertNotIn("# Canonical Knowledge Context", canonical_prompt)

    def test_prompt_includes_second_temple_context_for_hebrews(self):
        question = "How does the book of Hebrews use priesthood and sacrifice?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        canonical_context = build_canonical_context(
            load_canonical_library(),
            question,
            reference_context=reference,
            question_context=question_context,
            max_results=6,
            include_placeholders=True,
            allowed_statuses=("unreviewed", "in_review", "reviewed", "approved"),
            answer_mode="scholar",
            max_context_tokens=1200,
        )
        canonical_prompt = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=1200,
            answer_mode="scholar",
        )

        self.assertIn("Entry: Hebrews", canonical_prompt)
        self.assertIn("Second Temple Context:", canonical_prompt)
        self.assertIn("Later Christian Reception:", canonical_prompt)
        self.assertLess(
            canonical_prompt.index("Second Temple Context:"),
            canonical_prompt.index("Later Christian Reception:"),
        )

    def test_canonical_context_prompt_ignores_answer_modes(self):
        question = "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)
        canonical_context = build_canonical_context(
            load_canonical_library(),
            question,
            reference_context=reference,
            question_context=question_context,
            max_results=4,
            include_placeholders=True,
            allowed_statuses=("unreviewed", "in_review", "reviewed", "approved"),
            answer_mode="scholar",
            max_context_tokens=1200,
        )

        concise_prompt = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=1200,
            answer_mode="concise",
        )
        scholar_prompt = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=1200,
            answer_mode="scholar",
        )

        self.assertIn("## Entry: Shechem", concise_prompt)
        self.assertIn("## Entry: Shechem", scholar_prompt)
        self.assertIn("Summary:", concise_prompt)
        self.assertIn("Primary Scripture References:", concise_prompt)
        self.assertIn("Interpretive Disputes and Cautions:", concise_prompt)
        self.assertIn("Sources:", concise_prompt)
        self.assertIn("Ancient Near Eastern Context:", concise_prompt)
        self.assertIn("Covenant and Canonical Context:", scholar_prompt)
        self.assertIn("Interpretive Disputes and Cautions:", scholar_prompt)
        self.assertIn("Sources:", scholar_prompt)
        self.assertNotIn("Relevant facts:", concise_prompt)
        self.assertNotIn("Relevant facts:", scholar_prompt)
        self.assertNotIn("Retrieved object IDs:", concise_prompt)
        self.assertNotIn("Retrieved object IDs:", scholar_prompt)
        self.assertEqual(concise_prompt, scholar_prompt)

    def test_prompt_includes_local_session_memory_when_available(self):
        memory = SessionMemory(
            session_id="lesson",
            turns=[
                SessionTurn(
                    question="What does Proverbs 3 mean?",
                    answer_summary="Prior answer about wisdom context.",
                    reference_context={"book": "Proverbs", "is_reference_based": True},
                    genre_context={"primary_genre": "wisdom literature"},
                    question_type="passage_study",
                    profile="standard",
                    answer_mode="study",
                    timestamp="2026-06-27T00:00:00+00:00",
                )
            ],
        )

        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
            session_memory=memory,
        )

        self.assertIn("Local Session Memory", system_prompt)
        self.assertIn(
            "The following is local session context from prior turns. Use it only to maintain continuity.",
            system_prompt,
        )
        self.assertIn("Prior answer about wisdom context.", system_prompt)

    def test_standard_word_study_includes_non_rigid_guidance(self):
        question = "What does logos mean?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)

        system_prompt, user_prompt = build_prompt(
            "standard",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertIn("claim certainty where Scripture is silent", system_prompt)
        self.assertTrue(user_prompt.endswith(question))

    def test_scholar_word_study_warns_against_invented_scholarly_claims(self):
        question = "What does pneuma mean?"
        reference = detect_reference(question)
        genre = classify_genre(reference)
        question_context = classify_question_type(question, reference)

        system_prompt, _ = build_prompt(
            "scholar",
            "PROFILE",
            reference,
            genre,
            question_context,
            question,
        )

        self.assertIn("# Final Answer Format", system_prompt)
        self.assertIn("Clearly distinguish explicit statements", system_prompt)


if __name__ == "__main__":
    unittest.main()
