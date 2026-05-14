# Transpiled from declarative assembly spec: 4-DOF serial robot arm from preview schematic
from build123d import *
from math import cos, sin, pi


def gen_step():
    # --- parts ---
    base_disk = Cylinder(95, 42)
    turntable = Cylinder(76, 34)
    link1_column = Box(52, 52, 208)
    link2_forearm = Box(248, 48, 48)
    link3_upperarm = Box(198, 44, 44)
    wrist_block = Box(46, 44, 44)
    gripper_frame = Box(32, 72, 30)
    jaw_left = Box(14, 22, 52)
    jaw_right = Box(14, 22, 52)

    # --- joints ---
    RevoluteJoint('rv_s_0_0_1', base_disk,
        axis=Axis((0, 0, 21), (0, 0, 1)),
        angle_reference=(1, 0, 0))
    RigidJoint('rg_si_0_0__1', turntable, Location((0, 0, -17)))
    RigidJoint('rg_s_0_0_1', turntable, Location((0, 0, 17)))
    RigidJoint('rg_si_0_0__1_1', link1_column, Location((0, 0, -104)))
    RevoluteJoint('rv_c_0__1_1', link1_column,
        axis=Axis((0, -26, 104), (0, 1, 0)),
        angle_reference=(0, 0, 1))
    RigidJoint('rg_c__1_0_0', link2_forearm, Plane(origin=(-124, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RevoluteJoint('rv_c_1_0_1', link2_forearm,
        axis=Axis((124, 0, 24), (0, 1, 0)),
        angle_reference=(0, 0, 1))
    RigidJoint('rg_c__1_0_0_1', link3_upperarm, Plane(origin=(-99, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RevoluteJoint('rv_c_1_0_0', link3_upperarm,
        axis=Axis((99, 0, 0), (1, 0, 0)),
        angle_reference=(0, 1, 0))
    RigidJoint('rg_c__1_0_0_2', wrist_block, Plane(origin=(-23, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_s_1_0_0', wrist_block, Plane(origin=(23, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_si__1_0_0', gripper_frame, Plane(origin=(-16, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_s_0_1_0', gripper_frame, Plane(origin=(0, 36, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RigidJoint('rg_s_0__1_0', gripper_frame, Plane(origin=(0, -36, 0), x_dir=(0, 0, 1), z_dir=(0, -1, 0)).location)
    RigidJoint('rg_si_0__1_0', jaw_left, Plane(origin=(0, -11, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RigidJoint('rg_si_0_1_0', jaw_right, Plane(origin=(0, 11, 0), x_dir=(0, 0, 1), z_dir=(0, -1, 0)).location)

    # --- mates ---
    base_disk.joints['rv_s_0_0_1'].connect_to(turntable.joints['rg_si_0_0__1'], angle=0)
    turntable.joints['rg_s_0_0_1'].connect_to(link1_column.joints['rg_si_0_0__1_1'])
    link1_column.joints['rv_c_0__1_1'].connect_to(link2_forearm.joints['rg_c__1_0_0'], angle=20)
    link2_forearm.joints['rv_c_1_0_1'].connect_to(link3_upperarm.joints['rg_c__1_0_0_1'], angle=335)
    link3_upperarm.joints['rv_c_1_0_0'].connect_to(wrist_block.joints['rg_c__1_0_0_2'], angle=0)
    wrist_block.joints['rg_s_1_0_0'].connect_to(gripper_frame.joints['rg_si__1_0_0'])
    gripper_frame.joints['rg_s_0_1_0'].connect_to(jaw_left.joints['rg_si_0__1_0'])
    gripper_frame.joints['rg_s_0__1_0'].connect_to(jaw_right.joints['rg_si_0_1_0'])

    # --- assembly ---
    return Compound(children=[base_disk, turntable, link1_column, link2_forearm, link3_upperarm, wrist_block, gripper_frame, jaw_left, jaw_right])
