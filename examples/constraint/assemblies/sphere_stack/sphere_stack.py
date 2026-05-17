"""Two spheres stacked on a plate (single Compound export)."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/sphere_stack.step"

BASE = (100.0, 100.0, 20.0)
BALL_R = 18.0
KNOB_R = 10.0
XY = (12.0, -8.0)

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": list(BASE)},
        "ball": {"primitive": "sphere", "radius": BALL_R},
        "knob": {"primitive": "sphere", "radius": KNOB_R},
    },
    "constraints": [
        {"type": "point_plane_offset", "point": "ball.center", "plane": "base.+z", "offset": BALL_R},
        {"type": "point_plane_offset", "point": "ball.center", "plane": "base.+z", "in_plane": "x", "value": XY[0]},
        {"type": "point_plane_offset", "point": "ball.center", "plane": "base.+z", "in_plane": "y", "value": XY[1]},
        {
            "type": "point_plane_offset",
            "point": "knob.center",
            "plane": "base.+z",
            "offset": BASE[2] / 2.0 + BALL_R * 2.0 + KNOB_R,
        },
        {"type": "point_plane_offset", "point": "knob.center", "plane": "base.+z", "in_plane": "x", "value": XY[0]},
        {"type": "point_plane_offset", "point": "knob.center", "plane": "base.+z", "in_plane": "y", "value": XY[1]},
    ],
}


def _box(size: tuple[float, float, float]):
    from build123d import Box, BuildPart

    with BuildPart() as part:
        Box(*size)
    return part.part


def _sphere(radius: float):
    from build123d import BuildPart, Sphere

    with BuildPart() as part:
        Sphere(radius)
    return part.part


def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {
            "base": _box(BASE),
            "ball": _sphere(BALL_R),
            "knob": _sphere(KNOB_R),
        },
        report_path=ROOT / "out" / "assembly_sphere_stack.constraint.report.json",
    )
