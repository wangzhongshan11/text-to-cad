"""AGV cart: chassis + 4 wheels (constraint); deck, battery, mast, bumpers (Location)."""

from __future__ import annotations

import json
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/agv_cart.step"

# Chassis constraint region (mm)
CHASSIS = (820.0, 620.0, 72.0)
WHEEL = (90.0, 42.0, 90.0)
WHEEL_X = 330.0
WHEEL_Y = 245.0
CHASSIS_TOP_Z = CHASSIS[2] / 2.0

# Location region
DECK = (780.0, 580.0, 16.0)
BATTERY = (420.0, 320.0, 140.0)
DRIVE = (95.0, 70.0, 55.0)
MAST_BASE = (120.0, 120.0, 28.0)
MAST = (85.0, 85.0, 320.0)
LIDAR = (95.0, 95.0, 65.0)
BUMPER_F = (720.0, 40.0, 55.0)
BUMPER_R = (720.0, 40.0, 55.0)
SKIRT = (820.0, 12.0, 45.0)
RAIL = (760.0, 18.0, 12.0)
ESTOP = (55.0, 55.0, 40.0)
CONTROLLER = (180.0, 140.0, 38.0)


def _box(size: tuple[float, float, float]):
    with BuildPart() as part:
        Box(*size)
    return part.part


def _wheel_on_chassis(
    bodies: dict,
    constraints: list,
    body_id: str,
    *,
    x: float,
    y: float,
) -> None:
    bodies[body_id] = {"primitive": "box", "size": list(WHEEL)}
    constraints.extend(
        [
            {"type": "contact", "a": f"{body_id}.-z", "b": "chassis.+z"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "chassis.+z",
                "offset": WHEEL[2] / 2.0,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "chassis.+z",
                "in_plane": "x",
                "value": x,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "chassis.+z",
                "in_plane": "y",
                "value": y,
            },
            {"type": "axis_parallel", "a": f"{body_id}.axis_z", "b": "chassis.axis_z"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "chassis.axis_x"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_y", "b": "chassis.axis_y"},
        ]
    )


def _chassis_constraints() -> dict:
    bodies: dict = {"chassis": {"primitive": "box", "size": list(CHASSIS)}}
    constraints: list = []
    for suffix, x, y in (
        ("fl", -WHEEL_X, WHEEL_Y),
        ("fr", WHEEL_X, WHEEL_Y),
        ("rl", -WHEEL_X, -WHEEL_Y),
        ("rr", WHEEL_X, -WHEEL_Y),
    ):
        _wheel_on_chassis(bodies, constraints, f"wheel_{suffix}", x=x, y=y)
    return {"ground": "chassis", "bodies": bodies, "constraints": constraints}


CHASSIS_CONSTRAINTS = _chassis_constraints()


def _chassis_parts() -> dict:
    parts = {"chassis": _box(CHASSIS)}
    for suffix in ("fl", "fr", "rl", "rr"):
        parts[f"wheel_{suffix}"] = _box(WHEEL)
    return parts


def _deck_z() -> float:
    return CHASSIS_TOP_Z + DECK[2] / 2.0 + 2.0


def _payload_compound() -> Compound:
    dz = _deck_z() + DECK[2] / 2.0
    children: list = [
        _box(DECK).moved(Location((0.0, 0.0, _deck_z()))),
        _box(BATTERY).moved(Location((-120.0, 0.0, dz + BATTERY[2] / 2.0 + 8.0))),
        _box(CONTROLLER).moved(Location((200.0, -160.0, dz + CONTROLLER[2] / 2.0 + 6.0))),
        _box(CONTROLLER).moved(Location((200.0, 160.0, dz + CONTROLLER[2] / 2.0 + 6.0))),
        _box(DRIVE).moved(Location((-WHEEL_X, -WHEEL_Y - 20.0, dz + DRIVE[2] / 2.0))),
        _box(DRIVE).moved(Location((WHEEL_X, -WHEEL_Y - 20.0, dz + DRIVE[2] / 2.0))),
        _box(MAST_BASE).moved(Location((180.0, 0.0, dz + MAST_BASE[2] / 2.0 + 4.0))),
        _box(MAST).moved(
            Location((180.0, 0.0, dz + MAST_BASE[2] + MAST[2] / 2.0 + 12.0))
        ),
        _box(LIDAR).moved(
            Location((180.0, 0.0, dz + MAST_BASE[2] + MAST[2] + LIDAR[2] / 2.0 + 16.0))
        ),
        _box(BUMPER_F).moved(Location((0.0, CHASSIS[1] / 2.0 - 28.0, CHASSIS_TOP_Z + 30.0))),
        _box(BUMPER_R).moved(Location((0.0, -CHASSIS[1] / 2.0 + 28.0, CHASSIS_TOP_Z + 30.0))),
        _box(SKIRT).moved(Location((CHASSIS[0] / 2.0 - 8.0, 0.0, CHASSIS_TOP_Z + 22.0))),
        _box(SKIRT).moved(Location((-CHASSIS[0] / 2.0 + 8.0, 0.0, CHASSIS_TOP_Z + 22.0))),
        _box(RAIL).moved(Location((0.0, 120.0, dz + RAIL[2] / 2.0 + 2.0))),
        _box(RAIL).moved(Location((0.0, -120.0, dz + RAIL[2] / 2.0 + 2.0))),
        _box(ESTOP).moved(Location((-280.0, 0.0, dz + ESTOP[2] / 2.0 + 50.0))),
        _box((40.0, 40.0, 120.0)).moved(Location((-320.0, 220.0, dz + 70.0))),
        _box((40.0, 40.0, 120.0)).moved(Location((-320.0, -220.0, dz + 70.0))),
    ]
    return Compound(label="agv_payload", children=children)


def gen_step():
    chassis = constraint_assembly(
        CHASSIS_CONSTRAINTS,
        _chassis_parts(),
        report_path=ROOT / "out" / "assembly_agv_cart_chassis.constraint.report.json",
    )
    return build123d.Compound(label="agv_cart", children=[chassis, _payload_compound()])


if __name__ == "__main__":
    (ROOT / "specs" / "agv_cart_chassis.json").write_text(
        json.dumps(CHASSIS_CONSTRAINTS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    payload = gen_step()
    print(
        json.dumps(
            {
                "label": getattr(payload, "label", None),
                "chassis_bodies": len(CHASSIS_CONSTRAINTS["bodies"]),
                "chassis_constraints": len(CHASSIS_CONSTRAINTS["constraints"]),
                "total_parts": len(CHASSIS_CONSTRAINTS["bodies"]) + 17,
            },
            ensure_ascii=False,
        )
    )
