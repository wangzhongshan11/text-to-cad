from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from .errors import ConstraintAssemblyError
from .solver import solve_assembly, validate_only


def _load_spec(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("spec root must be an object")
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CAD assembly constraint solver")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve constraint assembly spec")
    solve_parser.add_argument("spec", type=Path, help="Path to constraints JSON")
    solve_parser.add_argument("--verbose", action="store_true")
    solve_parser.add_argument("--report-out", type=Path, help="Write compact LLM report JSON")
    solve_parser.add_argument("--transforms-out", type=Path, help="Write transforms JSON")

    validate_parser = subparsers.add_parser("validate", help="Validate spec without solving")
    validate_parser.add_argument("spec", type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            report = validate_only(_load_spec(args.spec))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        result = solve_assembly(_load_spec(args.spec), verbose=bool(args.verbose))
        llm_report = result["report"]
        print(json.dumps(llm_report, ensure_ascii=False, indent=2))

        if args.report_out is not None:
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(json.dumps(llm_report, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.transforms_out is not None:
            transforms = {
                body_id: list(matrix)
                for body_id, matrix in result["transforms"].items()
            }
            args.transforms_out.parent.mkdir(parents=True, exist_ok=True)
            args.transforms_out.write_text(
                json.dumps(transforms, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return 0 if llm_report.get("status") in {"ok", "underconstrained"} else 1
    except ConstraintAssemblyError as exc:
        if exc.report is not None:
            print(json.dumps(exc.report, ensure_ascii=False, indent=2), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
