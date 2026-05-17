"""4×4 pin grid on a plate: 1 base + 16 posts (17 bodies, 64 constraints)."""

from __future__ import annotations

from pathlib import Path

from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/pin_grid_4x4.step"

BASE_SIZE = (360.0, 280.0, 14.0)
PIN_SIZE = (14.0, 14.0, 32.0)
PITCH = 70.0
ROWS = 4
COLS = 4


def _constraints() -> dict:
    bodies: dict = {
        "base": {"primitive": "box", "size": list(BASE_SIZE)},
    }
    constraints: list[dict] = []
    for row in range(ROWS):
        for col in range(COLS):
            pid = f"p_{row}_{col}"
            bodies[pid] = {"primitive": "box", "size": list(PIN_SIZE)}
            x = (col - (COLS - 1) / 2.0) * PITCH
            y = (row - (ROWS - 1) / 2.0) * PITCH
            constraints.extend(
                [
                    {"type": "contact", "a": f"{pid}.-z", "b": "base.+z"},
                    {
                        "type": "point_plane_offset",
                        "point": f"{pid}.center",
                        "plane": "base.+z",
                        "offset": PIN_SIZE[2] / 2.0,
                    },
                    {
                        "type": "point_plane_offset",
                        "point": f"{pid}.center",
                        "plane": "base.+z",
                        "in_plane": "x",
                        "value": x,
                    },
                    {
                        "type": "point_plane_offset",
                        "point": f"{pid}.center",
                        "plane": "base.+z",
                        "in_plane": "y",
                        "value": y,
                    },
                ]
            )
    return {"ground": "base", "bodies": bodies, "constraints": constraints}


CONSTRAINTS = _constraints()


def _box(size: tuple[float, float, float]):
    from build123d import Box, BuildPart

    with BuildPart() as part:
        Box(*size)
    return part.part


def _parts() -> dict:
    parts = {"base": _box(BASE_SIZE)}
    for row in range(ROWS):
        for col in range(COLS):
            parts[f"p_{row}_{col}"] = _box(PIN_SIZE)
    return parts


def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        _parts(),
        report_path=ROOT / "out" / "assembly_pin_grid_4x4.constraint.report.json",
    )
