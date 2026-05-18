from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from .dsl import compile_v2_to_v1, layout_to_relations, relations_to_layout
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
    solve_parser.add_argument(
        "--verify-jacobian",
        action="store_true",
        help="Compare analytic vs sparse numeric Jacobian after solve (P2c-2)",
    )
    solve_parser.add_argument("--report-out", type=Path, help="Write compact LLM report JSON")
    solve_parser.add_argument("--transforms-out", type=Path, help="Write transforms JSON")

    validate_parser = subparsers.add_parser("validate", help="Validate spec without solving")
    validate_parser.add_argument("spec", type=Path)

    expand_parser = subparsers.add_parser(
        "expand",
        help="Dry-run macro expansion: emit an equivalent v1 spec (with triggered_by)",
    )
    expand_parser.add_argument("spec", type=Path, help="Path to v2 spec JSON")
    expand_parser.add_argument(
        "--out",
        type=Path,
        help="Output path for expanded spec (defaults to stdout)",
    )

    layout_to_parser = subparsers.add_parser(
        "layout-to-relations",
        help="Convert a layout dict JSON file to recommended v2 relations (P3c)",
    )
    layout_to_parser.add_argument("layout", type=Path, help="JSON layout object")
    layout_to_parser.add_argument("--ground", type=str, required=True)
    layout_to_parser.add_argument(
        "--mode",
        choices=("auto", "flat_on", "fix_to"),
        default="auto",
    )
    layout_to_parser.add_argument("--out", type=Path)

    layout_from_parser = subparsers.add_parser(
        "relations-to-layout",
        help="Export world positions from a solved v2 spec (P3c)",
    )
    layout_from_parser.add_argument("spec", type=Path)
    layout_from_parser.add_argument("--out", type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            report = validate_only(_load_spec(args.spec), spec_path=str(args.spec.resolve()))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        if args.command == "expand":
            expanded = compile_v2_to_v1(_load_spec(args.spec))
            payload = json.dumps(expanded, ensure_ascii=False, indent=2)
            if args.out is not None:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(payload, encoding="utf-8")
            else:
                print(payload)
            return 0

        if args.command == "layout-to-relations":
            layout = _load_spec(args.layout)
            relations = layout_to_relations(
                layout,
                ground=args.ground,
                mode=args.mode,
            )
            payload = json.dumps(relations, ensure_ascii=False, indent=2)
            if args.out is not None:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(payload, encoding="utf-8")
            else:
                print(payload)
            return 0

        if args.command == "relations-to-layout":
            spec = _load_spec(args.spec)
            layout = relations_to_layout(spec, spec_path=str(args.spec.resolve()))
            payload = json.dumps(layout, ensure_ascii=False, indent=2)
            if args.out is not None:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(payload, encoding="utf-8")
            else:
                print(payload)
            return 0

        result = solve_assembly(
            _load_spec(args.spec),
            spec_path=str(args.spec.resolve()),
            verbose=bool(args.verbose),
            verify_jacobian=bool(args.verify_jacobian),
        )
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

        return 0 if llm_report.get("status") in {"ok", "ok_assumed", "underconstrained"} else 1
    except ConstraintAssemblyError as exc:
        if exc.report is not None:
            print(json.dumps(exc.report, ensure_ascii=False, indent=2), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
