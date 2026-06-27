"""Command-line entry point for the BHF agent."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

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
        print()
        print("Debug metadata:")
        print(result.model_metadata)

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


if __name__ == "__main__":
    raise SystemExit(main())
