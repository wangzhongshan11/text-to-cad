"""6-DOF articulated robotic arm - parametric build123d assembly.

Coordinate convention:
  Origin: center of base plate on the floor plane
  XY: floor/base plane
  +Z: up

Joint layout:
  J1 - Base rotation (Z axis)
  J2 - Shoulder pitch (Y axis)
  J3 - Elbow pitch (Y axis)
  J4 - Wrist roll (forearm axis)
  J5 - Wrist pitch (Y axis)
  J6 - Tool flange rotation (end axis)

Dimensions in millimeters, angles in degrees.
"""

from build123d import *
from math import radians, sin, cos

# ---- Key dimensions --------------------------------------------------------

# Base
base_plate_radius = 120.0
base_plate_height = 25.0
base_turret_radius = 65.0
base_turret_height = 60.0

# Shoulder (offset from base center)
shoulder_offset_z = base_plate_height + base_turret_height
shoulder_radius = 40.0
shoulder_width = 90.0

# Upper arm
upper_arm_length = 300.0
upper_arm_width = 60.0
upper_arm_thickness = 50.0

# Elbow
elbow_radius = 32.0
elbow_width = 70.0

# Forearm
forearm_length = 250.0
forearm_width = 48.0
forearm_thickness = 40.0

# Wrist assembly
wrist_roll_length = 55.0
wrist_roll_radius = 22.0
wrist_pitch_radius = 20.0
wrist_pitch_width = 50.0

# Tool flange
flange_radius = 28.0
flange_length = 18.0
flange_bolt_radius = 22.0
flange_bolt_count = 4
flange_bolt_hole_diameter = 5.0

# Motor housings (visual cylinders at each joint)
motor_housing_radius = 22.0
motor_housing_length = 55.0

# Joint angles for neutral pose (degrees)
joint_angle_1 = 0.0     # base rotation
joint_angle_2 = -30.0   # shoulder pitch (forward lean)
joint_angle_3 = 45.0    # elbow pitch
joint_angle_4 = 0.0     # wrist roll
joint_angle_5 = -20.0   # wrist pitch
joint_angle_6 = 0.0     # tool rotation


# ---- Part builders ---------------------------------------------------------

def make_base_plate():
    with BuildPart() as bp:
        Cylinder(radius=base_plate_radius, height=base_plate_height)
        # Mounting holes on a bolt circle
        bolt_circle_r = base_plate_radius - 15.0
        for i in range(6):
            angle = radians(i * 60)
            with Locations((bolt_circle_r * cos(angle), bolt_circle_r * sin(angle))):
                Hole(radius=4.25, depth=base_plate_height)
    bp.part.label = "base_plate"
    bp.part.location = Location((0, 0, base_plate_height / 2))
    return bp.part


def make_base_turret():
    with BuildPart() as bt:
        # Main cylinder
        Cylinder(radius=base_turret_radius, height=base_turret_height)
        # Decorative groove
        with BuildSketch(
            Plane.XY.offset(base_turret_height - 12)
        ) as groove_sk:
            Circle(radius=base_turret_radius)
            Circle(radius=base_turret_radius - 5, mode=Mode.SUBTRACT)
        extrude(groove_sk.sketch, amount=-6, mode=Mode.SUBTRACT)
    bt.part.label = "base_turret"
    # Position on top of base plate
    bt.part.location = Location(
        (0, 0, base_plate_height + base_turret_height / 2)
    )
    return bt.part


def make_shoulder():
    shoulder_axis_z = base_plate_height + base_turret_height
    with BuildPart() as sh:
        # Central hub
        Cylinder(radius=shoulder_radius, height=shoulder_width, rotation=(0, 90, 0))
        # Decorative rings
        for offset in [20, -20]:
            with BuildSketch(
                Plane.XZ.offset(offset)
            ) as ring:
                Circle(radius=shoulder_radius + 5)
                Circle(radius=shoulder_radius - 2, mode=Mode.SUBTRACT)
            extrude(ring.sketch, amount=5)
    sh.part.label = "shoulder"
    # Shoulder sits on top of turret, centered in X
    sh.part.location = Location(
        (0, 0, shoulder_axis_z),
        (0, 0, 0),
    )
    return sh.part


def make_upper_arm():
    with BuildPart() as ua:
        # Main rectangular arm body
        Box(upper_arm_length, upper_arm_width, upper_arm_thickness)
    ua.part.label = "upper_arm"
    # Position: shoulder end at origin, extends in +X
    shoulder_axis_z = base_plate_height + base_turret_height
    ua.part.location = Location(
        (upper_arm_length / 2, 0, shoulder_axis_z),
    )
    return ua.part


def make_elbow_joint():
    with BuildPart() as el:
        Cylinder(radius=elbow_radius, height=elbow_width, rotation=(0, 90, 0))
        # Bearing ring details
        with BuildSketch(Plane.XZ.offset(0)) as ring:
            Circle(radius=elbow_radius + 4)
            Circle(radius=elbow_radius - 3, mode=Mode.SUBTRACT)
        extrude(ring.sketch, amount=8)
    el.part.label = "elbow"
    shoulder_axis_z = base_plate_height + base_turret_height
    el.part.location = Location(
        (upper_arm_length, 0, shoulder_axis_z),
    )
    return el.part


def make_forearm():
    with BuildPart() as fa:
        Box(forearm_length, forearm_width, forearm_thickness)
    fa.part.label = "forearm"
    shoulder_axis_z = base_plate_height + base_turret_height
    fa.part.location = Location(
        (upper_arm_length + forearm_length / 2, 0, shoulder_axis_z),
    )
    return fa.part


def make_wrist_roll():
    with BuildPart() as wr:
        Cylinder(radius=wrist_roll_radius, height=wrist_roll_length, rotation=(0, 90, 0))
        # Visual ring
        with BuildSketch(Plane.XZ.offset(0)) as ring:
            Circle(radius=wrist_roll_radius + 3)
            Circle(radius=wrist_roll_radius - 2, mode=Mode.SUBTRACT)
        extrude(ring.sketch, amount=6)
    wr.part.label = "wrist_roll"
    shoulder_axis_z = base_plate_height + base_turret_height
    wr.part.location = Location(
        (upper_arm_length + forearm_length + wrist_roll_length / 2, 0, shoulder_axis_z),
    )
    return wr.part


def make_wrist_pitch():
    with BuildPart() as wp:
        # Small pivot housing
        Cylinder(radius=wrist_pitch_radius, height=wrist_pitch_width, rotation=(0, 90, 0))
    wp.part.label = "wrist_pitch"
    shoulder_axis_z = base_plate_height + base_turret_height
    wp.part.location = Location(
        (upper_arm_length + forearm_length + wrist_roll_length,
         0, shoulder_axis_z),
    )
    return wp.part


def make_tool_flange():
    with BuildPart() as fl:
        Cylinder(radius=flange_radius, height=flange_length, rotation=(0, 90, 0))
        # Flange face plate
        with BuildSketch(Plane.XZ.offset(-flange_length / 2)) as face:
            Circle(radius=flange_radius)
        extrude(face.sketch, amount=-4)
        # Bolt holes on the face plate
        for i in range(flange_bolt_count):
            angle = radians(i * 90 + 45)
            with Locations((
                flange_bolt_radius * cos(angle),
                flange_bolt_radius * sin(angle),
            )):
                Hole(
                    radius=flange_bolt_hole_diameter / 2,
                    depth=8,
                )
    fl.part.label = "tool_flange"
    shoulder_axis_z = base_plate_height + base_turret_height
    fl.part.location = Location(
        (upper_arm_length + forearm_length + wrist_roll_length + wrist_pitch_width,
         0, shoulder_axis_z),
    )
    return fl.part


def make_motor_housing(label, location):
    """Visual motor housing cylinder at a joint."""
    with BuildPart() as mh:
        Cylinder(radius=motor_housing_radius, height=motor_housing_length)
        # Fins
        for i in range(4):
            z_offset = -motor_housing_length / 2 + 8 + i * 12
            with BuildSketch(Plane.XY.offset(z_offset)) as fin:
                Circle(radius=motor_housing_radius + 3)
                Circle(radius=motor_housing_radius - 1, mode=Mode.SUBTRACT)
            extrude(fin.sketch, amount=3)
    mh.part.label = label
    mh.part.location = location
    return mh.part


def make_gripper():
    """Simple two-finger parallel gripper at the tool flange."""
    shoulder_axis_z = base_plate_height + base_turret_height
    gripper_x = upper_arm_length + forearm_length + wrist_roll_length + wrist_pitch_width + flange_length

    fingers = []
    # Gripper base
    with BuildPart() as gb:
        Box(20, 40, 40)
    gb.part.label = "gripper_base"
    gb.part.location = Location(
        (gripper_x + 10, 0, shoulder_axis_z),
    )
    fingers.append(gb.part)

    # Two fingers
    for y_sign in [1, -1]:
        with BuildPart() as finger:
            # Finger body
            Box(8, 12, 40)
            # Fingertip pad (inward)
            with BuildSketch(Plane.XY.offset(0)) as pad:
                Rectangle(12, 4)
                Rectangle(7, 3.5, mode=Mode.SUBTRACT)
            extrude(pad.sketch, amount=-12 if y_sign > 0 else -12, mode=Mode.ADD)

        finger.part.label = f"finger_{'left' if y_sign > 0 else 'right'}"
        finger.part.location = Location(
            (gripper_x + 22, y_sign * 12, shoulder_axis_z),
        )
        fingers.append(finger.part)

    return Compound(label="gripper", children=fingers)


# ---- Assembly --------------------------------------------------------------

def gen_step():
    children = []

    # Base assembly (J1 - rotation)
    base_plate = make_base_plate()
    children.append(base_plate)

    base_turret = make_base_turret()
    children.append(base_turret)

    # Motor housings at joints
    # Shoulder motor (offset behind the shoulder in Y)
    shoulder_z = base_plate_height + base_turret_height
    shoulder_motor = make_motor_housing(
        "motor_shoulder",
        Location((-20, -shoulder_radius - motor_housing_radius - 5, shoulder_z)),
    )
    children.append(shoulder_motor)

    # Elbow motor
    elbow_motor = make_motor_housing(
        "motor_elbow",
        Location(
            (upper_arm_length - 40, shoulder_radius + motor_housing_radius + 5, shoulder_z),
        ),
    )
    children.append(elbow_motor)

    # Shoulder
    shoulder = make_shoulder()
    children.append(shoulder)

    # Upper arm
    upper_arm = make_upper_arm()
    children.append(upper_arm)

    # Elbow
    elbow = make_elbow_joint()
    children.append(elbow)

    # Forearm
    forearm = make_forearm()
    children.append(forearm)

    # Wrist motors
    wrist_roll_motor = make_motor_housing(
        "motor_wrist_roll",
        Location(
            (upper_arm_length + forearm_length - 40,
             forearm_width / 2 + motor_housing_radius + 3,
             shoulder_z),
        ),
    )
    children.append(wrist_roll_motor)

    # Wrist roll
    wrist_roll = make_wrist_roll()
    children.append(wrist_roll)

    # Wrist pitch
    wrist_pitch = make_wrist_pitch()
    children.append(wrist_pitch)

    # Tool flange
    tool_flange = make_tool_flange()
    children.append(tool_flange)

    # Gripper
    gripper = make_gripper()
    children.append(gripper)

    assembly = Compound(label="robot_arm_6dof", children=children)
    return assembly


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "cad", "scripts"))
    result = gen_step()
    print(f"Generated: {result.label}, children: {len(result.children)}")