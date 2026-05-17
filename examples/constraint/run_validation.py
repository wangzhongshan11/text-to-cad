#!/usr/bin/env python3
"""Manual validation runner for constraint assembly specs (no pytest)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / ".agents" / "skills" / "cad" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.solver import solve_assembly  # noqa: E402


SPECS_DIR = Path(__file__).resolve().parent / "specs"
OUT_DIR = Path(__file__).resolve().parent / "out"

EXPECTED = {
    "box_on_box.json": "ok",
    "two_boxes_under.json": "underconstrained",
    "two_boxes_fixed.json": "ok",
    "cylinder_on_box.json": "ok",
    "sphere_on_box.json": "ok",
    "box_edge_align.json": "ok",
    "three_box_tower.json": "ok",
    "twin_cylinders_on_plate.json": "ok",
    "sphere_on_sphere_stack.json": "ok",
    "box_bridge.json": "ok",
    "pin_grid_4x4.json": "ok",
    "wardrobe_closet.json": "ok",
    "optimus_prime_chassis.json": "ok",
    "robot_arm_base.json": "ok",
    "agv_cart_chassis.json": "ok",
    "forklift_truck_chassis.json": "ok",
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for spec_path in sorted(SPECS_DIR.glob("*.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        try:
            result = solve_assembly(spec)
        except Exception as exc:
            print(f"{spec_path.name}: ERROR {exc}")
            failures += 1
            continue
        report = result["report"]
        status = str(report.get("status"))
        expected = EXPECTED.get(spec_path.name, "ok")
        ok = status == expected
        print(f"{spec_path.name}: status={status} expected={expected} residual={report.get('residual_max')} ok={ok}")
        (OUT_DIR / f"{spec_path.stem}.report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (OUT_DIR / f"{spec_path.stem}.transforms.json").write_text(
            json.dumps(
                {body: list(matrix) for body, matrix in result["transforms"].items()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if not ok:
            failures += 1
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
