"""Constraint-driven assembly: block on base (single Compound export)."""

from __future__ import annotations

import json
from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/box_on_box.step"

BASE_SIZE = (200.0, 150.0, 20.0)
BLOCK_SIZE = (40.0, 30.0, 25.0)
BLOCK_XY = (30.0, 40.0)

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": list(BASE_SIZE)},
        "b1": {"primitive": "box", "size": list(BLOCK_SIZE)},
    },
    "constraints": [
        {"type": "plane_coincident", "a": "b1.-z", "b": "base.+z", "opposed": True},
        {
            "type": "point_plane_offset",
            "point": "b1.center",
            "plane": "base.+z",
            "offset": BLOCK_SIZE[2] / 2.0,
        },
        {
            "type": "point_plane_offset",
            "point": "b1.center",
            "plane": "base.+z",
            "in_plane": "x",
            "value": BLOCK_XY[0],
        },
        {
            "type": "point_plane_offset",
            "point": "b1.center",
            "plane": "base.+z",
            "in_plane": "y",
            "value": BLOCK_XY[1],
        },
    ],
}


def _make_centered_box(size: tuple[float, float, float]):
    from build123d import Box, BuildPart

    with BuildPart() as part:
        Box(*size)
    return part.part


def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {
            "base": _make_centered_box(BASE_SIZE),
            "b1": _make_centered_box(BLOCK_SIZE),
        },
        report_path=ROOT / "out" / "assembly_box_on_box.constraint.report.json",
    )


if __name__ == "__main__":
    payload = gen_step()
    print(json.dumps({"label": getattr(payload, "label", None)}, ensure_ascii=False))
