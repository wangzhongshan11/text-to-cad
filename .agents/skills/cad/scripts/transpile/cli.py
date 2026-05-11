"""CLI for the declarative assembly transpiler."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from transpile.core import TranspileError, transpile_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m transpile",
        description=(
            "Transpile a declarative assembly JSON spec "
            "(model-decomposition-assembly-spec) to a build123d Python script."
        ),
    )
    parser.add_argument(
        "input",
        help="Path to the input JSON spec file.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help=(
            "Output Python file path. "
            "Defaults to <input>.py in the same directory as the input file."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the spec and print what would be generated, without writing a file.",
    )

    args = parser.parse_args(argv)

    import json
    from transpile.core import transpile

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        spec = json.loads(input_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        code = transpile(spec)
    except TranspileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print(code)
        return 0

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_path = input_path.with_suffix(".py")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code, encoding="utf-8")
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
