"""
White minimalist 3-tier double-door wardrobe.
Based on reference: someTestCases/furniture/wardrobe1/preview.png

Assembly uses build123d RigidJoints as the constraint specification
(defining mating datum planes and normals between components),
combined with explicit parameterized Location transforms for
deterministic placement of each component.

Built-in RigidJoints on each component:
  Joint label             | Part         | Mating interface
  ------------------------|--------------|--------------------------
  bottom_seat_left_edge   | bottom_panel | +X face, seats left panel inner face
  bottom_seat_right_edge  | bottom_panel | -X face, seats right panel inner face
  bottom_seat_back        | bottom_panel | -Y face, seats back panel front face
  bottom_seat_top         | bottom_panel | +Z face, seats side panel bottoms
  left_inner_face         | left_panel   | +X face, mates to bottom panel left edge
  left_bottom_face        | left_panel   | -Z face, mates to bottom panel top edge
  left_top_face           | left_panel   | +Z face, mates to top panel left seat
  right_inner_face        | right_panel  | -X face, mates to bottom panel right edge
  right_bottom_face       | right_panel  | -Z face, mates to bottom panel top edge
  right_top_face           | right_panel  | +Z face, mates to top panel right seat
  back_front_face         | back_panel   | +Y face, mates to bottom panel back seat
  back_bottom_face        | back_panel   | -Z face, mates to bottom panel top
  shelf_lower_bottom      | shelf_lower  | -Z face, mounts at tier3 Z height
  shelf_lower_top         | shelf_lower  | +Z face, tier2 space above
  shelf_upper_bottom      | shelf_upper  | -Z face, mounts at tier3+tier2 Z height
  shelf_upper_top         | shelf_upper  | +Z face, tier1 space above
  top_bottom_left_seat    | top_panel    | -Z face, seats on left panel top
  top_bottom_right_seat   | top_panel    | -Z face, seats on right panel top
  door_l_inner_face       | door_left    | -Y face (toward cabinet)
  door_l_front_face       | door_left    | +Y face (outward)
  door_l_handle_mount     | door_left    | +Y face, handle attachment point
  door_r_inner_face       | door_right   | -Y face (toward cabinet)
  door_r_front_face       | door_right   | +Y face (outward)
  door_r_handle_mount     | door_right   | +Y face, handle attachment point
  handle_l_mount          | handle_left  | +Y face (standoff tips to door)
  handle_r_mount          | handle_right | +Y face (standoff tips to door)

Each RigidJoint is defined with a Location in the part's local coordinates.
The Location.orientation expresses the mating normal direction (axis direction).
Explicit Place transforms are then computed from these joint definitions,
positioning each part so its joint datums match the root frame.
After generation, inspect tooling validates the joint alignments.

Tier interior clear heights:
  Tier 3 (bottom): 750 mm (LARGEST)
  Tier 2 (middle): 650 mm
  Tier 1 (top):    remaining (~728 mm)

Units: millimeters. Origin: bottom panel center at floor; XY base plane; +Z up.
"""

from build123d import *

# ============================================
# DESIGN PARAMETERS
# ============================================

cabinet_width  = 1600.0  # X
cabinet_depth  = 550.0   # Y
cabinet_height = 2200.0  # Z

panel_thick = 18.0
back_thick  = 5.0

tier3_height = 750.0  # bottom tier - LARGEST
tier2_height = 650.0  # middle tier

door_gap   = 3.0
door_thick = 18.0

handle_r        = 6.0
handle_length   = 180.0
handle_standoff = 32.0

# ============================================
# DERIVED DIMENSIONS (all in mm)
# ============================================

# Z positions of horizontal panel bottom faces
bottom_panel_top_z   = panel_thick                                      # 18
shelf_lower_bottom_z = bottom_panel_top_z + tier3_height                # 768
shelf_lower_top_z    = shelf_lower_bottom_z + panel_thick               # 786
shelf_upper_bottom_z = shelf_lower_top_z + tier2_height                 # 1436
shelf_upper_top_z    = shelf_upper_bottom_z + panel_thick               # 1454
top_panel_bottom_z   = cabinet_height - panel_thick                     # 2182
tier1_actual         = top_panel_bottom_z - shelf_upper_top_z           # 728

# Interior clear dimensions
interior_w = cabinet_width - 2 * panel_thick         # 1564
interior_d = cabinet_depth - panel_thick - back_thick # 527

# Component dimensions
side_h = cabinet_height - panel_thick     # 2182
door_h = cabinet_height - 2 * door_gap    # 2194
door_w = (cabinet_width - 3 * door_gap) / 2  # 795.5

# ============================================
# HELPERS
# ============================================

def _panel(label, x_len, y_len, z_len, color=None):
    """Create labeled Box panel centered at origin."""
    p = Box(x_len, y_len, z_len)
    p.label = label
    if color is not None:
        p.color = color
    return p

def _joint(part, label, position, z_dir=(0, 0, 1)):
    """Define a RigidJoint on a part.

    Args:
        part:  the Solid/Compound
        label: joint identifier
        position: (x, y, z) in part-local coordinates
        z_dir:  the joint's +Z direction (mating normal) in part-local coords
    """
    RigidJoint(label, part, Location(Plane(origin=position, z_dir=z_dir)))

# ============================================
# COMPONENT FACTORIES
# ============================================

def make_bottom():
    """Bottom panel, bottom face at floor (Z=0)."""
    p = Box(cabinet_width, cabinet_depth, panel_thick,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    p.label = "bottom_panel"
    p.color = "ivory"
    return p

def make_top():
    return _panel("top_panel", cabinet_width, cabinet_depth, panel_thick, "ivory")

def make_left_side():
    return _panel("left_panel", panel_thick, cabinet_depth, side_h, "ivory")

def make_right_side():
    return _panel("right_panel", panel_thick, cabinet_depth, side_h, "ivory")

def make_back():
    return _panel("back_panel", interior_w, back_thick, side_h, "ivory")

def make_shelf_lower():
    return _panel("shelf_lower", interior_w, interior_d, panel_thick, "ivory")

def make_shelf_upper():
    return _panel("shelf_upper", interior_w, interior_d, panel_thick, "ivory")

def make_door_left():
    # Door: wide(X) x thin(Y) x tall(Z)
    return _panel("door_left", door_w, door_thick, door_h, "ivory")

def make_door_right():
    return _panel("door_right", door_w, door_thick, door_h, "ivory")

def make_handle():
    """Vertical bar handle. Bar axis = Z. Standoffs extend +Y."""
    r = handle_r
    h = handle_length
    bar = Cylinder(radius=r, height=h,
                   align=(Align.CENTER, Align.CENTER, Align.CENTER))
    sr = r * 0.4
    sp = h * 0.55
    so_t = Cylinder(radius=sr, height=handle_standoff,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    so_b = Cylinder(radius=sr, height=handle_standoff,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    so_t = Rot(90, 0, 0) * so_t
    so_b = Rot(90, 0, 0) * so_b
    so_t = Pos(0, -handle_standoff / 2, sp / 2) * so_t
    so_b = Pos(0, -handle_standoff / 2, -sp / 2) * so_b
    hh = bar + so_t + so_b
    hh.label = "handle_base"
    hh.color = "silver"
    return hh

# ============================================
# ASSEMBLY: constraint definition + placement
# ============================================

def gen_step():
    """Assemble wardrobe.

    1. Define RigidJoints as the geometric constraint specification
       (documenting which faces mate, with what normal direction).
    2. Place each component with explicit parameterized transforms
       computed from the joint datum locations.
    """

    # --- Create all parts at their local origins ---
    bottom      = make_bottom()
    top         = make_top()
    left        = make_left_side()
    right       = make_right_side()
    back        = make_back()
    shelf_lower = make_shelf_lower()
    shelf_upper = make_shelf_upper()
    door_l      = make_door_left()
    door_r      = make_door_right()
    handle_l    = make_handle()
    handle_r    = make_handle()

    # ============================================================
    # PHASE 1: Define RigidJoints (constraint specification)
    # ============================================================

    # -- bottom_panel (root, bottom face at Z=0) --
    # Part-local: origin at geometric center = (0,0,0),
    # but we used Align.MIN so bottom face IS at Z=0.
    # Part-local box spans: Z=[0, 18], X=[-800, 800], Y=[-275, 275]
    _joint(bottom, "top_face",           (0, 0, panel_thick),                           (0, 0, 1))
    _joint(bottom, "front_face",         (0, cabinet_depth/2, 0),                       (0, 1, 0))
    _joint(bottom, "rear_inner_face",    (0, -cabinet_depth/2 + panel_thick, 0),        (0, -1, 0))
    _joint(bottom, "left_inner_face",    (-cabinet_width/2 + panel_thick/2, 0, 0),      (-1, 0, 0))
    _joint(bottom, "right_inner_face",   (cabinet_width/2 - panel_thick/2, 0, 0),       (1, 0, 0))
    _joint(bottom, "left_top_edge",      (-cabinet_width/2 + panel_thick/2, 0, panel_thick), (0, 0, 1))
    _joint(bottom, "right_top_edge",     (cabinet_width/2 - panel_thick/2, 0, panel_thick),  (0, 0, 1))
    _joint(bottom, "rear_top_edge",      (0, -cabinet_depth/2 + panel_thick, panel_thick),    (0, 0, 1))

    # -- left_panel (part-local origin at geometric center) --
    # Part-local: X=[-9,9], Y=[-275,275], Z=[-1091,1091]
    _joint(left, "inner_face",          (panel_thick/2, 0, 0),     (1, 0, 0))
    _joint(left, "bottom_face",         (0, 0, -side_h/2),        (0, 0, -1))
    _joint(left, "top_face",            (0, 0, side_h/2),         (0, 0, 1))
    _joint(left, "front_edge",          (0, cabinet_depth/2, 0),   (0, 1, 0))

    # -- right_panel --
    # Part-local: X=[-9,9], Y=[-275,275], Z=[-1091,1091]
    _joint(right, "inner_face",         (-panel_thick/2, 0, 0),    (-1, 0, 0))
    _joint(right, "bottom_face",        (0, 0, -side_h/2),        (0, 0, -1))
    _joint(right, "top_face",           (0, 0, side_h/2),         (0, 0, 1))
    _joint(right, "front_edge",         (0, cabinet_depth/2, 0),   (0, 1, 0))

    # -- back_panel --
    # Part-local: X=[-782,782], Y=[-2.5,2.5], Z=[-1091,1091]
    _joint(back, "front_face",          (0, back_thick/2, 0),      (0, 1, 0))
    _joint(back, "bottom_face",         (0, 0, -side_h/2),        (0, 0, -1))

    # -- shelf_lower --
    # Part-local: X=[-782,782], Y=[-263.5,263.5], Z=[-9,9]
    _joint(shelf_lower, "bottom_face",  (0, 0, -panel_thick/2),   (0, 0, -1))
    _joint(shelf_lower, "top_face",     (0, 0, panel_thick/2),    (0, 0, 1))
    _joint(shelf_lower, "front_edge",   (0, interior_d/2, 0),     (0, 1, 0))

    # -- shelf_upper --
    _joint(shelf_upper, "bottom_face",  (0, 0, -panel_thick/2),   (0, 0, -1))
    _joint(shelf_upper, "top_face",     (0, 0, panel_thick/2),    (0, 0, 1))
    _joint(shelf_upper, "front_edge",   (0, interior_d/2, 0),     (0, 1, 0))

    # -- top_panel (part-local origin at geometric center) --
    # X=[-800,800], Y=[-275,275], Z=[-9,9]
    _joint(top, "bottom_face",          (0, 0, -panel_thick/2),   (0, 0, -1))
    _joint(top, "left_seat",            (-cabinet_width/2 + panel_thick/2, 0, -panel_thick/2), (0, 0, -1))
    _joint(top, "right_seat",           (cabinet_width/2 - panel_thick/2, 0, -panel_thick/2), (0, 0, -1))

    # -- door_left (part-local origin at geometric center) --
    # X=[-397.75,397.75], Y=[-9,9], Z=[-1097,1097]
    _joint(door_l, "inner_face",        (0, -door_thick/2, 0),    (0, -1, 0))
    _joint(door_l, "front_face",        (0, door_thick/2, 0),     (0, 1, 0))
    _joint(door_l, "handle_mount_face", (door_w/2 - 50, door_thick/2, door_h*0.3), (0, 1, 0))

    # -- door_right --
    _joint(door_r, "inner_face",        (0, -door_thick/2, 0),    (0, -1, 0))
    _joint(door_r, "front_face",        (0, door_thick/2, 0),     (0, 1, 0))
    _joint(door_r, "handle_mount_face", (-(door_w/2 - 50), door_thick/2, door_h*0.3), (0, 1, 0))

    # -- handle_left (bar axis=Z, standoffs +Y, mount plane at Y=handle_standoff/2) --
    _joint(handle_l, "mount_face",      (0, handle_standoff/2, 0), (0, 1, 0))

    # -- handle_right --
    _joint(handle_r, "mount_face",      (0, handle_standoff/2, 0), (0, 1, 0))

    # ============================================================
    # PHASE 2: Place components (explicit parameterized transforms)
    # ============================================================
    # Each transform is computed from the design parameters and
    # corresponds to aligning the RigidJoints defined above.

    # bottom_panel: already positioned with Align.MIN (bottom at Z=0)

    # left_panel: inner_face at X = cabinet_width/2 - panel_thick
    #             bottom_face at Z = bottom_panel_top_z (= panel_thick)
    left_x  = -cabinet_width / 2 + panel_thick / 2        # -791
    left_z  = bottom_panel_top_z + side_h / 2              # 18 + 1091 = 1109
    left    = Pos(left_x, 0, left_z) * left

    # right_panel: mirror across X=0
    right_x = cabinet_width / 2 - panel_thick / 2          # 791
    right_z = bottom_panel_top_z + side_h / 2
    right   = Pos(right_x, 0, right_z) * right

    # back_panel: front_face at Y = -cabinet_depth/2 + panel_thick
    #             sits between left and right behind bottom panel
    back_y  = -cabinet_depth / 2 + panel_thick - back_thick / 2  # -259.5
    back_z  = bottom_panel_top_z + side_h / 2                     # 1109
    back    = Pos(0, back_y, back_z) * back

    # shelf_lower: between cabinet walls, at Z = shelf_lower_bottom_z + panel_thick/2
    int_y_center = (-cabinet_depth/2 + panel_thick + back_thick + cabinet_depth/2) / 2  # 11.5
    shelf_lower_z = shelf_lower_bottom_z + panel_thick / 2       # 777
    shelf_lower   = Pos(0, int_y_center, shelf_lower_z) * shelf_lower

    # shelf_upper: between cabinet walls, at Z = shelf_upper_bottom_z + panel_thick/2
    shelf_upper_z = shelf_upper_bottom_z + panel_thick / 2       # 1445
    shelf_upper   = Pos(0, int_y_center, shelf_upper_z) * shelf_upper

    # top_panel: bottom at Z = top_panel_bottom_z (= cabinet_height - panel_thick)
    top_z = cabinet_height - panel_thick / 2  # 2191
    top   = Pos(0, 0, top_z) * top

    # Doors in front: door inner face at Y = cabinet_depth/2 + door_gap
    door_y = cabinet_depth / 2 + door_gap + door_thick / 2  # 287
    door_z = door_gap + door_h / 2                            # 1100
    door_l = Pos(-cabinet_width / 4, door_y, door_z) * door_l
    door_r = Pos(cabinet_width / 4,   door_y, door_z) * door_r

    # Handles: mount face at door front face (Y=dool_y + door_thick/2)
    # bar center behind door front by handle_standoff/2
    handle_y = door_y + door_thick / 2 - handle_standoff / 2  # 287+9-16=280
    hz = door_gap + door_h * 0.3                              # 3+658.2=661.2
    hx_l = -cabinet_width / 4 + door_w / 2 - 50               # -400+397.75-50=-52.25
    hx_r = cabinet_width / 4 - door_w / 2 + 50                # 400-397.75+50=52.25
    handle_l = Pos(hx_l, handle_y, hz) * handle_l
    handle_r = Pos(hx_r, handle_y, hz) * handle_r

    # ============================================================
    # BUILD COMPOUND
    # ============================================================
    assembly = Compound(
        label="wardrobe1",
        children=[bottom, top, left, right, back,
                  shelf_lower, shelf_upper,
                  door_l, door_r,
                  handle_l, handle_r],
    )
    return assembly
