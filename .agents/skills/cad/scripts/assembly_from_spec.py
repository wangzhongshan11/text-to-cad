#!/usr/bin/env python3
"""
Transpile a declarative assembly JSON into build123d Python, then run ``python -m step``
to write the sibling ``*_gen.step`` and Explorer ``.*_gen.step.glb`` sidecars.

Run from anywhere; pass an absolute path or a path relative to the current working directory.

Accepted inputs
---------------
- ``<name>_assembly.json``  → writes ``<name>_gen.py`` next to the JSON
- ``assembly.json``         → writes ``assembly_gen.py`` in the same directory

Examples
--------
  .venv/Scripts/python .agents/skills/cad/scripts/assembly_from_spec.py \\
      someTestCases/furniture/wardrobe1/wardrobe1_assembly.json

  cd .agents/skills/cad/scripts
  python assembly_from_spec.py ../../../../someTestCases/mechanism/AGV小车/agv_assembly.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def _derive_gen_py(assembly_json: Path) -> Path:
    name = assembly_json.name
    if name == "assembly.json":
        return assembly_json.with_name("assembly_gen.py")
    if name.endswith("_assembly.json"):
        base = name[: -len("_assembly.json")]
        return assembly_json.with_name(f"{base}_gen.py")
    raise ValueError(
        "Assembly JSON must be named 'assembly.json' or end with '_assembly.json', "
        f"got {name!r}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transpile *_assembly.json → *_gen.py, then run CAD scripts/step (STEP + GLB).",
    )
    parser.add_argument(
        "assembly_json",
        type=Path,
        help="Path to assembly.json or <name>_assembly.json",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter for ``python -m step`` (default: current interpreter)",
    )
    parser.add_argument(
        "--no-step",
        action="store_true",
        help="Only transpile to .py; do not run scripts/step",
    )
    args = parser.parse_args(argv)

    spec_path = args.assembly_json.resolve()
    if not spec_path.is_file():
        print(f"error: file not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        gen_py = _derive_gen_py(spec_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    scripts_dir = _scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from transpile.core import TranspileError, transpile

    try:
        raw = spec_path.read_text(encoding="utf-8-sig")
        spec = json.loads(raw)
        code = transpile(spec)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    except TranspileError as exc:
        print(f"error: transpile: {exc}", file=sys.stderr)
        return 1

    gen_py.parent.mkdir(parents=True, exist_ok=True)
    gen_py.write_text(code, encoding="utf-8")
    print(f"wrote: {gen_py}")

    if args.no_step:
        return 0

    cmd = [str(args.python), "-m", "step", str(gen_py)]
    print(f"run: cwd={scripts_dir} {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(scripts_dir))
    if proc.returncode != 0:
        print(f"error: step exited with code {proc.returncode}", file=sys.stderr)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
