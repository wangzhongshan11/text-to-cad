"""Vertical arm on base with edge alignment (from box_edge_align scenario)."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/edge_bracket.step"

BASE = (160.0, 120.0, 16.0)
ARM = (24.0, 18.0, 60.0)

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": list(BASE)},
        "arm": {"primitive": "box", "size": list(ARM)},
    },
    "initial_guess": {
        "arm": [-92.0, 20.0, 38.0, 0.0, 0.0, 0.0, 1.0],
    },
    "constraints": [
        {"type": "contact", "a": "arm.-z", "b": "base.+z"},
        {"type": "point_plane_offset", "point": "arm.center", "plane": "base.+z", "offset": ARM[2] / 2.0},
        {"type": "point_plane_offset", "point": "arm.center", "plane": "base.+z", "in_plane": "x", "value": -92.0},
        {"type": "point_plane_offset", "point": "arm.center", "plane": "base.+z", "in_plane": "y", "value": 20.0},
        {"type": "contact", "a": "arm.plane_px", "b": "base.plane_nx"},
        {"type": "axis_parallel", "a": "arm.edge_px_pz", "b": "base.edge_nx_pz"},
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
            "arm": _box(ARM),
        },
        report_path=ROOT / "out" / "assembly_edge_bracket.constraint.report.json",
    )
