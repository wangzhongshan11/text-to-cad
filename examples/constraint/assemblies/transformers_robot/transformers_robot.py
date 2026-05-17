"""Transformers-style robot: truck chassis (constraint) + robot body (Location)."""

from __future__ import annotations

import json
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/transformers_robot.step"

# ── Truck chassis ───────────────────────────────────────────────
PLATFORM = (400.0, 180.0, 55.0)
WHEEL = (55.0, 35.0, 55.0)
WHEEL_X_FRONT = 145.0
WHEEL_X_REAR = 120.0
WHEEL_Y = 78.0
PLATFORM_TOP_Z = PLATFORM[2] / 2.0

# ── Torso ───────────────────────────────────────────────────────
PELVIS = (185.0, 135.0, 75.0)
WAIST = (155.0, 115.0, 50.0)
CHEST = (210.0, 155.0, 100.0)
CHEST_GRILLE = (170.0, 20.0, 70.0)
ABS = (55., 18.0, 35.0)

# ── Head ────────────────────────────────────────────────────────
HEAD = (90.0, 82.0, 78.0)
ANTEN_L = (12.0, 12.0, 40.0)
ANTEN_R = (12.0, 12.0, 40.0)
FACEPLATE = (65.0, 10.0, 50.0)
EYE = (22.0, 8.0, 14.0)

# ── Shoulders & Arms ────────────────────────────────────────────
SHOULDER_PAD = (70.0, 60.0, 45.0)
SHOULDER_WHEEL = (42.0, 30.0, 42.0)
UPPER_ARM = (50.0, 50.0, 115.0)
FOREARM = (44.0, 44.0, 100.0)
HAND = (58.0, 42.0, 38.0)
ARM_EXHAUST = (16.0, 16.0, 50.0)

# ── Hips & Legs ─────────────────────────────────────────────────
HIP = (65.0, 65.0, 50.0)
THIGH = (60.0, 60.0, 130.0)
KNEE = (55.0, 55.0, 45.0)
SHIN = (52.0, 52.0, 120.0)
ANKLE = (48.0, 65.0, 35.0)
FOOT = (75.0, 105.0, 42.0)
LEG_WHEEL = (38.0, 25.0, 38.0)

# ── Back / Wings ────────────────────────────────────────────────
WING = (30.0, 140.0, 18.0)
BACKPACK = (160.0, 50.0, 60.0)

# ── Bumper trim ─────────────────────────────────────────────────
BUMPER_FRONT = (130.0, 160.0, 30.0)
BUMPER_REAR = (130.0, 160.0, 30.0)
FUEL_TANK = (60.0, 25.0, 35.0)


def _box(size: tuple[float, float, float]):
    with BuildPart() as part:
        Box(*size)
    return part.part


# ── Constraint helpers ──────────────────────────────────────────

def _wheel_on_platform(
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
            {"type": "contact", "a": f"{body_id}.-z", "b": "platform.+z"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "platform.+z",
                "offset": WHEEL[2] / 2.0,
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
            {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "platform.axis_x"},
        ]
    )


def _chassis_constraints() -> dict:
    bodies: dict = {"platform": {"primitive": "box", "size": list(PLATFORM)}}
    constraints: list = []

    # Front wheels (steering axle)
    for suffix, sx in (("fl", -WHEEL_X_FRONT), ("fr", WHEEL_X_FRONT)):
        _wheel_on_platform(bodies, constraints, f"wheel_{suffix}", x=sx, y=WHEEL_Y)

    # Rear wheels (dual drive axle — inner + outer pairs)
    for suffix, sx in (("rl", -WHEEL_X_REAR), ("rr", WHEEL_X_REAR)):
        _wheel_on_platform(bodies, constraints, f"wheel_{suffix}_inner", x=sx, y=WHEEL_Y - 32)
        _wheel_on_platform(bodies, constraints, f"wheel_{suffix}_outer", x=sx, y=WHEEL_Y + 8)

    return {"ground": "platform", "bodies": bodies, "constraints": constraints}


CHASSIS_CONSTRAINTS = _chassis_constraints()


def _chassis_parts() -> dict:
    parts = {"platform": _box(PLATFORM)}
    parts["wheel_fl"] = _box(WHEEL)
    parts["wheel_fr"] = _box(WHEEL)
    for suffix in ("rl", "rr"):
        parts[f"wheel_{suffix}_inner"] = _box(WHEEL)
        parts[f"wheel_{suffix}_outer"] = _box(WHEEL)
    return parts


# ── Chassis trim ────────────────────────────────────────────────

def _chassis_trim() -> Compound:
    z = PLATFORM_TOP_Z + 6.0
    return Compound(
        label="chassis_trim",
        children=[
            _box(BUMPER_FRONT).moved(Location((0.0, PLATFORM[1] / 2 + 6, z + BUMPER_FRONT[2] / 2))),
            _box(BUMPER_REAR).moved(Location((0.0, -PLATFORM[1] / 2 - 6, z + BUMPER_REAR[2] / 2))),
            _box(FUEL_TANK).moved(Location((-140, -55, z + FUEL_TANK[2] / 2))),
            _box(FUEL_TANK).moved(Location((140, -55, z + FUEL_TANK[2] / 2))),
        ],
    )


# ── Robot body ──────────────────────────────────

def _robot_body() -> Compound:
    z0 = PLATFORM_TOP_Z

    # Torso stack (bottom-up)
    z_pelvis = z0 + PELVIS[2] / 2 + 10
    z_waist = z_pelvis + PELVIS[2] / 2 + WAIST[2] / 2
    z_chest = z_waist + WAIST[2] / 2 + CHEST[2] / 2 + 5
    z_grille = z_waist + WAIST[2] / 2 + CHEST_GRILLE[2] / 2 + 5
    z_head = z_chest + CHEST[2] / 2 + HEAD[2] / 2 + 8

    children: list = [
        # Torso core
        _box(PELVIS).moved(Location((0, -10, z_pelvis))),
        _box(WAIST).moved(Location((0, -8, z_waist))),
        _box(CHEST).moved(Location((0, 5, z_chest))),
        # Chest grille (truck front detail)
        _box(CHEST_GRILLE).moved(Location((0, 72, z_grille))),
        # Abs detail
        _box(ABS).moved(Location((0, -55, z_waist + 5))),
        # Head + face
        _box(HEAD).moved(Location((0, 35, z_head))),
        _box(FACEPLATE).moved(Location((0, 70, z_head + 5))),
        # Eyes
        _box(EYE).moved(Location((20, 72, z_head + 18))),
        _box(EYE).moved(Location((-20, 72, z_head + 18))),
        # Antennae
        _box(ANTEN_L).moved(Location((22, 55, z_head + HEAD[2] / 2 + ANTEN_L[2] / 2))),
        _box(ANTEN_R).moved(Location((-22, 55, z_head + HEAD[2] / 2 + ANTEN_R[2] / 2))),
    ]

    # Backpack
    children.append(_box(BACKPACK).moved(Location((0, -72, z_chest + 10))))

    # Wings
    for wx in (-95, 95):
        children.append(_box(WING).moved(Location((wx, -70, z_chest + 5))))

    # Shoulders + arms
    shoulder_y = 10
    shoulder_z = z_chest + 15
    for side, sx in (("L", -1), ("R", 1)):
        sign = float(sx)
        # Shoulder pad
        children.append(_box(SHOULDER_PAD).moved(Location((sign * 150, shoulder_y, shoulder_z))))
        # Shoulder wheel
        children.append(_box(SHOULDER_WHEEL).moved(Location((sign * 148, shoulder_y + 32, shoulder_z + 5))))
        # Upper arm
        children.append(_box(UPPER_ARM).moved(Location((sign * 170, shoulder_y - 15, shoulder_z - 55))))
        # Arm exhaust pipe
        children.append(_box(ARM_EXHAUST).moved(Location((sign * 178, shoulder_y + 15, shoulder_z - 30))))
        # Forearm
        children.append(_box(FOREARM).moved(Location((sign * 185, shoulder_y - 45, shoulder_z - 125))))
        # Hand
        children.append(_box(HAND).moved(Location((sign * 195, shoulder_y - 65, shoulder_z - 180))))

    # Hips + legs
    hip_z = z_pelvis - 25
    for side, sx in (("L", -1), ("R", 1)):
        sign = float(sx)
        # Hip joint
        children.append(_box(HIP).moved(Location((sign * 52, -18, hip_z + 10))))
        # Thigh
        children.append(_box(THIGH).moved(Location((sign * 55, -22, hip_z - 75))))
        # Knee
        children.append(_box(KNEE).moved(Location((sign * 55, -22, hip_z - 140))))
        # Shin
        children.append(_box(SHIN).moved(Location((sign * 57, -18, hip_z - 210))))
        # Leg wheel
        children.append(_box(LEG_WHEEL).moved(Location((sign * 68, 5, hip_z - 145))))
        # Ankle
        children.append(_box(ANKLE).moved(Location((sign * 58, 10, hip_z - 265))))
        # Foot
        children.append(_box(FOOT).moved(Location((sign * 62, 28, z0 + FOOT[2] / 2 + 4))))

    # Exhaust stacks (on the back, flanking chest)
    for ex in (-85, 85):
        children.append(_box((24, 24, 85)).moved(Location((ex, -58, z_chest + 25))))

    return Compound(label="robot_body", children=children)


# ── Entry point ─────────────────────────────────────────────────

def gen_step():
    chassis = constraint_assembly(
        CHASSIS_CONSTRAINTS,
        _chassis_parts(),
        report_path=ROOT / "out" / "assembly_transformers_chassis.constraint.report.json",
    )
    return build123d.Compound(
        label="transformers_robot",
        children=[chassis, _chassis_trim(), _robot_body()],
    )


if __name__ == "__main__":
    (ROOT / "specs" / "transformers_robot_chassis.json").write_text(
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
                "trim_parts": 4,
                "robot_body_parts": 37,
                "total_parts": len(CHASSIS_CONSTRAINTS["bodies"]) + 4 + 37,
            },
            ensure_ascii=False,
        )
    )