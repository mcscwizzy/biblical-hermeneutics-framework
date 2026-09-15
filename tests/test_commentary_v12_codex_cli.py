from framework.commentary.v12_corpus import (
    CODEX_CLI,
    CodexCliV12ChapterPipeline,
    CODEX_TERRA_EFFORT,
    CODEX_TERRA_MODEL,
)


def test_codex_cli_pipeline_uses_approved_terra_high_invocation(tmp_path):
    pipeline = CodexCliV12ChapterPipeline()
    command = pipeline.command(tmp_path, tmp_path / "response.json")
    assert command[0] == str(CODEX_CLI)
    assert command[1:4] == ["exec", "--ephemeral", "--ignore-user-config"]
    assert command[command.index("-m") + 1] == CODEX_TERRA_MODEL
    assert command[command.index("-c") + 1] == f'model_reasoning_effort="{CODEX_TERRA_EFFORT}"'
    assert "--output-last-message" in command
    assert "-s" in command and command[command.index("-s") + 1] == "read-only"


def test_codex_cli_pipeline_is_not_configured_with_agent_provider():
    pipeline = CodexCliV12ChapterPipeline()
    assert pipeline.model == "gpt-5.6-terra"
    assert pipeline.effort == "high"
    assert not hasattr(pipeline, "config")
