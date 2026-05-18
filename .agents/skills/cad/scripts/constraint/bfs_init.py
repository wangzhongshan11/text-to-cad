"""P1a: BFS initial poses for the numerical (scipy) solve path.

Uses ``flat_on`` placement hints (from macro expansion or v1 pattern inference)
to seed body translations before scipy TRF. Analytic bucket bodies are excluded
from BFS here — they already have final poses from :mod:`constraint.analytic`.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from .analytic import (
    FlatOnPlacement,
    extract_flat_on_placements,
    place_flat_on,
)
from .primitives import PrimitiveBody
from .state import BodyPose, identity_pose


def _placement_graph(
    placements: list[FlatOnPlacement],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {}
    for placement in placements:
        parent_of[placement.child_id] = placement.parent_id
        children_of.setdefault(placement.parent_id, []).append(placement.child_id)
    return parent_of, children_of


def bfs_initial_poses(
    *,
    body_ids: tuple[str, ...],
    ground: str,
    catalog: dict[str, PrimitiveBody],
    constraints: list[dict[str, Any]],
    layout_poses: dict[str, BodyPose] | None = None,
    solved_poses: dict[str, BodyPose] | None = None,
) -> dict[str, BodyPose]:
    """Estimate initial poses by BFS along ``flat_on`` parent→child edges."""
    layout_poses = layout_poses or {}
    poses: dict[str, BodyPose] = dict(solved_poses or {})
    poses.setdefault(ground, identity_pose())
    for body_id in body_ids:
        if body_id in layout_poses:
            poses[body_id] = layout_poses[body_id]

    placements = extract_flat_on_placements(constraints)
    if not placements:
        return poses

    parent_of, children_of = _placement_graph(placements)
    placement_by_child = {p.child_id: p for p in placements}

    queue: deque[str] = deque([ground])
    placed: set[str] = set(poses.keys())

    while queue:
        parent_id = queue.popleft()
        for child_id in children_of.get(parent_id, []):
            if child_id in placed:
                continue
            if parent_of.get(child_id) != parent_id:
                continue
            placement = placement_by_child.get(child_id)
            if placement is None or parent_id not in poses:
                continue
            poses[child_id] = place_flat_on(placement, poses, catalog)
            placed.add(child_id)
            queue.append(child_id)

    return poses
