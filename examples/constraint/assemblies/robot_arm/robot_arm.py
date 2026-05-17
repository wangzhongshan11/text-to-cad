"""6-axis style blocky robot arm: base stack (constraint) + articulated links (Location)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/robot_arm.step"

# --- Base / shoulder constraint region (mm) ---
BASE = (260.0, 260.0, 38.0)
COLUMN = (92.0, 92.0, 235.0)
SLEW = (118.0, 118.0, 30.0)
SHOULDER = (90.0, 76.0, 68.0)
MOTOR = (50.0, 56.0, 48.0)

BASE_TOP_Z = BASE[2] / 2.0


def _shoulder_pivot_z() -> float:
    return BASE_TOP_Z + COLUMN[2] + SLEW[2] + SHOULDER[2] / 2.0


def _column_center_z() -> float:
    return BASE_TOP_Z + COLUMN[2] / 2.0


def _slew_top_z() -> float:
    return BASE_TOP_Z + COLUMN[2] + SLEW[2]

# --- Arm link sizes (Location region) ---
LINK_A = (74.0, 64.0, 255.0)
LINK_B = (68.0, 290.0, 64.0)
ELBOW = (78.0, 78.0, 78.0)
LINK_C = (60.0, 60.0, 210.0)
LINK_D = (54.0, 220.0, 54.0)
WRIST = (52.0, 48.0, 52.0)
FLANGE = (62.0, 62.0, 20.0)
GRIP = (86.0, 38.0, 42.0)
FINGER = (18.0, 48.0, 32.0)


def _box(size: tuple[float, float, float]):
    with BuildPart() as part:
        Box(*size)
    return part.part


def _stack_box(
    bodies: dict,
    constraints: list,
    body_id: str,
    size: tuple[float, float, float],
    *,
    on_body: str,
    on_plane: str,
    x: float,
    y: float,
) -> None:
    bodies[body_id] = {"primitive": "box", "size": list(size)}
    constraints.extend(
        [
            {"type": "contact", "a": f"{body_id}.-z", "b": f"{on_body}.{on_plane}"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": f"{on_body}.{on_plane}",
                "offset": size[2] / 2.0,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": f"{on_body}.{on_plane}",
                "in_plane": "x",
                "value": x,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": f"{on_body}.{on_plane}",
                "in_plane": "y",
                "value": y,
            },
            {"type": "axis_parallel", "a": f"{body_id}.axis_z", "b": "base.axis_z"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "base.axis_x"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_y", "b": "base.axis_y"},
        ]
    )


def _base_constraints() -> dict:
    bodies: dict = {"base": {"primitive": "box", "size": list(BASE)}}
    constraints: list = []

    _stack_box(bodies, constraints, "column", COLUMN, on_body="base", on_plane="+z", x=0.0, y=0.0)
    _stack_box(bodies, constraints, "slew", SLEW, on_body="column", on_plane="+z", x=0.0, y=0.0)
    _stack_box(bodies, constraints, "shoulder", SHOULDER, on_body="slew", on_plane="+z", x=0.0, y=0.0)

    return {"ground": "base", "bodies": bodies, "constraints": constraints}


BASE_CONSTRAINTS = _base_constraints()


def _base_parts() -> dict:
    return {body_id: _box(tuple(body["size"])) for body_id, body in BASE_CONSTRAINTS["bodies"].items()}


def _arm_kinematics() -> dict[str, float]:
    """Shoulder pivot and elbow/wrist anchors from stacked base dimensions."""
    shoulder_z = _shoulder_pivot_z()
    reach_y = 155.0
    elbow_drop = 55.0
    return {
        "shoulder_z": shoulder_z,
        "link_a_z": shoulder_z + LINK_A[2] / 2.0 - 25.0,
        "link_b_y": reach_y,
        "link_b_z": shoulder_z + LINK_B[2] / 2.0,
        "elbow_y": reach_y + LINK_B[1] / 2.0 - 20.0,
        "elbow_z": shoulder_z + LINK_A[2] - elbow_drop,
        "link_c_z": shoulder_z + LINK_A[2] - elbow_drop - LINK_C[2] / 2.0 + 30.0,
        "link_d_y": reach_y + LINK_B[1] / 2.0 + LINK_D[1] / 2.0 - 30.0,
        "link_d_z": shoulder_z + 40.0,
        "wrist_y": reach_y + LINK_B[1] / 2.0 + LINK_D[1] - 40.0,
        "wrist_z": shoulder_z + 25.0,
    }


def _arm_and_end_effector() -> Compound:
    k = _arm_kinematics()
    children: list = [
        _box(LINK_A).moved(Location((0.0, 0.0, k["link_a_z"]))),
        _box(LINK_B).moved(Location((0.0, k["link_b_y"], k["link_b_z"]))),
        _box(ELBOW).moved(Location((0.0, k["elbow_y"], k["elbow_z"]))),
        _box(LINK_C).moved(Location((0.0, k["elbow_y"] + 25.0, k["link_c_z"]))),
        _box(LINK_D).moved(Location((0.0, k["link_d_y"], k["link_d_z"]))),
        _box(WRIST).moved(Location((0.0, k["wrist_y"], k["wrist_z"]))),
        _box(FLANGE).moved(Location((0.0, k["wrist_y"] + 18.0, k["wrist_z"] - 25.0))),
        _box(GRIP).moved(Location((0.0, k["wrist_y"] + 42.0, k["wrist_z"] - 38.0))),
        _box(FINGER).moved(Location((-22.0, k["wrist_y"] + 55.0, k["wrist_z"] - 42.0))),
        _box(FINGER).moved(Location((22.0, k["wrist_y"] + 55.0, k["wrist_z"] - 42.0))),
    ]

    # Motor pack, cable tray, counterweight, guarding (Location embellishment)
    children.append(
        _box(MOTOR).moved(
            Location((COLUMN[0] / 2.0 + MOTOR[0] / 2.0 + 14.0, 0.0, _column_center_z()))
        )
    )
    children.append(_box((28.0, 200.0, 22.0)).moved(Location((-95.0, 0.0, _column_center_z()))))
    children.append(_box((70.0, 55.0, 45.0)).moved(Location((-115.0, -70.0, BASE_TOP_Z + 30.0))))
    children.append(_box((18.0, 120.0, 90.0)).moved(Location((55.0, k["link_b_y"] - 40.0, k["link_b_z"] + 30.0))))

    for index, angle_deg in enumerate((0.0, 72.0, 144.0, 216.0, 288.0)):
        rad = math.radians(angle_deg)
        radius = 48.0
        children.append(
            _box((14.0, 14.0, 22.0)).moved(
                Location(
                    (
                        radius * math.cos(rad),
                        radius * math.sin(rad),
                        _slew_top_z() + 18.0,
                    )
                )
            )
        )

    return Compound(label="arm_chain", children=children)


def gen_step():
    base_stack = constraint_assembly(
        BASE_CONSTRAINTS,
        _base_parts(),
        report_path=ROOT / "out" / "assembly_robot_arm_base.constraint.report.json",
    )
    return build123d.Compound(label="robot_arm", children=[base_stack, _arm_and_end_effector()])


if __name__ == "__main__":
    (ROOT / "specs" / "robot_arm_base.json").write_text(
        json.dumps(BASE_CONSTRAINTS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    payload = gen_step()
    print(
        json.dumps(
            {
                "label": getattr(payload, "label", None),
                "base_bodies": len(BASE_CONSTRAINTS["bodies"]),
                "base_constraints": len(BASE_CONSTRAINTS["constraints"]),
                "total_parts": len(BASE_CONSTRAINTS["bodies"]) + 19,
            },
            ensure_ascii=False,
        )
    )
