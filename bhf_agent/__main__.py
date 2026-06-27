"""Command-line entry point for the BHF agent."""

from __future__ import annotations

import argparse
import sys
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from .config import AgentConfig, ConfigError
from .profiles import ProfileError
from .runner import BHFAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask a local model a question through the BHF Agent Core."
    )
    parser.add_argument("question", help="Biblical interpretation question")
    parser.add_argument("--config", help="Path to agent JSON config")
    parser.add_argument("--profile", help="BHF profile name")
    parser.add_argument("--base-url", help="OpenAI-compatible local base URL")
    parser.add_argument("--model", help="Local model name")
    parser.add_argument("--temperature", type=float, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, help="Maximum response tokens")
    parser.add_argument(
        "--show-debug",
        action="store_true",
        help="Show debug metadata; never prints API keys",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> AgentConfig:
    config = AgentConfig.from_json_file(args.config) if args.config else AgentConfig()
    return config.with_overrides(
        profile=args.profile,
        base_url=args.base_url,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        debug=True if args.show_debug else None,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
        result = BHFAgent(config).ask(args.question)
    except (ConfigError, ProfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(result.answer_text or "(no answer returned)")
    print()
    print("Profile:", result.profile_used)
    print("Detected question type:", _format_question_type(result))
    print("Detected reference:", _format_reference(result))
    print("Detected genre:", result.genre_context.primary_genre or "not detected")

    if result.validation_result.warnings:
        print()
        print("Validation warnings:")
        for warning in result.validation_result.warnings:
            print(f"- {warning}")

    if result.errors:
        print()
        print("Adapter errors:")
        for error in result.errors:
            print(f"- {error}")

    if config.debug:
        pipeline_debug = result.model_metadata.get("pipeline", {})
        print()
        print("Debug:")
        print("Adapter type:", result.model_metadata.get("adapter_type") or config.adapter)
        print("Base URL:", _safe_base_url(config.base_url))
        print(
            "Model:",
            result.model_metadata.get("model")
            or result.model_metadata.get("configured_model")
            or config.model
            or "not configured",
        )
        print("Profile:", result.profile_used)
        print("Question type:", _format_question_type(result))
        print("Detected reference:", _format_reference(result))
        print("Detected genre:", result.genre_context.primary_genre or "not detected")
        print("Validation score:", result.validation_result.score)
        print(
            "Pipeline stages completed:",
            ", ".join(pipeline_debug.get("stages_completed", [])) or "none",
        )
        print(
            "Prompt strategy:",
            pipeline_debug.get("prompt_strategy") or "not detected",
        )
        print(
            "Validation warnings:",
            "; ".join(result.validation_result.warnings) or "none",
        )
        print(
            "Local knowledge used:",
            ", ".join(result.model_metadata.get("local_knowledge_keys", [])) or "none",
        )
        print(
            "Output cleanup applied:",
            str(bool(result.model_metadata.get("cleanup_applied"))).lower(),
        )

    return 1 if result.errors else 0


def _format_reference(result) -> str:
    ref = result.reference_context
    if not ref.is_reference_based:
        return f"topic-only ({ref.topic or 'not detected'})"
    location = ref.book or "unknown"
    if ref.chapter is not None:
        location += f" {ref.chapter}"
    if ref.verse is not None:
        location += f":{ref.verse}"
    if ref.testament:
        location += f" [{ref.testament}]"
    return location


def _format_question_type(result) -> str:
    context = result.question_context
    formatted = context.question_type or "unknown"
    if context.target_language:
        formatted += f" [{context.target_language}]"
    return formatted


def _safe_base_url(base_url: Optional[str]) -> str:
    if not base_url:
        return "not configured"
    parts = urlsplit(base_url)
    netloc = parts.hostname or ""
    if parts.port is not None:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


if __name__ == "__main__":
    raise SystemExit(main())
