"""Double-layer suspended ceiling (shuang yan pi diao ding) - standalone ceiling only.

Two stepped "eyelid" layers with indirect LED lighting coves,
decorative trim, central light panel. No room walls or structural slab.

Coordinate convention:
  Origin: center of ceiling on the visible ceiling plane
  XY: ceiling plane (horizontal)
  +Z: up (toward the hidden structural space)

Ceiling size: 4000 x 3000 mm
Finished ceiling bottom surface height: 0 (reference plane at visible ceiling)

Dimensions in millimeters.
"""

from build123d import *
from math import radians, sin, cos

# ---- Ceiling parameters ----------------------------------------------------

ceiling_width = 4000.0
ceiling_depth = 3000.0

# Layer 1: Upper "eyelid" -- wide perimeter frame, first step up from main ceiling
layer1_drop = 40.0          # step height (how much this layer rises)
layer1_width = 200.0        # width of frame strip from edge inward
layer1_thickness = 12.0     # board thickness

# Layer 2: Lower "eyelid" -- narrower frame, second step up
layer2_drop = 40.0          # additional step up from layer 1
layer2_width = 100.0        # narrower strip
layer2_thickness = 12.0

# Central ceiling panel -- the highest (deepest recess) flat area
central_panel_thickness = 12.0
# After layer1 + layer2 strips, the inner open area:
central_panel_width = ceiling_width - 2 * (layer1_width + layer2_width)
central_panel_depth = ceiling_depth - 2 * (layer1_width + layer2_width)

# Total drop from main ceiling bottom to central panel top
total_drop = layer1_drop + layer2_drop + central_panel_thickness

# ---- LED cove --------------------------------------------------------------

cove_width = 35.0           # LED strip holder width
cove_height = 18.0          # cove channel height

# ---- Decorative trim lines ------------------------------------------------

trim_offset_from_layer2 = 60.0  # distance from layer2 inner edge
trim_line_width = 8.0
trim_line_thickness = 5.0

# ---- Central light panel --------------------------------------------------

light_outer_w = central_panel_width * 0.60
light_outer_d = central_panel_depth * 0.60
light_frame_width = 24.0     # decorative frame rim width
light_panel_w = light_outer_w - 2 * light_frame_width
light_panel_d = light_outer_d - 2 * light_frame_width
light_frame_thickness = 6.0
light_panel_thickness = 10.0

# ---- Corner decorative blocks ---------------------------------------------

corner_block_size = 80.0
corner_block_thick = layer1_thickness

# ---- Derived Z positions --------------------------------------------------

# Z = 0 is the visible bottom surface of the finished ceiling
z_layer1_bottom = 0.0
z_layer1_top = z_layer1_bottom + layer1_thickness

z_layer2_bottom = z_layer1_top + layer1_drop
z_layer2_top = z_layer2_bottom + layer2_thickness

z_central_bottom = z_layer2_top + layer2_drop
z_central_top = z_central_bottom + central_panel_thickness

# Vertical wall Z positions
z_layer1_vert_top = z_layer2_bottom
z_layer1_vert_bottom = z_layer1_top
z_layer2_vert_top = z_central_bottom
z_layer2_vert_bottom = z_layer2_top

# Cove Z center
z_cove = z_layer1_top + cove_height / 2

# Trim lines Z
z_trim = z_central_top + trim_line_thickness / 2

# Light panel Z
z_light = z_central_top + light_frame_thickness / 2


# ---- Part builders ---------------------------------------------------------


def make_central_panel():
    """The main flat ceiling panel at the highest level."""
    with BuildPart() as cp:
        Box(central_panel_width, central_panel_depth, central_panel_thickness)
    cp.part.label = "central_ceiling_panel"
    cp.part.location = Location(
        (0, 0, z_central_bottom + central_panel_thickness / 2)
    )
    return cp.part


def make_layer1_frame():
    """Layer 1 -- wide perimeter frame (upper eyelid), visible from below."""
    strips = []
    outer_w = ceiling_width
    outer_d = ceiling_depth
    inner_w = ceiling_width - 2 * layer1_width
    inner_d = ceiling_depth - 2 * layer1_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    zc = z_layer1_bottom + layer1_thickness / 2

    # Four strips forming the rectangular frame
    specs = [
        ("front", 0, -half_od + layer1_width / 2, outer_w, layer1_width),
        ("back",  0,  half_od - layer1_width / 2, outer_w, layer1_width),
        ("left",  -half_ow + layer1_width / 2, 0, layer1_width, inner_d),
        ("right", half_ow - layer1_width / 2, 0, layer1_width, inner_d),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as s:
            Box(bw, bd, layer1_thickness)
        s.part.label = f"layer1_{label}"
        s.part.location = Location((cx, cy, zc))
        strips.append(s.part)

    return Compound(label="layer1_frame", children=strips)


def make_layer1_vertical():
    """Vertical faces connecting layer1 to layer2."""
    strips = []
    outer_w = ceiling_width
    outer_d = ceiling_depth
    inner_w = ceiling_width - 2 * layer1_width
    inner_d = ceiling_depth - 2 * layer1_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    vh = layer1_drop
    zc = z_layer1_top + vh / 2

    specs = [
        ("front", 0, -half_od + layer1_width / 2, outer_w, layer1_width),
        ("back",  0,  half_od - layer1_width / 2, outer_w, layer1_width),
        ("left",  -half_ow + layer1_width / 2, 0, layer1_width, inner_d),
        ("right", half_ow - layer1_width / 2, 0, layer1_width, inner_d),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as s:
            Box(bw, bd, vh)
        s.part.label = f"layer1_vert_{label}"
        s.part.location = Location((cx, cy, zc))
        strips.append(s.part)

    return Compound(label="layer1_vertical", children=strips)


def make_layer2_frame():
    """Layer 2 -- narrower frame (lower eyelid), visible from below."""
    strips = []
    outer_w = ceiling_width - 2 * layer1_width
    outer_d = ceiling_depth - 2 * layer1_width
    inner_w = outer_w - 2 * layer2_width
    inner_d = outer_d - 2 * layer2_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    zc = z_layer2_bottom + layer2_thickness / 2

    specs = [
        ("front", 0, -half_od + layer2_width / 2, outer_w, layer2_width),
        ("back",  0,  half_od - layer2_width / 2, outer_w, layer2_width),
        ("left",  -half_ow + layer2_width / 2, 0, layer2_width, inner_d),
        ("right", half_ow - layer2_width / 2, 0, layer2_width, inner_d),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as s:
            Box(bw, bd, layer2_thickness)
        s.part.label = f"layer2_{label}"
        s.part.location = Location((cx, cy, zc))
        strips.append(s.part)

    return Compound(label="layer2_frame", children=strips)


def make_layer2_vertical():
    """Vertical faces connecting layer2 to central panel."""
    strips = []
    outer_w = ceiling_width - 2 * layer1_width
    outer_d = ceiling_depth - 2 * layer1_width
    inner_w = outer_w - 2 * layer2_width
    inner_d = outer_d - 2 * layer2_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    vh = layer2_drop
    zc = z_layer2_top + vh / 2

    specs = [
        ("front", 0, -half_od + layer2_width / 2, outer_w, layer2_width),
        ("back",  0,  half_od - layer2_width / 2, outer_w, layer2_width),
        ("left",  -half_ow + layer2_width / 2, 0, layer2_width, inner_d),
        ("right", half_ow - layer2_width / 2, 0, layer2_width, inner_d),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as s:
            Box(bw, bd, vh)
        s.part.label = f"layer2_vert_{label}"
        s.part.location = Location((cx, cy, zc))
        strips.append(s.part)

    return Compound(label="layer2_vertical", children=strips)


def make_led_cove():
    """LED strip holders: sit on layer1, direct light up toward central panel edge."""
    strips = []
    outer_w = ceiling_width - 2 * layer1_width
    outer_d = ceiling_depth - 2 * layer1_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    zc = z_cove

    # Cove strips sit in the gap area, on top of layer 1, projecting inward slightly
    # They are placed at the inner edge of layer1 (before layer2 begins)
    cove_len_x = outer_w - 2 * layer2_width - 40
    cove_len_y = outer_d - 2 * layer2_width - 40

    specs = [
        ("front", 0, -half_od + layer2_width + cove_width / 2 + 2, cove_len_x, cove_width),
        ("back",  0,  half_od - layer2_width - cove_width / 2 - 2, cove_len_x, cove_width),
        ("left",  -half_ow + layer2_width + cove_width / 2 + 2, 0, cove_width, cove_len_y),
        ("right", half_ow - layer2_width - cove_width / 2 - 2, 0, cove_width, cove_len_y),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as c:
            Box(bw, bd, cove_height)
        c.part.label = f"led_cove_{label}"
        c.part.location = Location((cx, cy, zc))
        strips.append(c.part)

    return Compound(label="led_coves", children=strips)


def make_trim_lines():
    """Decorative trim moldings along the central panel."""
    lines = []
    half_pw = central_panel_width / 2
    half_pd = central_panel_depth / 2
    zc = z_trim
    offset = trim_offset_from_layer2

    specs = [
        ("front", 0, -half_pd + offset, central_panel_width - 2 * offset, trim_line_width),
        ("back",  0,  half_pd - offset, central_panel_width - 2 * offset, trim_line_width),
        ("left",  -half_pw + offset, 0, trim_line_width, central_panel_depth - 2 * offset),
        ("right", half_pw - offset, 0, trim_line_width, central_panel_depth - 2 * offset),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as t:
            Box(bw, bd, trim_line_thickness)
        t.part.label = f"trim_{label}"
        t.part.location = Location((cx, cy, zc))
        lines.append(t.part)

    return Compound(label="trim_lines", children=lines)


def make_central_light():
    """Central decorative light panel with outer frame rim."""
    children = []

    # Frame rim: four strips around the light panel perimeter
    half_ow = light_outer_w / 2
    half_od = light_outer_d / 2
    half_pw = light_panel_w / 2
    half_pd = light_panel_d / 2
    zc = z_light

    # The rim sits on top of the central panel as a raised frame
    rim_h = light_frame_thickness

    rim_specs = [
        ("front", 0, -half_od + light_frame_width / 2, light_outer_w, light_frame_width),
        ("back",  0,  half_od - light_frame_width / 2, light_outer_w, light_frame_width),
        ("left",  -half_ow + light_frame_width / 2, 0, light_frame_width, light_panel_d),
        ("right", half_ow - light_frame_width / 2, 0, light_frame_width, light_panel_d),
    ]
    for label, cx, cy, bw, bd in rim_specs:
        with BuildPart() as r:
            Box(bw, bd, rim_h)
        r.part.label = f"light_rim_{label}"
        r.part.location = Location((cx, cy, zc))
        children.append(r.part)

    # Inner light panel (diffuser)
    with BuildPart() as lp:
        Box(light_panel_w, light_panel_d, light_panel_thickness)
    lp.part.label = "light_panel_diffuser"
    lp.part.location = Location(
        (0, 0, zc + rim_h / 2 + light_panel_thickness / 2)
    )
    children.append(lp.part)

    return Compound(label="central_light", children=children)


def make_corner_decorations():
    """Decorative blocks at four corners of the layer1 frame."""
    blocks = []
    half_ow = ceiling_width / 2
    half_od = ceiling_depth / 2
    inset = layer1_width / 2
    zc = z_layer1_bottom + corner_block_thick / 2

    for x_sign, y_sign, label in [
        (-1, -1, "fl"), (1, -1, "fr"),
        (-1,  1, "bl"), (1,  1, "br"),
    ]:
        with BuildPart() as b:
            # Diagonal-cut look: use a box
            Box(corner_block_size, corner_block_size, corner_block_thick)
        b.part.label = f"corner_{label}"
        b.part.location = Location(
            (x_sign * (half_ow - inset), y_sign * (half_od - inset), zc)
        )
        blocks.append(b.part)

    return Compound(label="corner_decorations", children=blocks)


def make_shadow_line_layer1():
    """Fine shadow-line grooves on layer1 bottom face, near inner edge."""
    lines = []
    outer_w = ceiling_width - 2 * layer1_width
    outer_d = ceiling_depth - 2 * layer1_width
    half_ow = outer_w / 2
    half_od = outer_d / 2
    groove_w = 3.0
    groove_h = 3.0

    # Tiny grooves on the visible (bottom) face near the inner transition
    # These create the characteristic "shadow line" that defines shuang yan pi
    inset = 8.0  # distance from layer1 inner edge

    specs = [
        ("front", 0, -half_od + layer2_width + inset, outer_w - 2 * layer2_width, groove_w),
        ("back",  0,  half_od - layer2_width - inset, outer_w - 2 * layer2_width, groove_w),
        ("left",  -half_ow + layer2_width + inset, 0, groove_w, outer_d - 2 * layer2_width),
        ("right", half_ow - layer2_width - inset, 0, groove_w, outer_d - 2 * layer2_width),
    ]
    for label, cx, cy, bw, bd in specs:
        with BuildPart() as l:
            Box(bw, bd, groove_h)
        l.part.label = f"shadow_groove_{label}"
        # Place at layer1 bottom surface (Z ~ 0), protruding slightly
        l.part.location = Location((cx, cy, layer1_thickness + groove_h / 2))
        lines.append(l.part)

    return Compound(label="shadow_lines", children=lines)


# ---- Assembly --------------------------------------------------------------

def gen_step():
    children = []

    # Core ceiling layers (bottom to top)
    children.append(make_layer1_frame())       # Z=0 visible bottom
    children.append(make_layer1_vertical())    # Z=12 to Z=52
    children.append(make_layer2_frame())       # Z=52 visible
    children.append(make_layer2_vertical())    # Z=64 to Z=104
    children.append(make_central_panel())      # Z=104 top

    # LED lighting coves
    children.append(make_led_cove())

    # Decorative elements
    children.append(make_trim_lines())
    children.append(make_central_light())
    children.append(make_corner_decorations())
    children.append(make_shadow_line_layer1())

    assembly = Compound(label="double_layer_ceiling", children=children)
    return assembly


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "cad", "scripts"))
    result = gen_step()
    print(f"Generated: {result.label}, children: {len(result.children)}")