"""Counterbalance forklift: chassis + 4 wheels + rear counterweight (constraint);
cab, duplex mast, carriage, forks, overhead guard, pallet load (Location)."""

from __future__ import annotations

import json
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/forklift_truck.step"

# --- Chassis constraint region (mm) ---
CHASSIS = (1320.0, 820.0, 200.0)
WHEEL = (110.0, 380.0, 110.0)
COUNTER = (420.0, 720.0, 340.0)
WHEEL_X = 500.0
WHEEL_Y = 285.0
CHASSIS_TOP_Z = CHASSIS[2] / 2.0
CHASSIS_FRONT_X = CHASSIS[0] / 2.0

# --- Location superstructure ---
CAB = (520.0, 620.0, 420.0)
SEAT = (420.0, 380.0, 95.0)
STEER = (95.0, 95.0, 280.0)
MAST_RAIL = (88.0, 58.0, 2360.0)
CARRIAGE = (520.0, 95.0, 380.0)
BACKREST = (560.0, 42.0, 520.0)
FORK = (42.0, 1180.0, 95.0)
GUARD_POST = (42.0, 42.0, 520.0)
GUARD_ROOF = (920.0, 48.0, 38.0)
HYDRAULIC = (180.0, 140.0, 260.0)
GRILLE = (320.0, 28.0, 180.0)
HEADLIGHT = (85.0, 55.0, 65.0)
MIRROR = (18.0, 95.0, 120.0)
PALLET = (1100.0, 920.0, 145.0)
LOAD_A = (380.0, 320.0, 280.0)
LOAD_B = (320.0, 280.0, 220.0)
LOAD_C = (260.0, 240.0, 180.0)


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


def _block_on_chassis(
    bodies: dict,
    constraints: list,
    body_id: str,
    size: tuple[float, float, float],
    *,
    x: float,
    y: float,
) -> None:
    bodies[body_id] = {"primitive": "box", "size": list(size)}
    constraints.extend(
        [
            {"type": "contact", "a": f"{body_id}.-z", "b": "chassis.+z"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "chassis.+z",
                "offset": size[2] / 2.0,
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
    _block_on_chassis(
        bodies,
        constraints,
        "counterweight",
        COUNTER,
        x=-(CHASSIS[0] / 2.0 - COUNTER[0] / 2.0 - 80.0),
        y=0.0,
    )
    return {"ground": "chassis", "bodies": bodies, "constraints": constraints}


CHASSIS_CONSTRAINTS = _chassis_constraints()


def _chassis_parts() -> dict:
    parts = {"chassis": _box(CHASSIS)}
    for suffix in ("fl", "fr", "rl", "rr"):
        parts[f"wheel_{suffix}"] = _box(WHEEL)
    parts["counterweight"] = _box(COUNTER)
    return parts


def _mast_base_x() -> float:
    return CHASSIS_FRONT_X - 120.0


def _mast_center_z() -> float:
    return CHASSIS_TOP_Z + MAST_RAIL[2] / 2.0 + 18.0


def _carriage_z() -> float:
    return CHASSIS_TOP_Z + 520.0 + CARRIAGE[2] / 2.0


def _fork_y_center() -> float:
    return CHASSIS[1] / 2.0 + FORK[1] / 2.0 - 60.0


def _superstructure() -> Compound:
    mx = _mast_base_x()
    mz = _mast_center_z()
    cz = _carriage_z()
    fork_y = _fork_y_center()
    cab_x = -180.0
    cab_z = CHASSIS_TOP_Z + CAB[2] / 2.0 + 24.0
    guard_z = CHASSIS_TOP_Z + GUARD_POST[2] / 2.0 + 40.0
    roof_z = guard_z + GUARD_POST[2] / 2.0 + GUARD_ROOF[2] / 2.0 + 8.0
    pallet_z = CHASSIS_TOP_Z + PALLET[2] / 2.0 + 8.0
    load_base_z = pallet_z + PALLET[2] / 2.0

    children: list = [
        _box(CAB).moved(Location((cab_x, -40.0, cab_z))),
        _box(SEAT).moved(Location((cab_x + 40.0, -120.0, CHASSIS_TOP_Z + SEAT[2] / 2.0 + 36.0))),
        _box(STEER).moved(Location((cab_x + 60.0, -80.0, CHASSIS_TOP_Z + STEER[2] / 2.0 + 120.0))),
        _box(MAST_RAIL).moved(Location((mx, -195.0, mz))),
        _box(MAST_RAIL).moved(Location((mx, 195.0, mz))),
        _box(CARRIAGE).moved(Location((mx - 40.0, 0.0, cz))),
        _box(BACKREST).moved(Location((mx - 55.0, 0.0, cz + CARRIAGE[2] / 2.0 + BACKREST[2] / 2.0 + 6.0))),
        _box(FORK).moved(Location((mx, fork_y, CHASSIS_TOP_Z + FORK[2] / 2.0 + 28.0))),
        _box(FORK).moved(Location((mx, fork_y + 130.0, CHASSIS_TOP_Z + FORK[2] / 2.0 + 28.0))),
        _box(GUARD_POST).moved(Location((cab_x - 220.0, -320.0, guard_z))),
        _box(GUARD_POST).moved(Location((cab_x + 220.0, -320.0, guard_z))),
        _box(GUARD_POST).moved(Location((cab_x - 220.0, 280.0, guard_z))),
        _box(GUARD_POST).moved(Location((cab_x + 220.0, 280.0, guard_z))),
        _box(GUARD_ROOF).moved(Location((cab_x, 0.0, roof_z))),
        _box(HYDRAULIC).moved(Location((cab_x - 280.0, 220.0, CHASSIS_TOP_Z + HYDRAULIC[2] / 2.0 + 12.0))),
        _box(GRILLE).moved(Location((CHASSIS_FRONT_X - 40.0, 0.0, CHASSIS_TOP_Z + GRILLE[2] / 2.0 + 30.0))),
        _box(HEADLIGHT).moved(Location((CHASSIS_FRONT_X - 20.0, -240.0, CHASSIS_TOP_Z + 55.0))),
        _box(HEADLIGHT).moved(Location((CHASSIS_FRONT_X - 20.0, 240.0, CHASSIS_TOP_Z + 55.0))),
        _box(MIRROR).moved(Location((cab_x + 180.0, -360.0, cab_z + 80.0))),
        _box(MIRROR).moved(Location((cab_x + 180.0, 360.0, cab_z + 80.0))),
        _box((240.0, 120.0, 28.0)).moved(Location((cab_x, -200.0, cab_z + 120.0))),
        _box(PALLET).moved(Location((mx + 80.0, fork_y + 80.0, pallet_z))),
        _box(LOAD_A).moved(Location((mx + 60.0, fork_y + 40.0, load_base_z + LOAD_A[2] / 2.0))),
        _box(LOAD_B).moved(Location((mx + 40.0, fork_y + 200.0, load_base_z + LOAD_B[2] / 2.0 + 40.0))),
        _box(LOAD_C).moved(Location((mx + 20.0, fork_y + 340.0, load_base_z + LOAD_C[2] / 2.0 + 70.0))),
        _box((95.0, 95.0, 95.0)).moved(Location((mx, 0.0, cz - 120.0))),
        _box((28.0, 680.0, 18.0)).moved(Location((mx - 95.0, 0.0, CHASSIS_TOP_Z + 8.0))),
    ]
    return Compound(label="forklift_superstructure", children=children)


def gen_step():
    chassis = constraint_assembly(
        CHASSIS_CONSTRAINTS,
        _chassis_parts(),
        report_path=ROOT / "out" / "assembly_forklift_truck_chassis.constraint.report.json",
    )
    return build123d.Compound(
        label="forklift_truck",
        children=[chassis, _superstructure()],
    )


if __name__ == "__main__":
    (ROOT / "specs").mkdir(parents=True, exist_ok=True)
    (ROOT / "specs" / "forklift_truck_chassis.json").write_text(
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
                "location_parts": 27,
                "total_parts": len(CHASSIS_CONSTRAINTS["bodies"]) + 27,
            },
            ensure_ascii=False,
        )
    )
