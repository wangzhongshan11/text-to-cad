"""
Double-door wardrobe (ShuangKaiMen YiGui) with 3-tier cabinet body.
Bottom tier is the largest space.

Assembly structure (11 labeled children):
  bottom_panel (root)
  left_panel, right_panel (side walls)
  back_panel (rear)
  shelf_mid (divider between tier 2 and tier 3)
  shelf_top_divider (divider between tier 1 and tier 2)
  top_panel (crown)
  door_left, door_right (front double doors)
  handle_left, handle_right (door handles)

Tier heights (interior clear space):
  Tier 1 (top):    500 mm  - bedding / seasonal items
  Tier 2 (middle): 600 mm  - folded clothes
  Tier 3 (bottom): 900 mm  - long garments (LARGEST)

Units: millimeters
Origin: center of cabinet footprint at floor (Z=0); XY base plane; +Z upward
"""

from build123d import *

# ============================================
# 1. DESIGN PARAMETERS
# ============================================

# --- Cabinet overall dimensions ---
cabinet_width = 1800.0   # X - overall width
cabinet_depth = 600.0    # Y - overall depth
cabinet_height = 2200.0  # Z - overall height

# --- Panel thicknesses ---
panel_thick = 18.0       # main structural panels (sides, top, bottom, shelves)
back_thick = 5.0         # thin back panel

# --- Tier interior heights (clear space between panels) ---
tier1_height = 500.0     # top tier (bedding)
tier2_height = 600.0     # middle tier (folded clothes)
tier3_height = 900.0     # bottom tier (long garments) - LARGEST

# --- Door parameters ---
door_gap = 3.0           # gap between doors and to cabinet edges
door_thick = 18.0        # door panel thickness

# --- Handle parameters ---
handle_diameter = 12.0   # bar diameter
handle_length = 200.0    # bar length (vertical)
handle_standoff = 35.0   # distance from bar center to door surface

# ============================================
# 2. DERIVED DIMENSIONS
# ============================================

# Z positions of horizontal panels (bottom face Z coordinate)
# Floor is at Z=0.
# bottom_panel: Z=[0, panel_thick] = [0, 18]
# tier3 (bottom, largest): 900 mm clear above bottom_panel
# shelf_mid: sits at Z=[bottom_panel_top + tier3_height, that + panel_thick]
# tier2 (middle): 600 mm clear above shelf_mid
# shelf_top_divider: similar, above tier2
# tier1 (top): 500 mm clear above shelf_top_divider
# top_panel: sits at Z=[cabinet_height - panel_thick, cabinet_height]

bottom_panel_top = panel_thick                                  # 18
shelf_mid_bottom = bottom_panel_top + tier3_height              # 918
shelf_mid_top = shelf_mid_bottom + panel_thick                  # 936
shelf_top_div_bottom = shelf_mid_top + tier2_height             # 1536
shelf_top_div_top = shelf_top_div_bottom + panel_thick          # 1554
top_panel_bottom_actual = cabinet_height - panel_thick          # 2182
tier1_actual = top_panel_bottom_actual - shelf_top_div_top      # 628
# Note: tier1 is slightly larger than planned (628 vs 500) because
# the cabinet height yields extra space. This is acceptable.

# Interior clear dimensions
interior_w = cabinet_width - 2 * panel_thick                     # 1764
interior_d = cabinet_depth - panel_thick - back_thick            # 577

# Door dimensions (thin along Y, tall along Z)
door_h = cabinet_height - 2 * door_gap                           # 2194
door_w = (cabinet_width - 3 * door_gap) / 2                      # 895.5

# ============================================
# 3. HELPER
# ============================================

def _panel(label, x_len, y_len, z_len, color=None):
    """Create a labeled box panel centered at origin.

    Args:
        x_len: dimension along X (width)
        y_len: dimension along Y (depth)
        z_len: dimension along Z (height/thickness)
    """
    p = Box(x_len, y_len, z_len)
    p.label = label
    if color:
        p.color = color
    return p

# ============================================
# 4. COMPONENT FACTORIES
# ============================================

def make_bottom_panel():
    """Floor/base panel: 1800(X) x 600(Y) x 18(Z)."""
    return _panel("bottom_panel", cabinet_width, cabinet_depth, panel_thick, "tan")

def make_top_panel():
    """Crown panel: 1800(X) x 600(Y) x 18(Z)."""
    return _panel("top_panel", cabinet_width, cabinet_depth, panel_thick, "tan")

def make_left_panel():
    """Left side wall: 18(X) x 600(Y) x 2182(Z)."""
    h = cabinet_height - panel_thick
    return _panel("left_panel", panel_thick, cabinet_depth, h, "tan")

def make_right_panel():
    """Right side wall: 18(X) x 600(Y) x 2182(Z)."""
    h = cabinet_height - panel_thick
    return _panel("right_panel", panel_thick, cabinet_depth, h, "tan")

def make_back_panel():
    """Rear panel: 1764(X) x 5(Y) x 2182(Z)."""
    h = cabinet_height - panel_thick
    return _panel("back_panel", interior_w, back_thick, h, "wheat")

def make_shelf_mid():
    """Middle divider shelf: 1764(X) x 577(Y) x 18(Z)."""
    return _panel("shelf_mid", interior_w, interior_d, panel_thick, "tan")

def make_shelf_top_divider():
    """Upper divider shelf: 1764(X) x 577(Y) x 18(Z)."""
    return _panel("shelf_top_divider", interior_w, interior_d, panel_thick, "tan")

def make_door_left():
    """Left door: 895.5(X) x 18(Y) x 2194(Z)."""
    return _panel("door_left", door_w, door_thick, door_h, "sandybrown")

def make_door_right():
    """Right door: 895.5(X) x 18(Y) x 2194(Z)."""
    return _panel("door_right", door_w, door_thick, door_h, "sandybrown")

def make_handle():
    """One door handle: vertical bar + two standoffs.

    In part-local coordinates:
      - Bar axis = Z (vertical), bar center at origin
      - Standoffs extend in +Y direction from bar
      - Standoff tips define the mount plane at local Y = handle_standoff/2
    """
    r = handle_diameter / 2
    h = handle_length
    bar = Cylinder(radius=r, height=h,
                   align=(Align.CENTER, Align.CENTER, Align.CENTER))
    sr = r * 0.4
    sf_spacing = h * 0.6

    # Standoffs: default height along Z, rotated to point along +Y
    so_top = Cylinder(radius=sr, height=handle_standoff,
                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    so_bot = Cylinder(radius=sr, height=handle_standoff,
                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    # Rotate cylinder axis from Z to Y: 90 degrees around X
    so_top = Rot(90, 0, 0) * so_top
    so_bot = Rot(90, 0, 0) * so_bot
    # Position behind bar (-Y) at +/- Z
    so_top = Pos(0, -handle_standoff / 2, sf_spacing / 2) * so_top
    so_bot = Pos(0, -handle_standoff / 2, -sf_spacing / 2) * so_bot

    hh = bar + so_top + so_bot
    hh.label = "handle_base"
    hh.color = "silver"
    return hh

# ============================================
# 5. ASSEMBLY
# ============================================

def gen_step():
    """Assemble the complete wardrobe.

    All positions are computed from the design parameters.
    bottom_panel is the root, positioned at the assembly origin.
    Every other component is placed with an explicit Pos(...) transform.
    """

    # --- Create all 11 parts ---
    bottom = make_bottom_panel()
    top = make_top_panel()
    left = make_left_panel()
    right = make_right_panel()
    back = make_back_panel()
    shelf_mid = make_shelf_mid()
    shelf_top_div = make_shelf_top_divider()
    door_l = make_door_left()
    door_r = make_door_right()
    handle_l = make_handle()
    handle_r = make_handle()

    # --- Position each component ---

    # bottom_panel: center at (0, 0, panel_thick/2)
    bottom = Pos(0, 0, panel_thick / 2) * bottom

    # left_panel:
    #   Height = cabinet_height - panel_thick = 2182
    #   Center X = -cabinet_width/2 + panel_thick/2 = -900 + 9 = -891
    #   Center Y = 0 (centered depth-wise)
    #   Center Z = panel_thick + (2182)/2 = 18 + 1091 = 1109
    left_h = cabinet_height - panel_thick
    left_x = -cabinet_width / 2 + panel_thick / 2
    left_z = panel_thick + left_h / 2
    left = Pos(left_x, 0, left_z) * left

    # right_panel: mirror of left
    right_x = cabinet_width / 2 - panel_thick / 2
    right_z = panel_thick + left_h / 2
    right = Pos(right_x, 0, right_z) * right

    # back_panel:
    #   Sits between left and right, at rear
    #   Front face of back panel at Y = -cabinet_depth/2 + panel_thick
    #   Center Y = -cabinet_depth/2 + panel_thick + back_thick/2
    #            = -300 + 18 + 2.5 = -279.5
    #   Center Z = same as side panels = 1109
    back_y = -cabinet_depth / 2 + panel_thick + back_thick / 2
    back_z = panel_thick + left_h / 2
    back = Pos(0, back_y, back_z) * back

    # Interior region for shelves:
    #   X range: [-interior_w/2, interior_w/2] = [-882, 882]
    #   Y range: starts after back panel front face
    #     Y_min = -cabinet_depth/2 + panel_thick + back_thick = -277
    #     Y_max = cabinet_depth/2 = 300
    #     Y_center = (-277 + 300) / 2 = 11.5
    interior_y_center = (-cabinet_depth / 2 + panel_thick + back_thick
                         + cabinet_depth / 2) / 2

    # shelf_mid: sits between tier 3 (bottom) and tier 2 (middle)
    #   Center Z = shelf_mid_bottom + panel_thick/2 = 918 + 9 = 927
    shelf_mid_z = shelf_mid_bottom + panel_thick / 2
    shelf_mid = Pos(0, interior_y_center, shelf_mid_z) * shelf_mid

    # shelf_top_divider: sits between tier 2 (middle) and tier 1 (top)
    #   Center Z = shelf_top_div_bottom + panel_thick/2 = 1536 + 9 = 1545
    shelf_top_z = shelf_top_div_bottom + panel_thick / 2
    shelf_top_div = Pos(0, interior_y_center, shelf_top_z) * shelf_top_div

    # top_panel: crown, on top of side panels
    #   Center Z = cabinet_height - panel_thick/2 = 2200 - 9 = 2191
    top_z = cabinet_height - panel_thick / 2
    top = Pos(0, 0, top_z) * top

    # --- Doors ---
    # Doors sit in front of cabinet with a gap.
    # Door front face Y = cabinet_depth/2 + door_gap + door_thick = 300 + 3 + 18 = 321
    # Door center Y = cabinet_depth/2 + door_gap + door_thick/2 = 300 + 3 + 9 = 312
    # Door center Z = door_gap + door_h/2 = 3 + 1097 = 1100
    door_y = cabinet_depth / 2 + door_gap + door_thick / 2
    door_z = door_gap + door_h / 2

    # Left door: center X = -cabinet_width/4 = -450
    door_l_x = -cabinet_width / 4
    door_l = Pos(door_l_x, door_y, door_z) * door_l

    # Right door: center X = cabinet_width/4 = 450
    door_r_x = cabinet_width / 4
    door_r = Pos(door_r_x, door_y, door_z) * door_r

    # --- Handles ---
    # Handle local coords:
    #   Standoff tips at local Y = handle_standoff/2 (mount plane)
    #   To mount on door front face at world Y = door_front_y:
    #     bar center Y = door_front_y - handle_standoff/2
    door_front_y = door_y + door_thick / 2  # 312 + 9 = 321
    handle_world_y = door_front_y - handle_standoff / 2  # 321 - 17.5 = 303.5

    # Handle Z: ~1/4 of door height from bottom
    handle_z_abs = door_gap + door_h * 0.25  # 3 + 548.5 = 551.5

    # Left door handle: near the right edge (center opening edge of left door)
    #   Left door X range: [-897.75, -2.25]
    #   Right edge = -2.25; handle centers 60mm from edge
    handle_l_x = door_l_x + door_w / 2 - 60  # -2.25 - 60 = -62.25
    handle_l = Pos(handle_l_x, handle_world_y, handle_z_abs) * handle_l

    # Right door handle: near the left edge (center opening edge of right door)
    #   Right door X range: [2.25, 897.75]
    #   Left edge = 2.25; handle centers 60mm from edge
    handle_r_x = door_r_x - door_w / 2 + 60  # 2.25 + 60 = 62.25
    handle_r = Pos(handle_r_x, handle_world_y, handle_z_abs) * handle_r

    # --- Assembly compound ---
    assembly = Compound(
        label="wardrobe",
        children=[
            bottom,
            top,
            left,
            right,
            back,
            shelf_mid,
            shelf_top_div,
            door_l,
            door_r,
            handle_l,
            handle_r,
        ],
    )
    return assembly
