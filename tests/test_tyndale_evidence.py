import json
import zipfile
from pathlib import Path

from bhf_agent.config import AgentConfig, CommentaryConfig, CanonicalLibraryConfig
from bhf_agent.models import ChatResponse, ReferenceContext
from bhf_agent.profiles import ProfileLoader
from bhf_agent.runner import BHFAgent
from framework.commentary.evidence import (
    TyndaleEvidenceProvider,
    explicit_tyndale_request,
    format_tyndale_result_for_prompt,
    targeted_tyndale_gap,
)
from framework.commentary.importer import import_tyndale_archive


def _database(tmp_path: Path) -> Path:
    archive = tmp_path / "tyndale.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "notes.json",
            json.dumps(
                {
                    "entries": [
                        {
                            "id": "ruth-3-4",
                            "reference": "Ruth 3:4",
                            "title": "At the threshing floor",
                            "body": "The note supplies secondary historical and cultural context.",
                        }
                    ]
                }
            ),
        )
    database = tmp_path / "commentary.sqlite"
    import_tyndale_archive(archive, database)
    return database


def test_tyndale_request_gates_are_explicit_or_narrow(tmp_path):
    assert explicit_tyndale_request("What do the Tyndale study notes say about Ruth 3:4?")
    assert explicit_tyndale_request("According to the commentary, why is this important?")
    assert targeted_tyndale_gap("Explain the difficult passage", ())
    assert targeted_tyndale_gap("What is Ruth 3:4's historical setting?", ("historical setting",))
    assert not explicit_tyndale_request("Who was Boaz?")
    assert not targeted_tyndale_gap("Who was Boaz?", ())


def test_provider_returns_attributed_bounded_secondary_evidence(tmp_path):
    provider = TyndaleEvidenceProvider(_database(tmp_path), max_entries=2)
    result = provider.retrieve(
        question="What do the Tyndale notes say?",
        missing_dimensions=(),
        reference_context=ReferenceContext(book="Ruth", chapter=3, verse=4, is_reference_based=True),
        max_results=2,
    )
    prompt = format_tyndale_result_for_prompt(result)
    assert len(result.items) == 1
    assert "# SECONDARY TYNDALE EVIDENCE" in prompt
    assert "not Scripture, CKL content, lexicon data" in prompt
    assert "Tyndale House Publishers" in prompt


class _AnswerAdapter:
    def __init__(self):
        self.request = None

    def chat(self, request):
        self.request = request
        return ChatResponse(
            text="## Answer\nThe passage describes a nighttime threshing-floor encounter.\n\n## Biblical Evidence\nThe supplied passage is the primary evidence.",
            model="fake-model",
        )


def test_enabled_tyndale_is_injected_only_for_explicit_request(tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
    database = _database(tmp_path)
    config = AgentConfig(
        base_url="http://localhost:1234/v1",
        model="fake-model",
        profile="minimal-7b",
        canonical_library=CanonicalLibraryConfig(enabled=False, cache_enabled=False),
        commentary=CommentaryConfig(enabled=True, database_path=str(database)),
    )

    explicit_adapter = _AnswerAdapter()
    explicit_agent = BHFAgent(
        config,
        adapter=explicit_adapter,
        profile_loader=ProfileLoader(profile_dir),
    )
    explicit_result = explicit_agent.ask("According to the Tyndale commentary, explain Ruth 3:4.")
    assert "# SECONDARY COMMENTARY EVIDENCE" in explicit_adapter.request.system_prompt
    assert explicit_result.model_metadata["pipeline"]["tyndale_retrieval_succeeded"] is True

    ordinary_adapter = _AnswerAdapter()
    ordinary_agent = BHFAgent(
        config,
        adapter=ordinary_adapter,
        profile_loader=ProfileLoader(profile_dir),
    )
    ordinary_agent.ask("Explain Ruth 3:4.")
    assert "# SECONDARY COMMENTARY EVIDENCE" not in ordinary_adapter.request.system_prompt
