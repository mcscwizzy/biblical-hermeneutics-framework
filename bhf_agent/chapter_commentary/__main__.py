"""CLI for BHF chapter commentary generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS

from .builder import CommentaryBuilder


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    storage_dir = Path(args.storage_dir) if args.storage_dir else RUNTIME_DATA_PATHS.data_dir / "bhf-commentary"

    # Let builder load config from .bhf/config.json if it exists
    builder = CommentaryBuilder(storage_dir, config=None)

    try:
        if args.command == "build":
            return _handle_build(builder, args)
        elif args.command == "status":
            return _handle_status(builder, args)
        elif args.command == "audit":
            return _handle_audit(builder, args)
        else:
            parser.print_help()
            return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate BHF chapter commentary for the canonical Bible."
    )
    parser.add_argument(
        "--storage-dir",
        help="Directory for storing generated commentary JSON files",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    build_parser = subparsers.add_parser(
        "build",
        help="Generate chapter commentary",
    )
    build_group = build_parser.add_mutually_exclusive_group()
    build_group.add_argument(
        "--all",
        action="store_true",
        help="Generate all canonical chapters",
    )
    build_group.add_argument(
        "--book",
        help="Generate all chapters for a specific book",
    )
    build_group.add_argument(
        "--chapter",
        help="Generate commentary for a specific chapter (format: 'Book Chapter')",
    )
    build_parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Skip already-validated chapters (default)",
    )
    build_parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Regenerate all chapters",
    )
    build_parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Regenerate only stale chapters",
    )
    build_parser.add_argument(
        "--failed-only",
        action="store_true",
        help="Regenerate only failed chapters",
    )
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if validated",
    )
    build_parser.add_argument(
        "--limit",
        type=int,
        help="Limit generation to N chapters",
    )
    build_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be generated without creating files",
    )

    subparsers.add_parser(
        "status",
        help="Show commentary generation progress",
    )

    subparsers.add_parser(
        "audit",
        help="Audit generated commentary for issues",
    )

    return parser


def _handle_build(builder: CommentaryBuilder, args: argparse.Namespace) -> int:
    """Handle build command."""
    if args.dry_run:
        chapters = builder.discover_canonical_chapters()
        print(f"Would generate {len(chapters)} canonical chapters")
        return 0

    if args.all:
        print("Generating all canonical chapters...")
        progress = builder.build_all(
            resume=args.resume,
            stale_only=args.stale_only,
            failed_only=args.failed_only,
            force=args.force,
            limit=args.limit,
        )
        _print_progress(progress)
        return 0

    if args.book:
        print(f"Generating all chapters for {args.book}...")
        progress = builder.build_book(args.book)
        _print_progress(progress)
        return 0

    if args.chapter:
        parts = args.chapter.split()
        if len(parts) < 2:
            print("error: --chapter requires 'Book Chapter' format", file=sys.stderr)
            return 1
        book = " ".join(parts[:-1])
        try:
            chapter = int(parts[-1])
        except ValueError:
            print("error: Chapter must be an integer", file=sys.stderr)
            return 1
        print(f"Generating {book} {chapter}...")
        builder.build_chapter(book, chapter)
        print(f"✓ {book} {chapter}")
        return 0

    print("error: specify --all, --book, or --chapter", file=sys.stderr)
    return 1


def _handle_status(builder: CommentaryBuilder, args: argparse.Namespace) -> int:
    """Handle status command."""
    progress = builder.get_progress()

    if progress is None:
        print("No commentary generation in progress")
        return 0

    _print_progress(progress)
    return 0


def _handle_audit(builder: CommentaryBuilder, args: argparse.Namespace) -> int:
    """Handle audit command."""
    from .storage import list_commentaries

    commentaries = list_commentaries(builder.storage_dir)

    if not commentaries:
        print("No commentary files found")
        return 0

    print(f"Found {len(commentaries)} commentary files")

    # TODO: Implement actual audit checks
    # - Validate JSON structure
    # - Check evidence references
    # - Detect entity leakage

    return 0


def _print_progress(progress: dict) -> None:
    """Print formatted progress report."""
    if isinstance(progress, dict):
        total = progress.get("total_chapters", 0)
        validated = progress.get("validated", 0)
        partial = progress.get("partial", 0)
        needs_review = progress.get("needs_review", 0)
        failed = progress.get("failed", 0)
    else:
        total = progress.total_chapters
        validated = progress.validated
        partial = progress.partial
        needs_review = progress.needs_review
        failed = progress.failed

    print()
    print("BHF Commentary Build Status")
    print()
    print(f"Total:         {total:4d}")
    print(f"Validated:     {validated:4d}")
    print(f"Partial:       {partial:4d}")
    print(f"Needs Review:  {needs_review:4d}")
    print(f"Failed:        {failed:4d}")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
