import unittest

from bhf_agent.genre import classify_genre
from bhf_agent.prompts import build_prompt
from bhf_agent.references import detect_reference


class PromptBuildingTests(unittest.TestCase):
    def test_build_prompt_includes_profile_context_and_question(self):
        reference = detect_reference("What does Proverbs 3 mean?")
        genre = classify_genre(reference)

        system_prompt, user_prompt = build_prompt(
            "PROFILE CONTENT",
            reference,
            genre,
            "What does Proverbs 3 mean?",
        )

        self.assertIn("PROFILE CONTENT", system_prompt)
        self.assertIn("BHF Agent Runtime Instructions", system_prompt)
        self.assertIn("Book: Proverbs", system_prompt)
        self.assertIn("Primary genre: wisdom literature", system_prompt)
        self.assertEqual(user_prompt, "What does Proverbs 3 mean?")

    def test_hide_method_notes_adds_concise_instruction(self):
        reference = detect_reference("Explain John 3:16")
        genre = classify_genre(reference)

        system_prompt, _ = build_prompt(
            "PROFILE",
            reference,
            genre,
            "Explain John 3:16",
            show_method_notes=False,
        )

        self.assertIn("Keep method notes concise", system_prompt)


if __name__ == "__main__":
    unittest.main()
