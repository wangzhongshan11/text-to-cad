"""Two pillars on a long base (single Compound export)."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/box_bridge.step"

BASE = (240.0, 80.0, 14.0)
PILLAR = (50.0, 40.0, 36.0)
X_OFFSETS = (-70.0, 70.0)

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": list(BASE)},
        "left": {"primitive": "box", "size": list(PILLAR)},
        "right": {"primitive": "box", "size": list(PILLAR)},
    },
    "constraints": [
        {"type": "contact", "a": "left.-z", "b": "base.+z"},
        {"type": "point_plane_offset", "point": "left.center", "plane": "base.+z", "offset": PILLAR[2] / 2.0},
        {"type": "point_plane_offset", "point": "left.center", "plane": "base.+z", "in_plane": "x", "value": X_OFFSETS[0]},
        {"type": "point_plane_offset", "point": "left.center", "plane": "base.+z", "in_plane": "y", "value": 0.0},
        {"type": "contact", "a": "right.-z", "b": "base.+z"},
        {"type": "point_plane_offset", "point": "right.center", "plane": "base.+z", "offset": PILLAR[2] / 2.0},
        {"type": "point_plane_offset", "point": "right.center", "plane": "base.+z", "in_plane": "x", "value": X_OFFSETS[1]},
        {"type": "point_plane_offset", "point": "right.center", "plane": "base.+z", "in_plane": "y", "value": 0.0},
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
            "left": _box(PILLAR),
            "right": _box(PILLAR),
        },
        report_path=ROOT / "out" / "assembly_box_bridge.constraint.report.json",
    )
