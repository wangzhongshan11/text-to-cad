"""P0b: analytic placement for ``axis_aligned`` bodies.

Bodies in the analytic bucket are placed by closed-form geometry (no scipy).
Currently supports placements equivalent to a ``flat_on`` macro expansion:

* ``plane_coincident`` (opposed) between child face and parent plane
* ``point_plane_offset`` in-plane ``x`` / ``y`` and normal ``offset``

Bodies are ordered with a BFS over parent→child edges derived from those
placements. If every non-ground body marked ``axis_aligned`` can be placed
this way, :func:`try_solve_analytic` returns final poses with ``nfev=0``.
Otherwise it returns ``None`` and the caller falls back to numerical solve.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from .errors import ConstraintSchemaError
from .features import parse_feature_ref, world_plane
from .primitives import PrimitiveBody
from .state import BodyPose, identity_pose


@dataclass(frozen=True)
class FlatOnPlacement:
    child_id: str
    parent_id: str
    plane_ref: str
    u: float
    v: float
    normal_offset: float


def bucket_bodies(
    body_ids: tuple[str, ...],
    rotation_modes: dict[str, str],
    *,
    ground: str,
) -> dict[str, list[str]]:
    """Assign each body to layout / analytic / yaw / free (P0b: layout+yaw empty)."""
    buckets: dict[str, list[str]] = {
        "layout": [],
        "analytic": [],
        "yaw": [],
        "free": [],
    }
    for body_id in body_ids:
        if body_id == ground:
            continue
        mode = rotation_modes.get(body_id, "free")
        if mode == "axis_aligned":
            buckets["analytic"].append(body_id)
        elif mode == "yaw_only":
            buckets["yaw"].append(body_id)
        elif mode == "free":
            buckets["free"].append(body_id)
        else:
            buckets["free"].append(body_id)
    return buckets


def extract_flat_on_placements(constraints: list[dict[str, Any]]) -> list[FlatOnPlacement]:
    """Recover ``flat_on`` parameters from expanded constraints."""
    from_triggered = _extract_from_triggered_by(constraints)
    if from_triggered:
        return from_triggered
    return _extract_from_v1_pattern(constraints)


def _extract_from_triggered_by(
    constraints: list[dict[str, Any]],
) -> list[FlatOnPlacement]:
    partial: dict[str, dict[str, Any]] = {}

    for constraint in constraints:
        triggered_by = constraint.get("triggered_by")
        if not isinstance(triggered_by, str) or ":flat_on:" not in triggered_by:
            continue
        rid = triggered_by.split(":")[0]
        role = triggered_by.split(":")[-1]
        entry = partial.setdefault(rid, {})

        if constraint["type"] == "plane_coincident":
            plane_ref = str(constraint["b"])
            child_ref = str(constraint["a"])
            if "." in child_ref:
                entry["child_id"] = child_ref.split(".", 1)[0]
            entry["plane_ref"] = plane_ref
            if "." in plane_ref:
                entry["parent_id"] = plane_ref.split(".", 1)[0]
        elif constraint["type"] == "point_plane_offset":
            if constraint.get("in_plane") == "x":
                entry["u"] = float(constraint["value"])
            elif constraint.get("in_plane") == "y":
                entry["v"] = float(constraint["value"])
            elif "offset" in constraint:
                entry["normal_offset"] = float(constraint["offset"])
            entry.setdefault("plane_ref", str(constraint.get("plane", "")))
            point = str(constraint.get("point", ""))
            if "." in point:
                entry.setdefault("child_id", point.split(".", 1)[0])

    placements: list[FlatOnPlacement] = []
    for rid, entry in partial.items():
        required = ("child_id", "parent_id", "plane_ref", "u", "v", "normal_offset")
        if not all(key in entry for key in required):
            continue
        placements.append(
            FlatOnPlacement(
                child_id=str(entry["child_id"]),
                parent_id=str(entry["parent_id"]),
                plane_ref=str(entry["plane_ref"]),
                u=float(entry["u"]),
                v=float(entry["v"]),
                normal_offset=float(entry["normal_offset"]),
            )
        )
    return placements


def _extract_from_v1_pattern(
    constraints: list[dict[str, Any]],
) -> list[FlatOnPlacement]:
    """Infer flat_on-style placements from hand-written v1 constraints."""
    placements: list[FlatOnPlacement] = []

    plane_coincidents = [
        c
        for c in constraints
        if c.get("type") == "plane_coincident" and c.get("opposed")
    ]
    for pc in plane_coincidents:
        child_ref = parse_feature_ref(str(pc["a"]))
        parent_plane_ref = parse_feature_ref(str(pc["b"]))
        child_id = child_ref.body_id
        parent_id = parent_plane_ref.body_id
        plane_ref = str(pc["b"])

        u_val: float | None = None
        v_val: float | None = None
        offset_val: float | None = None

        for constraint in constraints:
            if constraint.get("type") != "point_plane_offset":
                continue
            point_ref = parse_feature_ref(
                str(constraint.get("point", constraint.get("a", "")))
            )
            if point_ref.body_id != child_id:
                continue
            plane_match = str(constraint.get("plane", constraint.get("b", "")))
            if plane_match != plane_ref:
                continue
            in_plane = constraint.get("in_plane")
            if in_plane == "x":
                u_val = float(constraint["value"])
            elif in_plane == "y":
                v_val = float(constraint["value"])
            elif "offset" in constraint:
                offset_val = float(constraint["offset"])

        if u_val is None or v_val is None or offset_val is None:
            continue

        placements.append(
            FlatOnPlacement(
                child_id=child_id,
                parent_id=parent_id,
                plane_ref=plane_ref,
                u=u_val,
                v=v_val,
                normal_offset=offset_val,
            )
        )

    return placements


def bfs_placement_order(
    placements: list[FlatOnPlacement],
    *,
    ground: str,
    analytic_body_ids: set[str],
) -> list[str] | None:
    """Return child body ids in BFS order, or ``None`` if not all placeable."""
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {}

    for placement in placements:
        if placement.child_id not in analytic_body_ids:
            continue
        if placement.child_id in parent_of and parent_of[placement.child_id] != placement.parent_id:
            return None
        parent_of[placement.child_id] = placement.parent_id
        children_of.setdefault(placement.parent_id, []).append(placement.child_id)

    if set(parent_of.keys()) != analytic_body_ids:
        return None

    order: list[str] = []
    queue: deque[str] = deque([ground])
    placed: set[str] = {ground}

    while queue:
        parent_id = queue.popleft()
        for child_id in children_of.get(parent_id, []):
            if child_id in placed:
                continue
            if parent_of.get(child_id) != parent_id:
                return None
            order.append(child_id)
            placed.add(child_id)
            queue.append(child_id)

    if placed != analytic_body_ids | {ground}:
        # unreachable analytic bodies (cycle or missing parent link)
        if analytic_body_ids - (placed - {ground}):
            return None

    return order


def place_flat_on(
    placement: FlatOnPlacement,
    poses: dict[str, BodyPose],
    catalog: dict[str, PrimitiveBody],
) -> BodyPose:
    """Compute child ``BodyPose`` (identity rotation) from a solved parent."""
    parent_pose = poses[placement.parent_id]
    plane = world_plane(catalog, poses, parse_feature_ref(placement.plane_ref))
    tangent_u, tangent_v = plane.tangent_axes()
    origin = plane.origin
    normal = plane.normal / (np.linalg.norm(plane.normal) + 1e-15)
    center = (
        origin
        + tangent_u * placement.u
        + tangent_v * placement.v
        + normal * placement.normal_offset
    )
    return BodyPose(
        (float(center[0]), float(center[1]), float(center[2])),
        (0.0, 0.0, 0.0, 1.0),
    )


def try_place_analytic_bodies(
    *,
    ground: str,
    body_ids: tuple[str, ...],
    catalog: dict[str, PrimitiveBody],
    constraints: list[dict[str, Any]],
    rotation_modes: dict[str, str],
    base_poses: dict[str, BodyPose] | None = None,
) -> dict[str, BodyPose] | None:
    """Place ``axis_aligned`` bodies into ``base_poses``; return merged poses or ``None``."""
    buckets = bucket_bodies(body_ids, rotation_modes, ground=ground)
    analytic_ids = set(buckets["analytic"])

    if not analytic_ids:
        return dict(base_poses) if base_poses else None

    placements = extract_flat_on_placements(constraints)
    placement_by_child = {p.child_id: p for p in placements}

    order = bfs_placement_order(
        placements,
        ground=ground,
        analytic_body_ids=analytic_ids,
    )
    if order is None:
        return None

    poses: dict[str, BodyPose] = {body_id: identity_pose() for body_id in body_ids}
    if base_poses:
        poses.update(base_poses)

    for child_id in order:
        placement = placement_by_child.get(child_id)
        if placement is None:
            return None
        if placement.parent_id not in poses:
            return None
        poses[child_id] = place_flat_on(placement, poses, catalog)

    return poses


def try_solve_analytic(
    *,
    ground: str,
    body_ids: tuple[str, ...],
    catalog: dict[str, PrimitiveBody],
    constraints: list[dict[str, Any]],
    rotation_modes: dict[str, str],
) -> dict[str, BodyPose] | None:
    """Place all ``axis_aligned`` bodies analytically when no yaw/free/layout remain."""
    buckets = bucket_bodies(body_ids, rotation_modes, ground=ground)
    if buckets["yaw"] or buckets["free"] or buckets["layout"]:
        return None
    return try_place_analytic_bodies(
        ground=ground,
        body_ids=body_ids,
        catalog=catalog,
        constraints=constraints,
        rotation_modes=rotation_modes,
    )


def assert_bfs_parent_before_child(
    order: list[str],
    placements: list[FlatOnPlacement],
) -> None:
    """Compile-time check helper: parent index < child index in BFS order."""
    index = {body_id: idx for idx, body_id in enumerate(order)}
    parent_of = {p.child_id: p.parent_id for p in placements}
    for child_id, parent_id in parent_of.items():
        if parent_id not in index or child_id not in index:
            raise ConstraintSchemaError(
                f"BFS order missing {child_id!r} or parent {parent_id!r}"
            )
        if index[parent_id] >= index[child_id]:
            raise ConstraintSchemaError(
                f"BFS order violation: parent {parent_id!r} must be placed "
                f"before child {child_id!r}"
            )
