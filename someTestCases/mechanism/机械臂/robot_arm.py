"""
4-DOF Serial Industrial Robot Arm with fixed gripper.

Based on: someTestCases/mechanism/机械臂/bom.json

Kinematic chain (base -> end-effector):
  BasePlate [ground, Z=0]
    -> J1 (revolute, +Z, +/-180deg)
      -> ShoulderLink (fastened)
        -> J2 (revolute, +Y, -135/+60deg)
          -> UpperArmLink (fastened)
            -> J3 (revolute, +Y, +/-150deg)
              -> ForearmLink (fastened)
                -> J4 (revolute, +X, +/-180deg)
                  -> WristHousing (fastened)
                    -> GripperBase (fastened)
                      -> LeftFinger + RightFinger

Units: millimeters. Origin: base plate center at floor; XY base plane; +Z up.
"""

import math
from build123d import *
from math import radians, degrees

# ============================================
# DESIGN PARAMETERS (mm)
# ============================================

# --- Base ---
base_radius      = 90.0
base_height      = 15.0
base_boss_radius = 40.0
base_boss_height = 12.0

# --- J1 (base rotation, +Z axis) ---
j1_radius   = 38.0
j1_height   = 25.0

# --- Shoulder link ---
shoulder_width  = 48.0   # X
shoulder_depth  = 42.0   # Y
shoulder_height = 60.0   # Z

# --- J2 (shoulder pitch, +Y axis) ---
j2_radius = 30.0
j2_width  = 46.0   # along Y

# --- Upper arm ---
upper_arm_width  = 38.0   # X
upper_arm_depth  = 34.0   # Y
upper_arm_length = 160.0  # Z

# --- J3 (elbow pitch, +Y axis) ---
j3_radius = 26.0
j3_width  = 40.0

# --- Forearm ---
forearm_width  = 32.0   # X
forearm_depth  = 28.0   # Y
forearm_length = 130.0  # Z

# --- J4 (wrist roll, +X axis) ---
j4_radius = 22.0
j4_length = 35.0   # along X

# --- Wrist housing ---
wrist_housing_radius = 24.0
wrist_housing_length = 28.0  # along X

# --- Gripper base ---
gripper_base_width  = 36.0
gripper_base_depth  = 30.0
gripper_base_height = 14.0

# --- Fingers ---
finger_width  = 8.0
finger_depth  = 22.0
finger_height = 50.0
finger_gap    = 18.0  # between fingers

# Joint angles (radians) for the displayed assembly pose
j1_angle_rad = radians(0)
j2_angle_rad = radians(-30)
j3_angle_rad = radians(45)
j4_angle_rad = radians(0)

# ============================================
# PART FACTORIES (each built at local origin)
# ============================================

def make_base_plate():
    """Base plate centered at origin, bottom at Z=0."""
    base = Cylinder(radius=base_radius, height=base_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    boss = Cylinder(radius=base_boss_radius, height=base_boss_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    boss = Pos(0, 0, base_height) * boss
    part = base + boss
    part.label = "BasePlate"
    part.color = "dimgray"
    return part

def make_j1_output_hub():
    body = Cylinder(radius=j1_radius, height=j1_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body.label = "J1_OutputHub"
    body.color = "steelblue"
    return body

def make_shoulder_link():
    body = Box(shoulder_width, shoulder_depth, shoulder_height,
               align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body.label = "ShoulderLink"
    body.color = "darkorange"
    return body

def make_j2_module():
    body = Cylinder(radius=j2_radius, height=j2_width,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    rotation=(90, 0, 0))
    body.label = "J2_Module"
    body.color = "steelblue"
    return body

def make_upper_arm_link():
    body = Box(upper_arm_width, upper_arm_depth, upper_arm_length,
               align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body.label = "UpperArmLink"
    body.color = "darkorange"
    return body

def make_j3_module():
    body = Cylinder(radius=j3_radius, height=j3_width,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    rotation=(90, 0, 0))
    body.label = "J3_Module"
    body.color = "steelblue"
    return body

def make_forearm_link():
    body = Box(forearm_width, forearm_depth, forearm_length,
               align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body.label = "ForearmLink"
    body.color = "darkorange"
    return body

def make_j4_module():
    body = Cylinder(radius=j4_radius, height=j4_length,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    rotation=(0, 90, 0))
    body.label = "J4_Module"
    body.color = "steelblue"
    return body

def make_wrist_housing():
    body = Cylinder(radius=wrist_housing_radius, height=wrist_housing_length,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    rotation=(0, 90, 0))
    body.label = "WristHousing"
    body.color = "dimgray"
    return body

def make_gripper_base():
    body = Box(gripper_base_width, gripper_base_depth, gripper_base_height,
               align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body.label = "GripperBase"
    body.color = "dimgray"
    return body

def make_finger(is_left=True):
    body = Box(finger_width, finger_depth, finger_height,
               align=(Align.CENTER, Align.CENTER, Align.CENTER))
    label = "LeftFinger" if is_left else "RightFinger"
    body.label = label
    body.color = "silver"
    return body

# ============================================
# HELPERS: RigidJoint definition
# ============================================

def _joint(part, label, position, z_dir=(0, 0, 1)):
    """Attach a RigidJoint to a part at the given local position and normal."""
    RigidJoint(label, part, Location(Plane( =position, z_dir=z_dir)))

def _revolute_joint(part, label, position, axis_vec):
    """Attach a RevoluteJoint to a part."""
    RevoluteJoint(label, part, axis=Axis(origin=position, direction=axis_vec))

def _orientation_from_z_to_dir(target_dir):
    """Return a Rotation that maps world +Z to target_dir.

    Uses axis-angle: rotation axis = Z cross target_dir,
    rotation angle = angle between Z and target_dir.
    """
    z = Vector(0, 0, 1)
    target = target_dir.normalized()
    # Cross product gives rotation axis; handle parallel case
    cross = z.cross(target)
    if cross.length < 1e-12:
        # Target is parallel to Z
        if target.Z > 0:
            return Rotation((0, 0, 1), 0)  # identity
        else:
            return Rotation((1, 0, 0), radians(180))  # flip
    axis = cross.normalized()
    dot = z.dot(target)
    angle = math.acos(max(-1.0, min(1.0, dot)))
    return Rotation(axis, angle)

# ============================================
# ASSEMBLY
# ============================================

def gen_step():
    """Build and assemble the complete 4-DOF robot arm.

    Uses forward kinematics: each joint pivot and orientation is computed
    by chaining Rotations from the base upward, applying joint angles at
    each revolute joint. Parts are then positioned at computed world
    coordinates using Pos and Rot operator functions.
    """

    # --- Create all parts at their local origins ---
    base          = make_base_plate()
    j1            = make_j1_output_hub()
    shoulder      = make_shoulder_link()
    j2            = make_j2_module()
    upper_arm     = make_upper_arm_link()
    j3            = make_j3_module()
    forearm       = make_forearm_link()
    j4            = make_j4_module()
    wrist         = make_wrist_housing()
    gripper_base  = make_gripper_base()
    left_finger   = make_finger(is_left=True)
    right_finger  = make_finger(is_left=False)

    # ============================================================
    # Define RigidJoints (mating datum specification)
    # ============================================================
    base_top_z = base_height + base_boss_height

    _joint(base, "top_mount", (0, 0, base_top_z), (0, 0, 1))

    _joint(j1, "input_mount",  (0, 0, -j1_height/2), (0, 0, -1))
    _joint(j1, "output_mount", (0, 0,  j1_height/2), (0, 0,  1))
    _revolute_joint(j1, "j1_pivot", (0, 0, 0), (0, 0, 1))

    _joint(shoulder, "proximal", (0, 0, -shoulder_height/2), (0, 0, -1))
    _joint(shoulder, "distal",   (0, 0,  shoulder_height/2), (0, 0,  1))

    _joint(j2, "input_mount",  (0, -j2_width/2, 0), (0, -1, 0))
    _joint(j2, "output_mount", (0,  j2_width/2, 0), (0,  1, 0))
    _revolute_joint(j2, "j2_pivot", (0, 0, 0), (0, 1, 0))

    _joint(upper_arm, "proximal", (0, 0, -upper_arm_length/2), (0, 0, -1))
    _joint(upper_arm, "distal",   (0, 0,  upper_arm_length/2), (0, 0,  1))

    _joint(j3, "input_mount",  (0, -j3_width/2, 0), (0, -1, 0))
    _joint(j3, "output_mount", (0,  j3_width/2, 0), (0,  1, 0))
    _revolute_joint(j3, "j3_pivot", (0, 0, 0), (0, 1, 0))

    _joint(forearm, "proximal", (0, 0, -forearm_length/2), (0, 0, -1))
    _joint(forearm, "distal",   (0, 0,  forearm_length/2), (0, 0,  1))

    _joint(j4, "input_mount",  (-j4_length/2, 0, 0), (-1, 0, 0))
    _joint(j4, "output_mount", ( j4_length/2, 0, 0), ( 1, 0, 0))
    _revolute_joint(j4, "j4_pivot", (0, 0, 0), (1, 0, 0))

    _joint(wrist, "mount",         (-wrist_housing_length/2, 0, 0), (-1, 0, 0))
    _joint(wrist, "tool_interface", ( wrist_housing_length/2, 0, 0), ( 1, 0, 0))

    _joint(gripper_base, "mount", (0, 0, -gripper_base_height/2), (0, 0, -1))

    # ============================================================
    # FORWARD KINEMATICS PLACEMENT
    # ============================================================
    # Kinematic chain: each revolute joint contributes a rotation,
    # each link contributes a translation along its local +Z (or +X for J4/wrist).
    #
    # In build123d 0.10.0:
    #   - Rotation(axis_vec, radians_angle) creates a rotation Location
    #   - v.rotate(Axis, degrees_angle) rotates a Vector
    #   - Pos(v) * Rotation(...) * part positions + orients a part
    #
    # J1 axis = world Z.  J2/J3 axis = world Y.
    # J4 axis = forearm direction (computed from FK chain).
    # We compute world directions explicitly using Axis/rotate.

    # --- BASE: fixed ---

    # --- J1: sits on top of base boss, rotates around world Z ---
    j1_pivot_z = base_top_z + j1_height / 2
    R_j1 = Rotation((0, 0, 1), j1_angle_rad)
    j1 = Pos(0, 0, j1_pivot_z) * R_j1 * j1

    # --- Shoulder: fastened to J1 output, extends along +Z ---
    shoulder_base_z = base_top_z + j1_height
    shoulder = Pos(0, 0, shoulder_base_z + shoulder_height / 2) * R_j1 * shoulder

    # --- J2: at shoulder distal, rotates around world Y ---
    j2_pivot_z = shoulder_base_z + shoulder_height
    R_j2 = R_j1 * Rotation((0, 1, 0), j2_angle_rad)
    # J2 output direction in world = R_j2 applied to (0, 1, 0)
    # Since we can't do Location * Vector, use Axis rotation
    j2_out_axis = Axis((0, 0, 0), (0, 1, 0))
    j2_out_dir = j2_out_axis.direction.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    j2_out_dir = j2_out_dir.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad))
    j2_pivot = Vector(0, 0, j2_pivot_z)
    j2_center = j2_pivot + j2_out_dir * (j2_width / 2)
    j2 = Pos(j2_center) * R_j2 * j2

    # --- UpperArm: fastened to J2 output ---
    # Link direction = rotated +Z
    ua_dir = Vector(0, 0, 1)
    ua_dir = ua_dir.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    ua_dir = ua_dir.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad))
    j2_out_face = j2_pivot + j2_out_dir * j2_width
    ua_center = j2_out_face + ua_dir * (upper_arm_length / 2)
    # Orientation: local Z aligns with ua_dir
    # Rotation(Z→ua_dir): axis = cross(Z, ua_dir), angle = acos(dot(Z, ua_dir))
    ua_orient = _orientation_from_z_to_dir(ua_dir)
    upper_arm = Pos(ua_center) * ua_orient * upper_arm

    # --- J3: at upper arm distal, rotates around world Y ---
    j3_pivot_pt = j2_out_face + ua_dir * upper_arm_length
    R_j3 = R_j2 * Rotation((0, 1, 0), j3_angle_rad)
    # J3 output direction: Y-axis rotated by J1+J2+J3 (all around Z or Y)
    j3_out_dir = Vector(0, 1, 0)
    j3_out_dir = j3_out_dir.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    j3_out_dir = j3_out_dir.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad + j3_angle_rad))
    j3_center = j3_pivot_pt + j3_out_dir * (j3_width / 2)
    j3 = Pos(j3_center) * R_j3 * j3

    # --- Forearm: fastened to J3 output ---
    fa_dir = Vector(0, 0, 1)
    fa_dir = fa_dir.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    fa_dir = fa_dir.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad + j3_angle_rad))
    j3_out_face = j3_pivot_pt + j3_out_dir * j3_width
    fa_center = j3_out_face + fa_dir * (forearm_length / 2)
    fa_orient = _orientation_from_z_to_dir(fa_dir)
    forearm = Pos(fa_center) * fa_orient * forearm

    # --- J4: at forearm distal, rotates around forearm's +X (fa_dir) ---
    j4_pivot_pt = j3_out_face + fa_dir * forearm_length
    # J4 axis in world = forearm direction (since J4 rotates around local +X)
    # local X = fa_dir in world
    R_j4 = R_j3 * Rotation(fa_dir, j4_angle_rad)
    j4_out_dir = Vector(1, 0, 0)  # local +X
    j4_out_dir = j4_out_dir.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    j4_out_dir = j4_out_dir.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad + j3_angle_rad))
    j4_out_dir = j4_out_dir.rotate(Axis((0,0,0), fa_dir), degrees(j4_angle_rad))
    j4_center = j4_pivot_pt + j4_out_dir * (j4_length / 2)
    j4 = Pos(j4_center) * R_j4 * j4

    # --- WristHousing: fastened to J4 output, extends along +X ---
    j4_out_face = j4_pivot_pt + j4_out_dir * j4_length
    wrist_dir = j4_out_dir
    wrist_center = j4_out_face + wrist_dir * (wrist_housing_length / 2)
    wrist = Pos(wrist_center) * R_j4 * wrist

    # --- GripperBase: mounted at wrist tool interface ---
    wrist_tool_face = j4_out_face + wrist_dir * wrist_housing_length
    gb_center = wrist_tool_face + wrist_dir * (gripper_base_depth / 2)
    gripper_base = Pos(gb_center) * R_j4 * gripper_base

    # --- Fingers: mounted on gripper base forward face ---
    gb_forward_face = wrist_tool_face + wrist_dir * gripper_base_depth
    # gripper base local Y in world = R_j4 applied to (0,1,0)
    gb_local_y = Vector(0, 1, 0)
    gb_local_y = gb_local_y.rotate(Axis((0,0,0),(0,0,1)), degrees(j1_angle_rad))
    gb_local_y = gb_local_y.rotate(Axis((0,0,0),(0,1,0)), degrees(j2_angle_rad + j3_angle_rad))
    gb_local_y = gb_local_y.rotate(Axis((0,0,0), fa_dir), degrees(j4_angle_rad))

    lf_start = gb_forward_face + gb_local_y * (finger_gap / 2)
    rf_start = gb_forward_face - gb_local_y * (finger_gap / 2)
    lf_center = lf_start + wrist_dir * (finger_depth / 2)
    rf_center = rf_start + wrist_dir * (finger_depth / 2)
    left_finger  = Pos(lf_center) * R_j4 * left_finger
    right_finger = Pos(rf_center) * R_j4 * right_finger

    # ============================================================
    # Build Compound assembly
    # ============================================================
    assembly = Compound(
        label="RobotArm",
        children=[
            base,
            j1,
            shoulder,
            j2,
            upper_arm,
            j3,
            forearm,
            j4,
            wrist,
            gripper_base,
            left_finger,
            right_finger,
        ],
    )
    return assembly


# ============================================
# URDF GENERATION
# ============================================

def gen_urdf():
    """Generate URDF envelope for the 4-DOF robot arm."""
    base_top_z = base_height + base_boss_height
    j1_half = j1_height / 2
    sh_half = shoulder_height / 2
    j2_half = j2_width / 2
    ua_half = upper_arm_length / 2
    j3_half = j3_width / 2
    fa_half = forearm_length / 2
    j4_half = j4_length / 2
    wh_half = wrist_housing_length / 2
    gb_half_d = gripper_base_depth / 2

    def m(val):
        """Convert mm to meters."""
        return val / 1000.0

    xml = """<?xml version="1.0" encoding="utf-8"?>
<robot name="4DOF_RobotArm">

  <!-- ===== BASE LINK (ground) ===== -->
  <link name="base_link">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 %s" rpy="0 0 0"/>
      <mass value="5.0"/>
      <inertia ixx="0.03" ixy="0" ixz="0" iyy="0.03" iyz="0" izz="0.05"/>
    </inertial>
  </link>

  <!-- ===== J1 (base rotation, +Z) ===== -->
  <joint name="joint_j1" type="revolute">
    <parent link="base_link"/>
    <child link="link_j1"/>
    <origin xyz="0 0 %s" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit effort="100" lower="-3.1416" upper="3.1416" velocity="3.14"/>
  </joint>
  <link name="link_j1">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="1.0"/>
      <inertia ixx="0.002" ixy="0" ixz="0" iyy="0.002" iyz="0" izz="0.003"/>
    </inertial>
  </link>

  <!-- ===== Shoulder Link (fastened to J1 output) ===== -->
  <joint name="joint_shoulder" type="fixed">
    <parent link="link_j1"/>
    <child link="link_shoulder"/>
    <origin xyz="0 0 %s" rpy="0 0 0"/>
  </joint>
  <link name="link_shoulder">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.8"/>
      <inertia ixx="0.003" ixy="0" ixz="0" iyy="0.003" iyz="0" izz="0.001"/>
    </inertial>
  </link>

  <!-- ===== J2 (shoulder pitch, +Y) ===== -->
  <joint name="joint_j2" type="revolute">
    <parent link="link_shoulder"/>
    <child link="link_j2"/>
    <origin xyz="0 0 %s" rpy="0 0 0"/>
    <axis xyz="0 1 0"/>
    <limit effort="80" lower="-2.3562" upper="1.0472" velocity="2.0"/>
  </joint>
  <link name="link_j2">
    <visual>
      <origin xyz="0 0 0" rpy="1.5708 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="1.5708 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.8"/>
      <inertia ixx="0.0015" ixy="0" ixz="0" iyy="0.0015" iyz="0" izz="0.002"/>
    </inertial>
  </link>

  <!-- ===== Upper Arm Link (fastened to J2 output) ===== -->
  <joint name="joint_upper_arm" type="fixed">
    <parent link="link_j2"/>
    <child link="link_upper_arm"/>
    <origin xyz="0 %s 0" rpy="1.5708 0 0"/>
  </joint>
  <link name="link_upper_arm">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="1.2"/>
      <inertia ixx="0.003" ixy="0" ixz="0" iyy="0.003" iyz="0" izz="0.001"/>
    </inertial>
  </link>

  <!-- ===== J3 (elbow pitch, +Y) ===== -->
  <joint name="joint_j3" type="revolute">
    <parent link="link_upper_arm"/>
    <child link="link_j3"/>
    <origin xyz="0 0 %s" rpy="0 0 0"/>
    <axis xyz="0 1 0"/>
    <limit effort="60" lower="-2.618" upper="2.618" velocity="2.5"/>
  </joint>
  <link name="link_j3">
    <visual>
      <origin xyz="0 0 0" rpy="1.5708 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="1.5708 0 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.6"/>
      <inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.0015"/>
    </inertial>
  </link>

  <!-- ===== Forearm Link (fastened to J3 output) ===== -->
  <joint name="joint_forearm" type="fixed">
    <parent link="link_j3"/>
    <child link="link_forearm"/>
    <origin xyz="0 %s 0" rpy="1.5708 0 0"/>
  </joint>
  <link name="link_forearm">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.8"/>
      <inertia ixx="0.0015" ixy="0" ixz="0" iyy="0.0015" iyz="0" izz="0.0008"/>
    </inertial>
  </link>

  <!-- ===== J4 (wrist roll, +X) ===== -->
  <joint name="joint_j4" type="revolute">
    <parent link="link_forearm"/>
    <child link="link_j4"/>
    <origin xyz="0 0 %s" rpy="0 1.5708 0"/>
    <axis xyz="1 0 0"/>
    <limit effort="40" lower="-3.1416" upper="3.1416" velocity="3.14"/>
  </joint>
  <link name="link_j4">
    <visual>
      <origin xyz="0 0 0" rpy="0 1.5708 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 1.5708 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.4"/>
      <inertia ixx="0.0003" ixy="0" ixz="0" iyy="0.0003" iyz="0" izz="0.0005"/>
    </inertial>
  </link>

  <!-- ===== Wrist Housing (fastened to J4 output) ===== -->
  <joint name="joint_wrist" type="fixed">
    <parent link="link_j4"/>
    <child link="link_wrist"/>
    <origin xyz="%s 0 0" rpy="0 0 0"/>
  </joint>
  <link name="link_wrist">
    <visual>
      <origin xyz="0 0 0" rpy="0 1.5708 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 1.5708 0"/>
      <geometry>
        <cylinder radius="%s" length="%s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.3"/>
      <inertia ixx="0.0002" ixy="0" ixz="0" iyy="0.0002" iyz="0" izz="0.0003"/>
    </inertial>
  </link>

  <!-- ===== Gripper Base (fastened to wrist) ===== -->
  <joint name="joint_gripper_base" type="fixed">
    <parent link="link_wrist"/>
    <child link="link_gripper_base"/>
    <origin xyz="%s 0 0" rpy="0 0 0"/>
  </joint>
  <link name="link_gripper_base">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.2"/>
      <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.00015"/>
    </inertial>
  </link>

  <!-- ===== Left Finger (fastened to gripper base) ===== -->
  <joint name="joint_left_finger" type="fixed">
    <parent link="link_gripper_base"/>
    <child link="link_left_finger"/>
    <origin xyz="%s %s 0" rpy="0 0 0"/>
  </joint>
  <link name="link_left_finger">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.05"/>
      <inertia ixx="1e-05" ixy="0" ixz="0" iyy="5e-06" iyz="0" izz="1e-05"/>
    </inertial>
  </link>

  <!-- ===== Right Finger (fastened to gripper base) ===== -->
  <joint name="joint_right_finger" type="fixed">
    <parent link="link_gripper_base"/>
    <child link="link_right_finger"/>
    <origin xyz="%s %s 0" rpy="0 0 0"/>
  </joint>
  <link name="link_right_finger">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <box size="%s %s %s"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.05"/>
      <inertia ixx="1e-05" ixy="0" ixz="0" iyy="5e-06" iyz="0" izz="1e-05"/>
    </inertial>
  </link>

</robot>""" % (
        # base_link: visual cylinder r, l; collision r, l; inertial z
        m(base_radius), m(base_height + base_boss_height),
        m(base_radius), m(base_height + base_boss_height),
        m(base_top_z / 2),
        # joint_j1 origin z
        m(base_top_z + j1_half),
        # link_j1 visual, collision
        m(j1_radius), m(j1_height), m(j1_radius), m(j1_height),
        # joint_shoulder origin z
        m(j1_half + sh_half),
        # link_shoulder box
        m(shoulder_width), m(shoulder_depth), m(shoulder_height),
        m(shoulder_width), m(shoulder_depth), m(shoulder_height),
        # joint_j2 origin z
        m(sh_half + j2_radius),
        # link_j2 visual, collision
        m(j2_radius), m(j2_width), m(j2_radius), m(j2_width),
        # joint_upper_arm origin y
        m(j2_half + ua_half),
        # link_upper_arm box
        m(upper_arm_width), m(upper_arm_depth), m(upper_arm_length),
        m(upper_arm_width), m(upper_arm_depth), m(upper_arm_length),
        # joint_j3 origin z
        m(ua_half + j3_radius),
        # link_j3 visual, collision
        m(j3_radius), m(j3_width), m(j3_radius), m(j3_width),
        # joint_forearm origin y
        m(j3_half + fa_half),
        # link_forearm box
        m(forearm_width), m(forearm_depth), m(forearm_length),
        m(forearm_width), m(forearm_depth), m(forearm_length),
        # joint_j4 origin z
        m(fa_half + j4_half),
        # link_j4 visual, collision
        m(j4_radius), m(j4_length), m(j4_radius), m(j4_length),
        # joint_wrist origin x
        m(j4_half + wh_half),
        # link_wrist visual, collision
        m(wrist_housing_radius), m(wrist_housing_length),
        m(wrist_housing_radius), m(wrist_housing_length),
        # joint_gripper_base origin x
        m(wh_half + gb_half_d),
        # link_gripper_base box
        m(gripper_base_width), m(gripper_base_depth), m(gripper_base_height),
        m(gripper_base_width), m(gripper_base_depth), m(gripper_base_height),
        # joint_left_finger x, y
        m(gb_half_d + finger_depth / 2), m(finger_gap / 2),
        # link_left_finger box
        m(finger_width), m(finger_depth), m(finger_height),
        m(finger_width), m(finger_depth), m(finger_height),
        # joint_right_finger x, y
        m(gb_half_d + finger_depth / 2), m(-finger_gap / 2),
        # link_right_finger box
        m(finger_width), m(finger_depth), m(finger_height),
        m(finger_width), m(finger_depth), m(finger_height),
    )

    return {
        "xml": xml,
        "urdf_output": "robot_arm.urdf",
        "explorer_metadata": {
            "kind": "texttocad-urdf-explorer",
            "schemaVersion": 3,
            "jointDefaultsByName": {
                "joint_j1": 0,
                "joint_j2": -30,
                "joint_j3": 45,
                "joint_j4": 0,
            },
            "poses": [
                {
                    "name": "home",
                    "jointValuesByName": {
                        "joint_j1": 0,
                        "joint_j2": 0,
                        "joint_j3": 0,
                        "joint_j4": 0,
                    },
                },
                {
                    "name": "reach_forward",
                    "jointValuesByName": {
                        "joint_j1": 0,
                        "joint_j2": -60,
                        "joint_j3": 90,
                        "joint_j4": 0,
                    },
                },
            ],
        }
    }