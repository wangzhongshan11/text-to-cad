# Transpiled from declarative assembly spec: 双门衣柜 wardrobe1（121×46×176 cm）
from build123d import *
from math import cos, sin, pi


def gen_step():
    # --- parts ---
    bottom_panel = Box(1210, 460, 18)
    left_panel = Box(18, 460, 1724)
    right_panel = Box(18, 460, 1724)
    back_panel = Box(1174, 5, 1724)
    mid_panel = Box(18, 460, 1724)
    top_panel = Box(1210, 460, 18)
    rod_l = Cylinder(12, 570)
    rod_r = Cylinder(12, 570)
    shelf_r = Box(570, 440, 18)
    drawer_bot = Box(560, 420, 290)
    drawer_top = Box(560, 420, 290)
    door_l = Box(607, 20, 1760)
    door_r = Box(603, 20, 1760)

    # --- joints ---
    RigidJoint('rg_c__1_0_1', bottom_panel, Location((-605, 0, 9)))
    RigidJoint('rg_c_1_0_1', bottom_panel, Location((605, 0, 9)))
    RigidJoint('rg_c_0__1_1', bottom_panel, Location((0, -230, 9)))
    RigidJoint('rg_s_0_0_1', bottom_panel, Location((0, 0, 9)))
    RigidJoint('rg_si__1_2_0__1', bottom_panel, Location((-302.5, 0, -9)))
    RigidJoint('rg_si_0_0__1', left_panel, Location((0, 0, -862)))
    RigidJoint('rg_s_1_0_7_8', left_panel, Plane(origin=(9, 0, 754.25), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location)
    RigidJoint('rg_s_0_1_0', left_panel, Plane(origin=(0, 230, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RigidJoint('rg_si_0_0__1_1', right_panel, Location((0, 0, -862)))
    RigidJoint('rg_s__1_0_7_8', right_panel, Plane(origin=(-9, 0, 754.25), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location)
    RigidJoint('rg_s__1_0__5_8', right_panel, Plane(origin=(-9, 0, -538.75), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location)
    RigidJoint('rg_s_0_1_0_1', right_panel, Plane(origin=(0, 230, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RigidJoint('rg_si_0_0__1_2', back_panel, Location((0, 0, -862)))
    RigidJoint('rg_si_0_0__1_3', mid_panel, Location((0, 0, -862)))
    RigidJoint('rg_s_0_0_1_1', mid_panel, Location((0, 0, 862)))
    RigidJoint('rg_si_0_0__1_7', top_panel, Location((0, 0, -9)))
    RigidJoint('rg_si_0_0__1_5', rod_l, Location((0, 0, -285)))
    RigidJoint('rg_si_0_0__1_6', rod_r, Location((0, 0, -285)))
    RigidJoint('rg_si_1_0__1', shelf_r, Plane(origin=(285, 0, -9), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location)
    RigidJoint('rg_si_0_0__1_4', drawer_bot, Location((0, 0, -145)))
    RigidJoint('rg_s_0_0_1_2', drawer_bot, Location((0, 0, 145)))
    RigidJoint('rg_si_0_0__1_8', drawer_top, Location((0, 0, -145)))
    RigidJoint('rg_si_0__1_0', door_l, Plane(origin=(0, -10, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)
    RigidJoint('rg_si_0__1_0_1', door_r, Plane(origin=(0, -10, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)).location)

    # --- mates ---
    bottom_panel.joints['rg_c__1_0_1'].connect_to(left_panel.joints['rg_si_0_0__1'])
    bottom_panel.joints['rg_c_1_0_1'].connect_to(right_panel.joints['rg_si_0_0__1_1'])
    bottom_panel.joints['rg_c_0__1_1'].connect_to(back_panel.joints['rg_si_0_0__1_2'])
    bottom_panel.joints['rg_s_0_0_1'].connect_to(mid_panel.joints['rg_si_0_0__1_3'])
    bottom_panel.joints['rg_si__1_2_0__1'].connect_to(drawer_bot.joints['rg_si_0_0__1_4'])
    left_panel.joints['rg_s_1_0_7_8'].connect_to(rod_l.joints['rg_si_0_0__1_5'])
    left_panel.joints['rg_s_0_1_0'].connect_to(door_l.joints['rg_si_0__1_0'])
    right_panel.joints['rg_s__1_0_7_8'].connect_to(rod_r.joints['rg_si_0_0__1_6'])
    right_panel.joints['rg_s__1_0__5_8'].connect_to(shelf_r.joints['rg_si_1_0__1'])
    right_panel.joints['rg_s_0_1_0_1'].connect_to(door_r.joints['rg_si_0__1_0_1'])
    mid_panel.joints['rg_s_0_0_1_1'].connect_to(top_panel.joints['rg_si_0_0__1_7'])
    drawer_bot.joints['rg_s_0_0_1_2'].connect_to(drawer_top.joints['rg_si_0_0__1_8'])

    # --- assembly ---
    return Compound(children=[bottom_panel, left_panel, right_panel, back_panel, mid_panel, top_panel, rod_l, rod_r, shelf_r, drawer_bot, drawer_top, door_l, door_r])
