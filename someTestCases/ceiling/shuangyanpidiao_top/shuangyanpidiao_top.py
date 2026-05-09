"""
Double-Layer Gypsum-Board Suspended Ceiling (ShuangYanPi DiaoDing)
with bidirectional grid (ShuangXiang ShanGe) and recessed downlight array (PaiLie TongDeng).

Units: millimeters
Origin: center of ceiling; XY base plane; +Z upward (extrusion / ceiling top side)
"""

from build123d import *

# --- Ceiling dimensions ---
room_width = 4000.0  # mm (X)
room_depth = 3000.0  # mm (Y)
ceiling_thickness = 10.0  # mm

# --- Double-layer stepped tier parameters ---
# Two nested raised rectangular rims produce the characteristic
# double-layer stepped ceiling profile.
outer_step_width = 150.0  # mm - width of the outer raised tier rim
inner_step_width = 100.0  # mm - width of the inner raised tier rim
step_height = 30.0  # mm - height of each tier step above the base plate

# --- Bidirectional grid parameters ---
grid_rib_width = 20.0  # mm - rib thickness
grid_rib_depth = 15.0  # mm - rib projection downward from ceiling bottom
grid_spacing_x = 600.0  # mm - longitudinal grid spacing
grid_spacing_y = 600.0  # mm - transverse grid spacing

# --- Recessed downlight parameters ---
downlight_diameter = 80.0  # mm - typical recessed LED downlight OD
downlight_spacing_x = 1200.0  # mm
downlight_spacing_y = 1200.0  # mm


def _make_base_plate():
    """Main ceiling plate centered at origin."""
    return Box(room_width, room_depth, ceiling_thickness)


def _make_double_layer_tiers():
    """Two nested raised rims on top of the base plate."""
    # Outer tier rim
    outer = Box(room_width, room_depth, step_height) - Box(
        room_width - 2 * outer_step_width,
        room_depth - 2 * outer_step_width,
        step_height,
    )

    # Inner tier rim (nested inside the outer one)
    inner_outer_w = room_width - 2 * outer_step_width
    inner_outer_d = room_depth - 2 * outer_step_width
    inner = Box(inner_outer_w, inner_outer_d, step_height) - Box(
        inner_outer_w - 2 * inner_step_width,
        inner_outer_d - 2 * inner_step_width,
        step_height,
    )

    rise = ceiling_thickness
    return Pos(0, 0, rise) * (outer + inner)


def _make_bidirectional_grid():
    """Longitudinal + transverse grid ribs projecting downward (-Z)."""
    interior_w = room_width - 2 * (outer_step_width + inner_step_width)
    interior_d = room_depth - 2 * (outer_step_width + inner_step_width)

    parts = []

    # --- Longitudinal ribs (along X, evenly spaced across Y) ---
    nx = max(1, int(interior_d / grid_spacing_y))
    start_y = -interior_d / 2 + grid_spacing_y / 2
    for i in range(nx):
        cy = start_y + i * grid_spacing_y
        # Clamp near edges to keep ribs fully inside interior
        cy = max(-interior_d / 2 + grid_rib_width / 2,
                 min(interior_d / 2 - grid_rib_width / 2, cy))
        rib = Box(interior_w, grid_rib_width, grid_rib_depth)
        rib = Pos(0, cy, -grid_rib_depth / 2) * rib
        parts.append(rib)

    # --- Transverse ribs (along Y, evenly spaced across X) ---
    ny = max(1, int(interior_w / grid_spacing_x))
    start_x = -interior_w / 2 + grid_spacing_x / 2
    for i in range(ny):
        cx = start_x + i * grid_spacing_x
        cx = max(-interior_w / 2 + grid_rib_width / 2,
                 min(interior_w / 2 - grid_rib_width / 2, cx))
        rib = Box(grid_rib_width, interior_d, grid_rib_depth)
        rib = Pos(cx, 0, -grid_rib_depth / 2) * rib
        parts.append(rib)

    result = parts[0]
    for p in parts[1:]:
        result += p
    return result


def _make_downlights():
    """Array of recessed downlight cylinders (for subtractive boolean).

    Returns a compound of cylinders passing through the full ceiling thickness + grid.
    """
    interior_w = room_width - 2 * (outer_step_width + inner_step_width)
    interior_d = room_depth - 2 * (outer_step_width + inner_step_width)

    r = downlight_diameter / 2
    pass_height = ceiling_thickness + grid_rib_depth + step_height + 2.0

    cylinders = []

    margin_x = 0.0
    margin_y = 0.0

    nx = max(1, int((interior_w - 2 * margin_x) / downlight_spacing_x))
    ny = max(1, int((interior_d - 2 * margin_y) / downlight_spacing_y))

    start_x = -interior_w / 2 + margin_x + downlight_spacing_x / 2
    start_y = -interior_d / 2 + margin_y + downlight_spacing_y / 2

    for ix in range(nx):
        cx = start_x + ix * downlight_spacing_x
        for iy in range(ny):
            cy = start_y + iy * downlight_spacing_y
            cyl = Cylinder(
                radius=r,
                height=pass_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            cyl = Pos(cx, cy, -grid_rib_depth - 1.0) * cyl
            cylinders.append(cyl)

    result = cylinders[0]
    for c in cylinders[1:]:
        result += c
    return result


def gen_step():
    """Return the complete double-layer ceiling with grid and downlights."""
    base = _make_base_plate()
    tiers = _make_double_layer_tiers()
    grid = _make_bidirectional_grid()
    downlights = _make_downlights()

    ceiling = base + tiers + grid
    ceiling -= downlights
    ceiling.label = "shuangyanpidiao_top"
    return ceiling
