import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bhf_agent.config import AgentConfig
from bhf_agent.eval import load_suite, score_answer, run_suite
from tools.eval_local import main


SUITE_PATH = Path("tests/prompts/ckl-regression-suite.json")
GENERIC_ANSWER = (
    "Genre: narrative. Original audience: ancient Israel. Observation: the text says this. "
    "Interpretation: it probably means this in context. Application: modern readers may "
    "consider this. Some scholars debate details, so confidence is moderate. Key biblical "
    "data: Genesis 12, Joshua 24, John 1. Major views: some interpreters emphasize promise, "
    "others renewal. Short Answer: The Hebrew word is ruach. Basic Meaning: its semantic "
    "range can include wind, breath, or spirit. Context Matters: meaning depends on passage "
    "context. Cautions: this may vary."
)


def metadata_payload(
    *,
    object_ids: list[str],
    retrieval_method: str | None,
    topic_count: int,
    prompt_tokens: int = 0,
    topic_token_budget: int | None = None,
    enabled: bool = True,
    loaded: bool = True,
    include_placeholders: bool = False,
    allowed_statuses: list[str] | None = None,
) -> dict[str, object]:
    pipeline: dict[str, object] = {
        "canonical_library_enabled": enabled,
        "canonical_library_loaded": loaded,
        "canonical_library_include_placeholders": include_placeholders,
        "canonical_library_allowed_statuses": allowed_statuses
        or ["in_review", "reviewed", "approved"],
        "canonical_library_object_ids": list(object_ids),
        "canonical_library_retrieval_method": retrieval_method,
        "canonical_library_topic_count": topic_count,
        "canonical_library_prompt_tokens": prompt_tokens,
        "stages_completed": ["build_prompts", "call_model", "finalize_result"],
    }
    if topic_token_budget is not None:
        pipeline["canonical_library_topic_token_budget"] = topic_token_budget
    return {
        "canonical_library_object_ids": list(object_ids),
        "canonical_library_retrieval_method": retrieval_method,
        "canonical_library_topic_count": topic_count,
        "pipeline": pipeline,
    }


class FakeAgent:
    received_configs: list[AgentConfig] = []

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.__class__.received_configs.append(config)

    def ask(self, question: str) -> SimpleNamespace:
        metadata = self._metadata_for(question)
        return SimpleNamespace(answer_text=GENERIC_ANSWER, model_metadata=metadata)

    def _metadata_for(self, question: str) -> dict[str, object]:
        config = self.config
        if question == "Shechem" and not config.canonical_library.enabled:
            return metadata_payload(
                object_ids=[],
                retrieval_method=None,
                topic_count=0,
                prompt_tokens=0,
                enabled=False,
                loaded=False,
            )
        if question == "Shechem" and tuple(config.canonical_library.allowed_statuses) == ("approved",):
            return metadata_payload(
                object_ids=[],
                retrieval_method=None,
                topic_count=0,
                prompt_tokens=0,
            )
        if question == "Shechem":
            return metadata_payload(
                object_ids=["shechem"],
                retrieval_method="exact",
                topic_count=1,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "Tell me about Babylon":
            return metadata_payload(
                object_ids=["babylon-1"],
                retrieval_method="exact",
                topic_count=1,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "Jeruselem":
            return metadata_payload(
                object_ids=["jerusalem"],
                retrieval_method="exact",
                topic_count=1,
                prompt_tokens=578,
                topic_token_budget=780,
            )
        if question == "What is Joshua 24?":
            return metadata_payload(
                object_ids=["shechem", "joshua-son-of-nun", "joshua"],
                retrieval_method="exact+scripture",
                topic_count=3,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "What is covenant in the Bible?":
            return metadata_payload(
                object_ids=["what-is-covenant", "what-is-sacrifice-in-the-bible", "covenant-theme"],
                retrieval_method="exact",
                topic_count=3,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "Tell me about covenant and kingdom":
            return metadata_payload(
                object_ids=["davidic-covenant", "covenant-theme", "kingdom-theme"],
                retrieval_method="exact",
                topic_count=3,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?":
            return metadata_payload(
                object_ids=["shechem", "joshua-son-of-nun", "joshua", "what-is-the-kingdom-of-israel", "abraham"],
                retrieval_method="exact+scripture",
                topic_count=5,
                prompt_tokens=1201,
                topic_token_budget=780,
            )
        if question == "Tell me about the temple, exile, and kingdom themes in Israel":
            budget = 32 if config.canonical_library.max_context_tokens == 50 else 780
            prompt_tokens = 51 if config.canonical_library.max_context_tokens == 50 else 1201
            return metadata_payload(
                object_ids=[
                    "division-of-the-kingdom",
                    "what-is-the-kingdom-of-israel",
                    "temple-theme",
                    "exile-theme",
                    "kingdom-theme",
                ],
                retrieval_method="exact",
                topic_count=5,
                prompt_tokens=prompt_tokens,
                topic_token_budget=budget,
            )
        if question == "":
            return metadata_payload(
                object_ids=[],
                retrieval_method=None,
                topic_count=0,
                prompt_tokens=0,
                topic_token_budget=780,
            )
        if question == "???":
            return metadata_payload(
                object_ids=[],
                retrieval_method=None,
                topic_count=0,
                prompt_tokens=0,
                topic_token_budget=780,
            )
        return metadata_payload(
            object_ids=[],
            retrieval_method=None,
            topic_count=0,
            prompt_tokens=0,
            topic_token_budget=780,
        )


class EvalSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeAgent.received_configs = []

    def test_suite_loader_parses_cases_and_overrides(self) -> None:
        suite = load_suite(SUITE_PATH)

        self.assertEqual(suite.id, "ckl-phase-15-regression-suite")
        self.assertEqual(len(suite.cases), 12)

        status_case = next(case for case in suite.cases if case.id == "status-filtering-approved-only")
        token_case = next(case for case in suite.cases if case.id == "token-budget-truncation")
        disabled_case = next(case for case in suite.cases if case.id == "ckl-disabled")

        self.assertEqual(
            status_case.config_overrides["canonical_library"]["allowed_statuses"],
            ["approved"],
        )
        self.assertEqual(
            token_case.config_overrides["canonical_library"]["max_context_tokens"],
            50,
        )
        self.assertFalse(disabled_case.config_overrides["canonical_library"]["enabled"])

    def test_score_answer_uses_metadata_checks(self) -> None:
        suite = load_suite(SUITE_PATH)
        fixture = next(case for case in suite.cases if case.id == "exact-id-shechem")

        result = score_answer(
            GENERIC_ANSWER,
            fixture,
            metadata=metadata_payload(
                object_ids=["shechem"],
                retrieval_method="exact",
                topic_count=1,
                prompt_tokens=1201,
                topic_token_budget=780,
            ),
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.metadata_passed)
        self.assertTrue(all(check.matched for check in result.metadata_checks))
        self.assertEqual(result.score, 100)

    def test_run_suite_uses_per_case_overrides_and_metadata(self) -> None:
        suite = load_suite(SUITE_PATH)
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="fake-model",
            profile="standard",
        )

        with patch("bhf_agent.eval.BHFAgent", FakeAgent):
            result = run_suite(suite, config)

        self.assertTrue(result.passed)
        self.assertEqual(result.passed_count, len(suite.cases))
        self.assertEqual(result.failed_count, 0)

        self.assertTrue(
            any(not cfg.canonical_library.enabled for cfg in FakeAgent.received_configs)
        )
        self.assertTrue(
            any(tuple(cfg.canonical_library.allowed_statuses) == ("approved",) for cfg in FakeAgent.received_configs)
        )
        self.assertTrue(
            any(cfg.canonical_library.max_context_tokens == 50 for cfg in FakeAgent.received_configs)
        )

    def test_suite_cli_json_mode_is_machine_readable(self) -> None:
        suite = load_suite(SUITE_PATH)

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "agent.json"
            config_path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "fake-model",
                        "profile": "standard",
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("bhf_agent.eval.BHFAgent", FakeAgent):
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--suite",
                            str(SUITE_PATH),
                            "--config",
                            str(config_path),
                            "--json",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["suite_id"], "ckl-phase-15-regression-suite")
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["results"]), len(suite.cases))


if __name__ == "__main__":
    unittest.main()
