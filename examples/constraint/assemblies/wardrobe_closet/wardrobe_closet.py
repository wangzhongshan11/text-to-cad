"""Wardrobe: shell via constraint_assembly; interior shelves/dividers via Location (hybrid)."""

from __future__ import annotations

import json
from pathlib import Path

import build123d
from build123d import Box, BuildPart, Compound, Location
from constraint.assemble import constraint_assembly

ROOT = Path(__file__).resolve().parents[2]

STEP_OUTPUT = "model/wardrobe_closet.step"

W = 1200.0
D = 560.0
H = 2100.0
T = 18.0
BOTTOM_TOP_Z = T / 2.0


def _box(size: tuple[float, float, float]):
    with BuildPart() as part:
        Box(*size)
    return part.part


def _on_bottom(
    bodies: dict,
    constraints: list,
    body_id: str,
    size: tuple[float, float, float],
    *,
    x: float,
    y: float,
    thickness_axis: str,
) -> None:
    """Panel sitting on bottom; lock Z height + XY + both in-plane axes (no spin around Z)."""
    bodies[body_id] = {"primitive": "box", "size": list(size)}
    thickness_axis = thickness_axis.lower()
    in_plane_lock = (
        {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "bottom.axis_x"}
        if thickness_axis == "x"
        else {"type": "axis_parallel", "a": f"{body_id}.axis_y", "b": "bottom.axis_y"}
    )
    constraints.extend(
        [
            {"type": "contact", "a": f"{body_id}.-z", "b": "bottom.+z"},
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "offset": size[2] / 2.0,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "in_plane": "x",
                "value": x,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "in_plane": "y",
                "value": y,
            },
            {"type": "axis_parallel", "a": f"{body_id}.axis_z", "b": "bottom.axis_z"},
            in_plane_lock,
        ]
    )


def _at_height(
    bodies: dict,
    constraints: list,
    body_id: str,
    size: tuple[float, float, float],
    *,
    x: float,
    y: float,
    z_center: float,
) -> None:
    bodies[body_id] = {"primitive": "box", "size": list(size)}
    constraints.extend(
        [
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "offset": z_center - BOTTOM_TOP_Z,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "in_plane": "x",
                "value": x,
            },
            {
                "type": "point_plane_offset",
                "point": f"{body_id}.center",
                "plane": "bottom.+z",
                "in_plane": "y",
                "value": y,
            },
            {"type": "axis_parallel", "a": f"{body_id}.axis_z", "b": "bottom.axis_z"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_x", "b": "bottom.axis_x"},
            {"type": "axis_parallel", "a": f"{body_id}.axis_y", "b": "bottom.axis_y"},
        ]
    )


def _shell_constraints() -> dict:
    bodies: dict = {"bottom": {"primitive": "box", "size": [W, D, T]}}
    constraints: list = []

    side_h = H - 2.0 * T
    y_back = -(D - T) / 2.0

    _on_bottom(bodies, constraints, "left", (T, D, side_h), x=-(W - T) / 2.0, y=0.0, thickness_axis="x")
    _on_bottom(bodies, constraints, "right", (T, D, side_h), x=(W - T) / 2.0, y=0.0, thickness_axis="x")
    _on_bottom(
        bodies,
        constraints,
        "back",
        (W - 2.0 * T, T, side_h),
        x=0.0,
        y=y_back,
        thickness_axis="y",
    )
    _at_height(bodies, constraints, "top", (W - 2.0 * T, D, T), x=0.0, y=0.0, z_center=H - T / 2.0)

    return {"ground": "bottom", "bodies": bodies, "constraints": constraints}


SHELL_CONSTRAINTS = _shell_constraints()


def _shell_parts() -> dict:
    return {
        body_id: _box(tuple(body["size"]))
        for body_id, body in SHELL_CONSTRAINTS["bodies"].items()
    }


def _interior_compound() -> Compound:
    """Shelves/dividers: formula placement inside resolved shell envelope."""
    shelf_w = W - 2.0 * T
    shelf_d = D - T
    y_back = -(D - T) / 2.0
    shelf_y = y_back + shelf_d / 2.0
    div_h = 900.0
    div_zc = T + div_h / 2.0 + 200.0

    children: list = []
    for zc in (320.0, 520.0, 720.0, 920.0, 1120.0, 1320.0):
        children.append(_box((shelf_w, shelf_d, T)).moved(Location((0.0, shelf_y, zc))))
    for x_pos in (-260.0, 260.0):
        children.append(_box((T, shelf_d, div_h)).moved(Location((x_pos, shelf_y, div_zc))))
    shoe_z = BOTTOM_TOP_Z + 80.0 + 16.0
    children.append(_box((shelf_w, shelf_d, 32.0)).moved(Location((0.0, shelf_y, shoe_z))))
    return Compound(label="interior", children=children)


def gen_step():
    shell = constraint_assembly(
        SHELL_CONSTRAINTS,
        _shell_parts(),
        report_path=ROOT / "out" / "assembly_wardrobe_closet.constraint.report.json",
    )
    return build123d.Compound(label="wardrobe_closet", children=[shell, _interior_compound()])


if __name__ == "__main__":
    payload = gen_step()
    print(
        json.dumps(
            {
                "label": getattr(payload, "label", None),
                "shell_bodies": len(SHELL_CONSTRAINTS["bodies"]),
                "interior_panels": 9,
            },
            ensure_ascii=False,
        )
    )
