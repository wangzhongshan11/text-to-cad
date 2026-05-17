"""Blocky Optimus Prime: truck chassis (constraint) + robot upper body (Location)."""

from __future__ import annotations

import json
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/optimus_prime.step"

# Truck chassis (mm)
PLATFORM = (380.0, 170.0, 52.0)
WHEEL = (62.0, 30.0, 62.0)
WHEEL_X = 145.0
WHEEL_Y = 72.0
BUMPER = (120.0, 150.0, 28.0)
RAIL = (380.0, 18.0, 36.0)
PLATFORM_TOP_Z = PLATFORM[2] / 2.0

# Robot upper body offsets from platform top
PELVIS = (200.0, 130.0, 70.0)
WAIST = (170.0, 110.0, 55.0)
CHEST = (220.0, 150.0, 95.0)
CAB = (150.0, 120.0, 80.0)
WINDSHIELD = (130.0, 24.0, 70.0)
HEAD = (95.0, 85.0, 75.0)
CREST = (40.0, 70.0, 35.0)
MATRIX = (50.0, 12.0, 40.0)

ARM_UPPER = (48.0, 48.0, 110.0)
ARM_FORE = (42.0, 42.0, 95.0)
HAND = (55.0, 40.0, 35.0)
LEG_THIGH = (58.0, 58.0, 120.0)
LEG_SHIN = (50.0, 50.0, 115.0)
FOOT = (70.0, 95.0, 40.0)


def _box(size: tuple[float, float, float]):
    with BuildPart() as part:
        Box(*size)
    return part.part


def _wheel_on_platform(
    bodies: dict,
    constraints: list,
    body_id: str,
    *,
    x: float,
    y: float,
) -> None:
    _panel_on_platform(
        bodies,
        constraints,
        body_id,
        WHEEL,
        x=x,
        y=y,
        thickness_axis="x",
    )


def _panel_on_platform(
    bodies: dict,
    constraints: list,
    body_id: str,
    size: tuple[float, float, float],
    *,
    x: float,
    y: float,
    thickness_axis: str,
) -> None:
    bodies[body_id] = {"primitive": "box", "size": list(size)}
    lock = (
        {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "platform.axis_x"}
        if thickness_axis == "x"
        else {"type": "axis_parallel", "a": f"{body_id}.axis_y", "b": "platform.axis_y"}
    )
    constraints.extend(
        [
            {"type": "contact", "a": f"{body_id}.-z", "b": "platform.+z"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "platform.+z",
                "offset": size[2] / 2.0,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "platform.+z",
                "in_plane": "x",
                "value": x,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "platform.+z",
                "in_plane": "y",
                "value": y,
            },
            {"type": "axis_parallel", "a": f"{body_id}.axis_z", "b": "platform.axis_z"},
            lock,
        ]
    )


def _chassis_constraints() -> dict:
    bodies: dict = {"platform": {"primitive": "box", "size": list(PLATFORM)}}
    constraints: list = []

    for suffix, sx, sy in (
        ("fl", -WHEEL_X, WHEEL_Y),
        ("fr", WHEEL_X, WHEEL_Y),
        ("rl", -WHEEL_X, -WHEEL_Y),
        ("rr", WHEEL_X, -WHEEL_Y),
    ):
        _wheel_on_platform(bodies, constraints, f"wheel_{suffix}", x=sx, y=sy)

    return {"ground": "platform", "bodies": bodies, "constraints": constraints}


CHASSIS_CONSTRAINTS = _chassis_constraints()


def _chassis_parts() -> dict:
    parts = {"platform": _box(PLATFORM)}
    for suffix in ("fl", "fr", "rl", "rr"):
        parts[f"wheel_{suffix}"] = _box(WHEEL)
    return parts


def _chassis_trim() -> Compound:
    z = PLATFORM_TOP_Z + 8.0
    return Compound(
        label="chassis_trim",
        children=[
            _box(BUMPER).moved(Location((0.0, PLATFORM[1] / 2.0 - 30.0, z + BUMPER[2] / 2.0))),
            _box(BUMPER).moved(Location((0.0, -PLATFORM[1] / 2.0 + 30.0, z + BUMPER[2] / 2.0))),
            _box(RAIL).moved(Location((0.0, 0.0, z + RAIL[2] / 2.0))),
        ],
    )


def _robot_upper_body() -> Compound:
    z0 = PLATFORM_TOP_Z
    z_pelvis = z0 + PELVIS[2] / 2.0 + 10.0
    z_waist = z_pelvis + PELVIS[2] / 2.0 + WAIST[2] / 2.0
    z_chest = z_waist + WAIST[2] / 2.0 + CHEST[2] / 2.0 + 8.0
    z_cab = z_chest + CHEST[2] / 2.0 + CAB[2] / 2.0 - 15.0
    z_head = z_cab + CAB[2] / 2.0 + HEAD[2] / 2.0 + 5.0

    children: list = [
        _box(PELVIS).moved(Location((0.0, -15.0, z_pelvis))),
        _box(WAIST).moved(Location((0.0, -10.0, z_waist))),
        _box(CHEST).moved(Location((0.0, 5.0, z_chest))),
        _box(CAB).moved(Location((25.0, 55.0, z_cab))),
        _box(WINDSHIELD).moved(Location((30.0, 95.0, z_cab + 15.0))),
        _box(MATRIX).moved(Location((-35.0, 45.0, z_chest))),
        _box(HEAD).moved(Location((10.0, 40.0, z_head))),
        _box(CREST).moved(Location((10.0, 75.0, z_head + HEAD[2] / 2.0 + CREST[2] / 2.0 - 5.0))),
    ]

    shoulder_z = z_chest + 20.0
    for side, sx in (("L", -1.0), ("R", 1.0)):
        sign = sx
        children.append(_box(ARM_UPPER).moved(Location((sign * 155.0, 0.0, shoulder_z))))
        children.append(
            _box(ARM_FORE).moved(Location((sign * 175.0, -25.0, shoulder_z - 70.0)))
        )
        children.append(_box(HAND).moved(Location((sign * 185.0, -40.0, shoulder_z - 140.0))))

    hip_z = z_pelvis - 20.0
    for side, sx in (("L", -1.0), ("R", 1.0)):
        sign = sx
        children.append(_box(LEG_THIGH).moved(Location((sign * 55.0, -20.0, hip_z - 40.0))))
        children.append(_box(LEG_SHIN).moved(Location((sign * 58.0, -15.0, hip_z - 120.0))))
        children.append(_box(FOOT).moved(Location((sign * 60.0, 25.0, z0 + FOOT[2] / 2.0 + 4.0))))

    # exhaust stacks
    for ex, ey in ((-55.0, -55.0), (55.0, -55.0)):
        children.append(_box((28.0, 28.0, 90.0)).moved(Location((ex, ey, z_chest + 30.0))))

    return Compound(label="robot_upper", children=children)


def gen_step():
    chassis = constraint_assembly(
        CHASSIS_CONSTRAINTS,
        _chassis_parts(),
        report_path=ROOT / "out" / "assembly_optimus_prime_chassis.constraint.report.json",
    )
    return build123d.Compound(
        label="optimus_prime",
        children=[chassis, _chassis_trim(), _robot_upper_body()],
    )


if __name__ == "__main__":
    (ROOT / "specs" / "optimus_prime_chassis.json").write_text(
        json.dumps(CHASSIS_CONSTRAINTS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    payload = gen_step()
    print(
        json.dumps(
            {
                "label": getattr(payload, "label", None),
                "chassis_bodies": len(CHASSIS_CONSTRAINTS["bodies"]),
                "total_parts": 5 + 3 + 22,
                "chassis_constraints": len(CHASSIS_CONSTRAINTS["constraints"]),
                "upper_parts": 22,
            },
            ensure_ascii=False,
        )
    )
