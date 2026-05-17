"""Two cylinders on a rectangular plate at different XY positions."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/twin_cylinders.step"

PLATE = (220.0, 100.0, 10.0)
PIN_A = (10.0, 40.0)
PIN_B = (8.0, 32.0)

CONSTRAINTS = {
    "ground": "plate",
    "bodies": {
        "plate": {"primitive": "box", "size": list(PLATE)},
        "pin_a": {"primitive": "cylinder", "radius": PIN_A[0], "height": PIN_A[1]},
        "pin_b": {"primitive": "cylinder", "radius": PIN_B[0], "height": PIN_B[1]},
    },
    "initial_guess": {
        "pin_a": [-50.0, 0.0, 25.0, 0.0, 0.0, 0.0, 1.0],
        "pin_b": [55.0, 0.0, 21.0, 0.0, 0.0, 0.0, 1.0],
    },
    "constraints": [
        {"type": "contact", "a": "pin_a.-z", "b": "plate.+z"},
        {"type": "axis_parallel", "a": "pin_a.axis", "b": "plate.axis_z"},
        {"type": "point_plane_offset", "point": "pin_a.center", "plane": "plate.+z", "offset": PIN_A[1] / 2.0},
        {"type": "point_plane_offset", "point": "pin_a.center", "plane": "plate.+z", "in_plane": "x", "value": -50.0},
        {"type": "contact", "a": "pin_b.-z", "b": "plate.+z"},
        {"type": "axis_parallel", "a": "pin_b.axis", "b": "plate.axis_z"},
        {"type": "point_plane_offset", "point": "pin_b.center", "plane": "plate.+z", "offset": PIN_B[1] / 2.0},
        {"type": "point_plane_offset", "point": "pin_b.center", "plane": "plate.+z", "in_plane": "x", "value": 55.0},
    ],
}


def _plate():
    from build123d import Box, BuildPart

    with BuildPart() as part:
        Box(*PLATE)
    return part.part


def _cylinder(radius: float, height: float):
    from build123d import BuildPart, Cylinder

    with BuildPart() as part:
        Cylinder(radius=radius, height=height)
    return part.part


def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {
            "plate": _plate(),
            "pin_a": _cylinder(*PIN_A),
            "pin_b": _cylinder(*PIN_B),
        },
        report_path=ROOT / "out" / "assembly_twin_cylinders.constraint.report.json",
    )
