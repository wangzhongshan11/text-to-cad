from __future__ import annotations

import re
from typing import Any

import numpy as np

from .state import BodyPose, quaternion_xyzw_to_rotation_matrix

_AXIS_REF = re.compile(r"^([A-Za-z0-9_]+)\.(axis_[xyz]|axis)$")


def _parse_axis_ref(ref: str) -> tuple[str, str] | None:
    match = _AXIS_REF.match(str(ref).strip())
    if not match:
        return None
    axis = match.group(2)
    if axis == "axis":
        axis = "axis_z"
    return match.group(1), axis


def _collect_axis_parallel(constraints: list[dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    pairs: list[tuple[str, str, str, str]] = []
    for constraint in constraints:
        if constraint.get("type") != "axis_parallel":
            continue
        a = _parse_axis_ref(str(constraint.get("a", "")))
        b = _parse_axis_ref(str(constraint.get("b", "")))
        if a is None or b is None:
            continue
        pairs.append((a[0], a[1], b[0], b[1]))
    return pairs


def axis_lock_preflight_warnings(
    *,
    ground: str,
    constraints: list[dict[str, Any]],
    catalog: dict[str, Any] | None = None,
) -> list[str]:
    """Warn when a body sits on ground but only locks one world axis direction."""
    warnings: list[str] = []
    on_ground: set[str] = set()
    for constraint in constraints:
        if constraint.get("type") not in {"contact", "plane_coincident"}:
            continue
        a_ref = str(constraint.get("a", ""))
        b_ref = str(constraint.get("b", ""))
        if a_ref.endswith(".-z") and b_ref.startswith(f"{ground}."):
            on_ground.add(a_ref.split(".", 1)[0])

    locked_to_ground: dict[str, set[str]] = {}
    for body_a, axis_a, body_b, axis_b in _collect_axis_parallel(constraints):
        if body_b != ground:
            continue
        locked_to_ground.setdefault(body_a, set()).add(axis_a)

    for body_id in sorted(on_ground):
        if catalog is not None and catalog.get(body_id) is not None:
            if getattr(catalog[body_id], "primitive", None) == "cylinder":
                continue
        locked = locked_to_ground.get(body_id, set())
        if "axis_z" in locked and not ({"axis_x", "axis_y"} & locked):
            warnings.append(
                f"missing_in_plane_axis_lock: {body_id} has axis_z parallel to ground "
                "but no axis_x/axis_y lock; may spin about Z with zero residual"
            )
    return warnings


def _world_axis_direction(axis_name: str) -> np.ndarray:
    if axis_name == "axis_x":
        return np.array([1.0, 0.0, 0.0])
    if axis_name == "axis_y":
        return np.array([0.0, 1.0, 0.0])
    return np.array([0.0, 0.0, 1.0])


def _body_local_axis_in_world(pose: BodyPose, axis_name: str) -> np.ndarray:
    rotation = quaternion_xyzw_to_rotation_matrix(pose.quaternion_xyzw)
    local = _world_axis_direction(axis_name)
    world = rotation @ local
    norm = float(np.linalg.norm(world))
    if norm <= 1e-12:
        return world
    return world / norm


def rotation_audit_issues(
    *,
    ground: str,
    poses: dict[str, BodyPose],
    constraints: list[dict[str, Any]],
    catalog: dict[str, Any] | None = None,
    angle_tol_deg: float = 3.0,
) -> list[dict[str, str]]:
    """Post-solve check: axis_parallel satisfied in direction but spin may remain."""
    issues: list[dict[str, str]] = []
    cos_tol = float(np.cos(np.deg2rad(angle_tol_deg)))
    pairs = _collect_axis_parallel(constraints)

    locked_to_ground: dict[str, set[str]] = {}
    for body_a, axis_a, body_b, axis_b in pairs:
        if body_b != ground:
            continue
        locked_to_ground.setdefault(body_a, set()).add(axis_a)

    for body_id, pose in poses.items():
        if body_id == ground:
            continue
        if catalog is not None and catalog.get(body_id) is not None:
            if getattr(catalog[body_id], "primitive", None) == "cylinder":
                continue
        locked = locked_to_ground.get(body_id, set())
        if "axis_z" in locked and not ({"axis_x", "axis_y"} & locked):
            issues.append(
                {
                    "body": body_id,
                    "reason": "only_axis_z_locked_to_ground",
                    "hint": f"add axis_parallel for {body_id}.axis_x or .axis_y to {ground}",
                }
            )

    for body_a, axis_a, body_b, axis_b in pairs:
        if body_a not in poses or body_b not in poses:
            continue
        dir_a = _body_local_axis_in_world(poses[body_a], axis_a)
        dir_b = _body_local_axis_in_world(poses[body_b], axis_b)
        alignment = float(abs(np.dot(dir_a, dir_b)))
        if alignment + 1e-9 < cos_tol:
            issues.append(
                {
                    "body": body_a,
                    "reason": f"axis_parallel_mismatch:{body_a}.{axis_a} vs {body_b}.{axis_b}",
                    "hint": f"alignment={alignment:.4f}; check constraints or initial_guess",
                }
            )
    return issues[:8]
