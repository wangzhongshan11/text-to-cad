"""Optimus Prime (Qing Tian Zhu) - stylized blocky robot figure assembly.

Coordinate convention:
  Origin: center of pelvis on the floor plane
  XY: floor/base plane
  +Z: up

Total height: approximately 320mm

Dimensions in millimeters.
"""

from build123d import *
from math import radians, sin, cos

# ---- Overall proportions ---------------------------------------------------

total_height = 320.0

# Pelvis
pelvis_width = 56.0
pelvis_depth = 40.0
pelvis_height = 30.0

# Waist/torso connector
waist_width = 36.0
waist_depth = 30.0
waist_height = 16.0

# Torso (chest)
torso_width = 68.0
torso_depth = 44.0
torso_height = 72.0

# Head
head_width = 32.0
head_depth = 28.0
head_height = 36.0

# Neck
neck_radius = 8.0
neck_height = 10.0

# Shoulders
shoulder_width = 28.0
shoulder_depth = 32.0
shoulder_height = 34.0

# Upper arms
upper_arm_width = 20.0
upper_arm_depth = 20.0
upper_arm_length = 50.0

# Elbows
elbow_radius = 12.0
elbow_width = 22.0

# Lower arms (forearms)
forearm_width = 22.0
forearm_depth = 20.0
forearm_length = 52.0

# Hands
hand_width = 24.0
hand_depth = 18.0
hand_height = 22.0

# Upper legs (thighs)
thigh_width = 24.0
thigh_depth = 24.0
thigh_length = 54.0

# Knees
knee_radius = 13.0
knee_width = 26.0

# Lower legs (shins)
shin_width = 26.0
shin_depth = 24.0
shin_length = 56.0

# Feet
foot_width = 34.0
foot_depth = 52.0
foot_height = 16.0

# Backpack (truck cab roof on back)
backpack_width = 40.0
backpack_depth = 18.0
backpack_height = 50.0

# ---- Derived positions ------------------------------------------------------

# Z heights (bottom of each part)
pelvis_z_bottom = 0.0
pelvis_z_top = pelvis_height

waist_z_bottom = pelvis_z_top
waist_z_top = waist_z_bottom + waist_height

torso_z_bottom = waist_z_top
torso_z_top = torso_z_bottom + torso_height

neck_z_bottom = torso_z_top
neck_z_top = neck_z_bottom + neck_height

head_z_bottom = neck_z_top
head_z_top = head_z_bottom + head_height

# Shoulder center Z
shoulder_center_z = torso_z_top - 10

# Hip Z (leg attachment)
hip_z = pelvis_z_bottom

# Thigh Z
thigh_z_top = hip_z
thigh_z_bottom = thigh_z_top - thigh_length

# Knee Z
knee_z = thigh_z_bottom

# Shin Z
shin_z_top = knee_z - knee_width / 2
shin_z_bottom = shin_z_top - shin_length

# Foot Z
foot_z_top = shin_z_bottom
foot_z_bottom = foot_z_top - foot_height

# Lateral positions (X offsets from center)
shoulder_x_offset = torso_width / 2 + shoulder_width / 2 - 6
hip_x_offset = pelvis_width / 2 - 6

# ---- Part builders ---------------------------------------------------------


def make_pelvis():
    """Central hip/pelvis block with side extensions."""
    with BuildPart() as p:
        # Main pelvis block
        Box(pelvis_width, pelvis_depth, pelvis_height)
        # Side hip armor plates
        for x_sign in [-1, 1]:
            with BuildSketch(Plane.XY.offset(-pelvis_height / 2 + 6)) as side:
                with Locations((x_sign * (pelvis_width / 2 + 8), 0)):
                    Circle(radius=11)
            extrude(side.sketch, amount=pelvis_height - 8)
    p.part.label = "pelvis"
    p.part.location = Location((0, 0, pelvis_height / 2))
    return p.part


def make_waist():
    """Waist/torso connector block."""
    with BuildPart() as w:
        Box(waist_width, waist_depth, waist_height)
    w.part.label = "waist"
    w.part.location = Location((0, 0, pelvis_z_top + waist_height / 2))
    return w.part


def make_torso():
    """Torso with iconic chest window panel and side details."""
    with BuildPart() as t:
        # Main torso box
        Box(torso_width, torso_depth, torso_height)
        # Chest window panels (iconic truck windshield look)
        window_panel_w = 16
        window_panel_h = 36
        for x_sign in [-1, 1]:
            with BuildSketch(Plane.XY.offset(torso_height / 2 - window_panel_h / 2 - 8)) as win:
                with Locations((x_sign * 14, -torso_depth / 2)):
                    Rectangle(window_panel_w, window_panel_h)
            extrude(win.sketch, amount=-3, mode=Mode.SUBTRACT)
        # Central vertical chest line (groove)
        with BuildSketch(Plane.XY.offset(torso_height / 2 - 24)) as groove:
            with Locations((0, -torso_depth / 2)):
                Rectangle(3, 40)
        extrude(groove.sketch, amount=-2, mode=Mode.SUBTRACT)
        # Side vents (horizontal slots)
        for z_off in [torso_height / 2 - 18, torso_height / 2 - 30]:
            with BuildSketch(Plane.XY.offset(z_off)) as vent:
                for x_sign in [-1, 1]:
                    with Locations((x_sign * (torso_width / 2), 0)):
                        Rectangle(6, 12)
            extrude(vent.sketch, amount=-4, mode=Mode.SUBTRACT)
    t.part.label = "torso"
    t.part.location = Location((0, 0, torso_z_bottom + torso_height / 2))
    return t.part


def make_neck():
    """Neck cylinder."""
    with BuildPart() as n:
        Cylinder(radius=neck_radius, height=neck_height)
    n.part.label = "neck"
    n.part.location = Location((0, 0, neck_z_bottom + neck_height / 2))
    return n.part


def make_head():
    """Head with iconic antenna crest and face mask."""
    with BuildPart() as h:
        # Main head box
        Box(head_width, head_depth, head_height)
        # Face mask plate (front)
        with BuildSketch(Plane.XY.offset(-head_height / 2 + 10)) as mask:
            with Locations((0, -head_depth / 2)):
                Rectangle(head_width - 6, head_height - 14)
        extrude(mask.sketch, amount=-3, mode=Mode.SUBTRACT)
        # Mouth vent lines
        for y_off in [-head_depth / 2]:
            with BuildSketch(Plane.XY.offset(-head_height / 2 + 22)) as mouth:
                with Locations((0, y_off)):
                    Rectangle(14, 3)
                    Rectangle(14, 3, rotation=90)
            extrude(mouth.sketch, amount=-2, mode=Mode.SUBTRACT)
        # Eyes (horizontal slots at upper face)
        for x_sign in [-1, 1]:
            with BuildSketch(Plane.XY.offset(head_height / 2 - 10)) as eye:
                with Locations((x_sign * 8, -head_depth / 2)):
                    Rectangle(8, 3)
            extrude(eye.sketch, amount=-2, mode=Mode.SUBTRACT)
    h.part.label = "head"
    h.part.location = Location((0, 0, head_z_bottom + head_height / 2))
    return h.part


def make_head_crest():
    """Iconic antenna/ear fin crest on top sides of head."""
    crest_parts = []
    for x_sign in [-1, 1]:
        with BuildPart() as fin:
            with BuildSketch(Plane.XZ.offset(x_sign * (head_width / 2 - 2))) as fin_sk:
                # Triangular crest shape
                with BuildLine() as fin_line:
                    Polyline(
                        (0, 0),
                        (-8, 18),
                        (2, 14),
                        (4, 0),
                        close=True,
                    )
                make_face()
            extrude(amount=4)
        fin.part.label = f"crest_{'left' if x_sign < 0 else 'right'}"
        fin.part.location = Location(
            (0, x_sign * (head_width / 2 - 2) + (2 if x_sign > 0 else -2),
             head_z_top),
            (0, 0, 0),
        )
        crest_parts.append(fin.part)

    # Central antenna block
    with BuildPart() as antenna:
        Box(6, 4, 14)
    antenna.part.label = "antenna"
    antenna.part.location = Location((0, 0, head_z_top + 7))
    crest_parts.append(antenna.part)

    return Compound(label="head_crest", children=crest_parts)


def make_shoulder(x_sign):
    """Shoulder armor block on one side."""
    with BuildPart() as s:
        # Main shoulder block
        Box(shoulder_width, shoulder_depth, shoulder_height)
        # Top shoulder pad extension
        with BuildSketch(Plane.XY.offset(shoulder_height / 2 - 6)) as pad:
            Rectangle(shoulder_width + 6, shoulder_depth + 4)
        extrude(pad.sketch, amount=8)
    s.part.label = f"shoulder_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * shoulder_x_offset
    s.part.location = Location((x_center, 0, shoulder_center_z))
    return s.part


def make_upper_arm(x_sign):
    """Upper arm (bicep) block."""
    with BuildPart() as ua:
        Box(upper_arm_width, upper_arm_depth, upper_arm_length)
        # Armor band detail near shoulder
        with BuildSketch(Plane.XY.offset(upper_arm_length / 2 - 8)) as band:
            Rectangle(upper_arm_width + 4, upper_arm_depth + 4)
            Rectangle(upper_arm_width, upper_arm_depth, mode=Mode.SUBTRACT)
        extrude(band.sketch, amount=5)
    ua.part.label = f"upper_arm_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * shoulder_x_offset * 1.05
    ua_z_center = shoulder_center_z - shoulder_height / 2 - upper_arm_length / 2
    ua.part.location = Location((x_center, 0, ua_z_center))
    return ua.part


def make_elbow(x_sign):
    """Elbow joint cylinder."""
    with BuildPart() as e:
        Cylinder(radius=elbow_radius, height=elbow_width, rotation=(0, 90, 0))
    e.part.label = f"elbow_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * shoulder_x_offset * 1.05
    e_z_center = shoulder_center_z - shoulder_height / 2 - upper_arm_length
    e.part.location = Location((x_center, 0, e_z_center))
    return e.part


def make_forearm(x_sign):
    """Forearm block."""
    with BuildPart() as fa:
        Box(forearm_width, forearm_depth, forearm_length)
        # Wrist detail
        with BuildSketch(Plane.XY.offset(-forearm_length / 2 + 6)) as wrist:
            Rectangle(forearm_width + 6, forearm_depth + 6)
            Rectangle(forearm_width - 2, forearm_depth - 2, mode=Mode.SUBTRACT)
        extrude(wrist.sketch, amount=6)
    fa.part.label = f"forearm_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * shoulder_x_offset * 1.05
    fa_z_center = shoulder_center_z - shoulder_height / 2 - upper_arm_length - elbow_width / 2 - forearm_length / 2
    fa.part.location = Location((x_center, 0, fa_z_center))
    return fa.part


def make_hand(x_sign):
    """Simple blocky fist."""
    with BuildPart() as h:
        Box(hand_width, hand_depth, hand_height)
    h.part.label = f"hand_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * shoulder_x_offset * 1.05
    h_z_center = shoulder_center_z - shoulder_height / 2 - upper_arm_length - elbow_width / 2 - forearm_length - hand_height / 2
    h.part.location = Location((x_center, 0, h_z_center))
    return h.part


def make_thigh(x_sign):
    """Upper leg (thigh) block."""
    with BuildPart() as th:
        Box(thigh_width, thigh_depth, thigh_length)
        # Thigh armor plate on front
        with BuildSketch(Plane.XY.offset(-thigh_length / 2 + 10)) as plate:
            with Locations((0, -thigh_depth / 2)):
                Rectangle(thigh_width - 4, thigh_length - 16)
        extrude(plate.sketch, amount=-3, mode=Mode.SUBTRACT)
    th.part.label = f"thigh_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * hip_x_offset
    th_z_center = hip_z - thigh_length / 2
    th.part.location = Location((x_center, 0, th_z_center))
    return th.part


def make_knee(x_sign):
    """Knee joint cylinder."""
    with BuildPart() as k:
        Cylinder(radius=knee_radius, height=knee_width, rotation=(0, 90, 0))
    k.part.label = f"knee_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * hip_x_offset
    k_z_center = hip_z - thigh_length - knee_width / 2
    k.part.location = Location((x_center, 0, k_z_center))
    return k.part


def make_shin(x_sign):
    """Lower leg (shin) block."""
    with BuildPart() as sh:
        Box(shin_width, shin_depth, shin_length)
    sh.part.label = f"shin_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * hip_x_offset
    sh_z_center = hip_z - thigh_length - knee_width - shin_length / 2
    sh.part.location = Location((x_center, 0, sh_z_center))
    return sh.part


def make_foot(x_sign):
    """Foot with toe detail."""
    with BuildPart() as f:
        # Main foot block
        Box(foot_width, foot_depth, foot_height)
        # Front toe segment
        with BuildSketch(Plane.XY.offset(-foot_height / 2 + 3)) as toe:
            with Locations((0, -foot_depth / 2 + 10)):
                Rectangle(foot_width - 6, 16)
        extrude(toe.sketch, amount=3)
    f.part.label = f"foot_{'left' if x_sign < 0 else 'right'}"
    x_center = x_sign * hip_x_offset
    f_z_center = hip_z - thigh_length - knee_width - shin_length - foot_height / 2
    f.part.location = Location((x_center, 0, f_z_center))
    return f.part


def make_backpack():
    """Backpack block (truck cab rear)."""
    with BuildPart() as bp:
        Box(backpack_width, backpack_depth, backpack_height)
        # Vertical line details
        for x_off in [-8, 0, 8]:
            with BuildSketch(Plane.XY.offset(0)) as line:
                with Locations((x_off, -backpack_depth / 2)):
                    Rectangle(2, backpack_height - 8)
            extrude(line.sketch, amount=-2, mode=Mode.SUBTRACT)
    bp.part.label = "backpack"
    bp_z_center = torso_z_bottom + backpack_height / 2
    bp.part.location = Location((0, torso_depth / 2 + backpack_depth / 2, bp_z_center))
    return bp.part


def make_waist_skirt():
    """Armored skirt plates around waist/pelvis."""
    skirt_parts = []
    for y_sign in [-1, 1]:
        with BuildPart() as plate:
            with BuildSketch(Plane.XZ.offset(y_sign * (pelvis_depth / 2 + 3))) as sk:
                # Trapezoidal skirt plate
                with BuildLine() as sk_line:
                    Polyline(
                        (-pelvis_width / 2 + 4, 0),
                        ( pelvis_width / 2 - 4, 0),
                        ( pelvis_width / 2 - 10, -16),
                        (-pelvis_width / 2 + 10, -16),
                        close=True,
                    )
                make_face()
            extrude(amount=3)
        plate.part.label = f"skirt_{'front' if y_sign < 0 else 'back'}"
        plate.part.location = Location(
            (0, y_sign * (pelvis_depth / 2 + 3) + (1.5 if y_sign > 0 else -1.5),
             pelvis_z_top - 4)
        )
        skirt_parts.append(plate.part)
    return Compound(label="waist_skirt", children=skirt_parts)


# ---- Exhaust pipes on shoulders --------------------------------------------

def make_exhaust_pipes():
    """Twin exhaust pipes behind the shoulders (iconic Optimus trait)."""
    pipes = []
    for x_sign in [-1, 1]:
        for pipe_idx in range(2):
            y_off = -8 + pipe_idx * 16
            with BuildPart() as pipe:
                Cylinder(radius=5, height=38, rotation=(0, 90, 0))
                # Pipe end cap
                with BuildSketch(Plane.XZ.offset(-19)) as cap:
                    Circle(radius=7)
                    Circle(radius=4, mode=Mode.SUBTRACT)
                extrude(cap.sketch, amount=4)
            pipe.part.label = f"pipe_{'left' if x_sign < 0 else 'right'}_{pipe_idx + 1}"
            pipe.part.location = Location(
                (x_sign * (shoulder_x_offset - 8), y_off, shoulder_center_z)
            )
            pipes.append(pipe.part)
    return Compound(label="exhaust_pipes", children=pipes)


# ---- Assembly --------------------------------------------------------------

def gen_step():
    children = []

    # Pelvis and waist
    children.append(make_pelvis())
    children.append(make_waist())
    children.append(make_waist_skirt())

    # Torso and back
    children.append(make_torso())
    children.append(make_backpack())

    # Neck and head
    children.append(make_neck())
    children.append(make_head())
    children.append(make_head_crest())

    # Arms (left and right)
    for x_sign in [-1, 1]:
        children.append(make_shoulder(x_sign))
        children.append(make_upper_arm(x_sign))
        children.append(make_elbow(x_sign))
        children.append(make_forearm(x_sign))
        children.append(make_hand(x_sign))

    # Exhaust pipes behind shoulders
    children.append(make_exhaust_pipes())

    # Legs (left and right)
    for x_sign in [-1, 1]:
        children.append(make_thigh(x_sign))
        children.append(make_knee(x_sign))
        children.append(make_shin(x_sign))
        children.append(make_foot(x_sign))

    assembly = Compound(label="optimus_prime", children=children)
    return assembly


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "cad", "scripts"))
    result = gen_step()
    print(f"Generated: {result.label}, children: {len(result.children)}")