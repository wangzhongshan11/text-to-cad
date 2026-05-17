"""Three-box tower on a base plate."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/three_box_tower.step"

BASE = (180.0, 140.0, 12.0)
MID = (80.0, 60.0, 20.0)
TOP = (35.0, 35.0, 30.0)

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": list(BASE)},
        "mid": {"primitive": "box", "size": list(MID)},
        "top": {"primitive": "box", "size": list(TOP)},
    },
    "constraints": [
        {"type": "contact", "a": "mid.-z", "b": "base.+z"},
        {"type": "point_plane_offset", "point": "mid.center", "plane": "base.+z", "offset": MID[2] / 2.0},
        {"type": "point_plane_offset", "point": "mid.center", "plane": "base.+z", "in_plane": "x", "value": 25.0},
        {"type": "point_plane_offset", "point": "mid.center", "plane": "base.+z", "in_plane": "y", "value": -10.0},
        {"type": "contact", "a": "top.-z", "b": "mid.+z"},
        {"type": "point_plane_offset", "point": "top.center", "plane": "mid.+z", "offset": TOP[2] / 2.0},
        {"type": "point_plane_offset", "point": "top.center", "plane": "mid.+z", "in_plane": "x", "value": 0.0},
        {"type": "point_plane_offset", "point": "top.center", "plane": "mid.+z", "in_plane": "y", "value": 0.0},
    ],
}


def _box(size: tuple[float, float, float]):
    from build123d import Box, BuildPart

    with BuildPart() as part:
        Box(*size)
    return part.part


def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {
            "base": _box(BASE),
            "mid": _box(MID),
            "top": _box(TOP),
        },
        report_path=ROOT / "out" / "assembly_three_box_tower.constraint.report.json",
    )
