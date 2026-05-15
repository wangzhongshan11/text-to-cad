"""Desk with drawers - parametric build123d assembly.

Coordinate convention:
  Origin: center of tabletop footprint on the floor plane
  XY: floor/base plane
  +Z: up

Dimensions in millimeters.
"""

from build123d import *

# ---- Parameters ------------------------------------------------------------

# Desk overall
desk_width = 1200.0
desk_depth = 600.0
desk_height = 750.0

# Tabletop
tabletop_thickness = 25.0

# Legs (square cross-section)
leg_side = 50.0
# Legs inset from tabletop edges
leg_inset_x = 40.0
leg_inset_y = 40.0

# Side panels (left and right vertical panels to hold drawers)
panel_thickness = 15.0
panel_depth = desk_depth - 2 * leg_inset_y  # flush with inner leg edges

# Drawers
num_drawers = 3
drawer_gap = 2.0  # gap between drawers for clearance
drawer_front_thickness = 18.0
drawer_side_thickness = 12.0
drawer_bottom_thickness = 6.0

# Drawer interior dimensions
drawer_interior_width = 350.0
drawer_interior_depth = panel_depth - 2 * drawer_side_thickness
drawer_interior_height = 180.0

# Drawer outer dimensions
drawer_outer_width = drawer_interior_width + 2 * drawer_side_thickness
drawer_outer_depth = panel_depth
drawer_outer_height = drawer_interior_height + drawer_bottom_thickness

# Drawer pull (simple bar handle)
pull_width = 100.0
pull_diameter = 12.0
pull_protrusion = 22.0

# ---- Helper: leg positions ------------------------------------------------

def leg_positions():
    lx = desk_width / 2 - leg_inset_x - leg_side / 2
    ly = desk_depth / 2 - leg_inset_y - leg_side / 2
    return [
        (-lx, -ly),  # front-left
        ( lx, -ly),  # front-right
        (-lx,  ly),  # back-left
        ( lx,  ly),  # back-right
    ]

# ---- Part builders ---------------------------------------------------------

def make_tabletop():
    with BuildPart() as top:
        Box(desk_width, desk_depth, tabletop_thickness)
        # Chamfer top edges for a finished look
        edges = top.edges().filter_by(Axis.Z).group_by(Axis.Z)[-1]
        chamfer(edges, length=2.0)
    top.part.label = "tabletop"
    # Position: top sits on legs, bottom face at Z = desk_height - tabletop_thickness
    top.part.location = Location((0, 0, desk_height - tabletop_thickness / 2))
    return top.part


def make_leg():
    with BuildPart() as leg:
        Box(leg_side, leg_side, desk_height - tabletop_thickness)
    leg.part.label = "leg"
    return leg.part


def make_left_panel():
    panel_x = -desk_width / 2 + leg_inset_x + leg_side + panel_thickness / 2
    panel_z = (desk_height - tabletop_thickness) / 2
    with BuildPart() as p:
        Box(panel_thickness, panel_depth, desk_height - tabletop_thickness)
    p.part.label = "left_panel"
    p.part.location = Location((panel_x, 0, panel_z))
    return p.part


def make_right_panel():
    panel_x = desk_width / 2 - leg_inset_x - leg_side - panel_thickness / 2
    panel_z = (desk_height - tabletop_thickness) / 2
    with BuildPart() as p:
        Box(panel_thickness, panel_depth, desk_height - tabletop_thickness)
    p.part.label = "right_panel"
    p.part.location = Location((panel_x, 0, panel_z))
    return p.part


def make_drawer(drawer_index):
    """Create a single drawer box with front face and handle.
    drawer_index: 0 = bottom, 1 = middle, 2 = top
    """
    # Drawer origin: center of drawer box
    # X position: between left and right panels
    drawer_x = 0.0
    # Total drawer stack height
    total_stack = num_drawers * drawer_outer_height + (num_drawers - 1) * drawer_gap
    # Bottom of stack starts above floor with some clearance
    stack_bottom = 80.0
    # Z center of this drawer
    drawer_z = (
        stack_bottom
        + drawer_outer_height / 2
        + drawer_index * (drawer_outer_height + drawer_gap)
    )

    with BuildPart() as drawer:
        # Drawer box (hollow, open top)
        Box(drawer_outer_width, drawer_outer_depth, drawer_outer_height)
    drawer.part.label = f"drawer_box_{drawer_index + 1}"

    # Hollow out drawer - offset shell from top face
    # Extract the top face and shell the drawer body
    top_faces = drawer.part.faces().filter_by(Axis.Z).group_by(Axis.Z)[-1]
    drawer_shell = offset(
        drawer.part,
        -drawer_side_thickness,
        openings=top_faces,
    )
    drawer.part = drawer_shell

    with BuildPart() as front:
        # Drawer front face - a decorative plate on the front
        Box(
            drawer_outer_width + 4,
            drawer_front_thickness,
            drawer_outer_height + 8,
        )
    front.part.label = f"drawer_front_{drawer_index + 1}"

    with BuildPart() as handle:
        # Horizontal cylindrical bar handle
        Cylinder(
            radius=pull_diameter / 2,
            height=pull_width,
            rotation=(0, 90, 0),  # rotate so cylinder axis is along X
        )
    handle.part.label = f"drawer_handle_{drawer_index + 1}"

    # Position the front face: at the front of the drawer box
    front_y = -drawer_outer_depth / 2 + drawer_front_thickness / 2
    front.part.location = Location(
        (0, front_y, 0)
    )

    # Position the handle on the front face
    handle_y = front_y - drawer_front_thickness / 2 - pull_protrusion / 2
    handle.part.location = Location(
        (0, handle_y, 0)
    )

    # Assemble drawer sub-assembly
    drawer_assy = Compound(
        label=f"drawer_{drawer_index + 1}",
        children=[drawer.part, front.part, handle.part],
    )
    # Move the entire drawer assembly to its position
    drawer_assy.location = Location((drawer_x, 0, drawer_z))
    return drawer_assy


def make_drawer_rails():
    """Simple support rails for each drawer on left and right panels."""
    rails = []
    total_stack = num_drawers * drawer_outer_height + (num_drawers - 1) * drawer_gap
    stack_bottom = 80.0

    # Rail dimensions
    rail_width = drawer_side_thickness + 4
    rail_thickness = 6.0
    rail_length = 40.0  # support length into the desk depth

    # Left rail X: inner face of left panel
    left_panel_x = -desk_width / 2 + leg_inset_x + leg_side + panel_thickness
    # Right rail X: inner face of right panel
    right_panel_x = desk_width / 2 - leg_inset_x - leg_side - panel_thickness

    for i in range(num_drawers):
        rail_z = stack_bottom + i * (drawer_outer_height + drawer_gap)

        for rx, label_prefix in [(left_panel_x, "left"), (right_panel_x, "right")]:
            with BuildPart() as rail:
                Box(rail_width, rail_length, rail_thickness)
            rail.part.label = f"rail_{label_prefix}_{i + 1}"
            rail.part.location = Location(
                (rx + (-rail_width / 2 if label_prefix == "left" else rail_width / 2),
                 0,
                 rail_z + rail_thickness / 2)
            )
            rails.append(rail.part)

    if rails:
        return Compound(label="drawer_rails", children=rails)
    return None


# ---- Assembly --------------------------------------------------------------

def gen_step():
    children = []

    # Tabletop
    tabletop = make_tabletop()
    children.append(tabletop)

    # Legs
    for i, (lx, ly) in enumerate(leg_positions()):
        leg = make_leg()
        leg.label = f"leg_{i + 1}"
        leg.location = Location((lx, ly, (desk_height - tabletop_thickness) / 2))
        children.append(leg)

    # Side panels
    children.append(make_left_panel())
    children.append(make_right_panel())

    # Drawer rails
    rails = make_drawer_rails()
    if rails is not None:
        children.append(rails)

    # Drawers
    for i in range(num_drawers):
        children.append(make_drawer(i))

    assembly = Compound(label="desk_with_drawers", children=children)
    return assembly


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "cad", "scripts"))
    # Quick test
    result = gen_step()
    print(f"Generated: {result.label}, children: {len(result.children)}")