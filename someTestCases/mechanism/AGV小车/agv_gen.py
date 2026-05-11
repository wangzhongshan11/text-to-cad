# Transpiled from declarative assembly spec: AGV 小车（示意）
from build123d import *
from math import cos, sin, pi


def gen_step():
    # --- parts ---
    chassis = Box(920, 620, 140)
    wheel_fl = Cylinder(75, 55)
    wheel_fr = Cylinder(75, 55)
    wheel_rl = Cylinder(75, 55)
    wheel_rr = Cylinder(75, 55)
    mast = Box(260, 240, 420)

    # --- joints ---
    RigidJoint('rg_si__1__1__1', chassis, Plane(origin=(-460, -310, -70), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_si_1__1__1', chassis, Plane(origin=(460, -310, -70), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location)
    RigidJoint('rg_si__1_1__1', chassis, Plane(origin=(-460, 310, -70), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_si_1_1__1', chassis, Plane(origin=(460, 310, -70), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location)
    RigidJoint('rg_s_0__1_2_1', chassis, Location((0, -155, 70)))
    RigidJoint('rg_si_0_0__1', wheel_fl, Location((0, 0, -27.5)))
    RigidJoint('rg_si_0_0__1_1', wheel_fr, Location((0, 0, -27.5)))
    RigidJoint('rg_si_0_0__1_2', wheel_rl, Location((0, 0, -27.5)))
    RigidJoint('rg_si_0_0__1_3', wheel_rr, Location((0, 0, -27.5)))
    RigidJoint('rg_si_0_0__1_4', mast, Location((0, 0, -210)))

    # --- mates ---
    chassis.joints['rg_si__1__1__1'].connect_to(wheel_fl.joints['rg_si_0_0__1'])
    chassis.joints['rg_si_1__1__1'].connect_to(wheel_fr.joints['rg_si_0_0__1_1'])
    chassis.joints['rg_si__1_1__1'].connect_to(wheel_rl.joints['rg_si_0_0__1_2'])
    chassis.joints['rg_si_1_1__1'].connect_to(wheel_rr.joints['rg_si_0_0__1_3'])
    chassis.joints['rg_s_0__1_2_1'].connect_to(mast.joints['rg_si_0_0__1_4'])

    # --- assembly ---
    return Compound(children=[chassis, wheel_fl, wheel_fr, wheel_rl, wheel_rr, mast])
