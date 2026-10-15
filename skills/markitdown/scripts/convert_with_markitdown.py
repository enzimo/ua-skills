#!/usr/bin/env python3
"""Convert a document or supported URL to Markdown with MarkItDown."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_command(args: argparse.Namespace) -> list[str]:
    markitdown = shutil.which("markitdown")
    if markitdown:
        command = [markitdown]
    else:
        uvx = shutil.which("uvx")
        if not uvx:
            raise RuntimeError(
                "Neither 'markitdown' nor 'uvx' is available. Install with: "
                "python -m pip install 'markitdown[all]'"
            )
        command = [uvx, "--from", "markitdown[all]", "markitdown"]

    if args.use_plugins:
        command.append("--use-plugins")

    if args.docintel_endpoint:
        command.extend(["-d", "-e", args.docintel_endpoint])

    command.append(args.source)

    if args.output:
        command.extend(["-o", str(args.output)])

    return command


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a document or supported URL to Markdown with MarkItDown."
    )
    parser.add_argument("source", help="Input file path or supported URL.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Markdown output path. If omitted, Markdown is written to stdout.",
    )
    parser.add_argument(
        "--use-plugins",
        action="store_true",
        help="Enable installed MarkItDown plugins.",
    )
    parser.add_argument(
        "--docintel-endpoint",
        help="Azure Document Intelligence endpoint to pass to MarkItDown.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    source_path = Path(args.source)
    is_url = "://" in args.source
    if not is_url and not source_path.exists():
        print(f"Input does not exist: {source_path}", file=sys.stderr)
        return 2

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        command = build_command(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 127

    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        return result.returncode

    if args.output and (not args.output.exists() or args.output.stat().st_size == 0):
        print(f"MarkItDown completed but output is empty: {args.output}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
