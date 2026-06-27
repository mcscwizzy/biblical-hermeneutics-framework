import unittest

from bhf_agent.genre import classify_genre
from bhf_agent.prompts import build_prompt
from bhf_agent.references import detect_reference


class PromptBuildingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = detect_reference("What does Proverbs 3 mean?")
        self.genre = classify_genre(self.reference)

    def test_build_prompt_includes_profile_context_and_question(self):
        system_prompt, user_prompt = build_prompt(
            "standard",
            "PROFILE CONTENT",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("PROFILE CONTENT", system_prompt)
        self.assertIn("BHF Agent Runtime Instructions", system_prompt)
        self.assertIn("Standard Runtime Strategy", system_prompt)
        self.assertIn("Book: Proverbs", system_prompt)
        self.assertIn("Primary genre: wisdom literature", system_prompt)
        self.assertEqual(user_prompt, "What does Proverbs 3 mean?")

    def test_minimal_profile_gets_strict_small_model_instructions(self):
        system_prompt, _ = build_prompt(
            "minimal-7b",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("Minimal Runtime Strategy", system_prompt)
        self.assertIn("Keep answers short", system_prompt)
        self.assertIn("Use simple sentences", system_prompt)
        self.assertIn("Avoid scholarly surveys", system_prompt)
        self.assertIn("Avoid precise dates unless they are supplied", system_prompt)
        self.assertIn("Say uncertain instead of guessing", system_prompt)
        self.assertIn(
            "Genre; Original Audience / Ancient Context; Observation; Interpretation; Application; Cautions / Uncertainty",
            system_prompt,
        )

    def test_standard_profile_gets_balanced_instructions(self):
        system_prompt, _ = build_prompt(
            "standard",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("Standard Runtime Strategy", system_prompt)
        self.assertIn("Use a structured answer with clear headings", system_prompt)
        self.assertIn("Include brief method notes when enabled", system_prompt)
        self.assertIn("Mention major interpretive views when they are relevant", system_prompt)
        self.assertIn("Avoid denominational overreach", system_prompt)

    def test_scholar_profile_gets_deeper_research_style_instructions(self):
        system_prompt, _ = build_prompt(
            "scholar",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("Scholar Runtime Strategy", system_prompt)
        self.assertIn("historical context", system_prompt)
        self.assertIn("intertextuality", system_prompt)
        self.assertIn("language cautions", system_prompt)
        self.assertIn("multiple interpretive options", system_prompt)
        self.assertIn("careful confidence labels", system_prompt)
        self.assertIn(
            "Do not invent scholars, citations, dates, manuscripts, or language claims",
            system_prompt,
        )

    def test_unknown_profile_falls_back_to_standard_strategy(self):
        system_prompt, _ = build_prompt(
            "unknown-profile",
            "PROFILE",
            self.reference,
            self.genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("Standard Runtime Strategy", system_prompt)
        self.assertIn("Use a structured answer with clear headings", system_prompt)
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


if __name__ == "__main__":
    unittest.main()
