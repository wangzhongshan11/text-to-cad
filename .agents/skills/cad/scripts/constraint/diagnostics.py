"""P0c/P2b: DOF diagnostics — mating/gauge, auto_lock, status v2, MUS conflicts."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation

from .constraints import CompiledConstraint
from .state import STATE_DIM, BodyPose, normalize_quaternion_xyzw, quaternion_residual


RELATIVE_MATING_EPSILON = 1e-3
SINGULAR_THRESHOLD = 1e-4
MUS_MAX_OVER = 20
MUS_REPORT_LIMIT = 3
MAX_WITNESS_CANDIDATES = 4


def _rotation_axes_from_null(null_vector: np.ndarray, *, threshold: float = 0.15) -> list[str]:
    quat = null_vector[3:7]
    if float(np.linalg.norm(quat)) <= threshold:
        return []
    axes: list[str] = []
    if abs(float(quat[0])) > threshold:
        axes.append("x")
    if abs(float(quat[1])) > threshold:
        axes.append("y")
    if abs(float(quat[2])) > threshold:
        axes.append("z")
    return axes


def _trans_axes_from_null(null_vector: np.ndarray, *, threshold: float = 0.35) -> list[str]:
    translation = null_vector[0:3]
    axes: list[str] = []
    if abs(float(translation[0])) > threshold:
        axes.append("x")
    if abs(float(translation[1])) > threshold:
        axes.append("y")
    if abs(float(translation[2])) > threshold:
        axes.append("z")
    return axes


def _is_mating_constraint(constraint: CompiledConstraint) -> bool:
    return constraint.constraint_type != "axis_parallel"


def normalize_jacobian_rows(
    jacobian: np.ndarray,
    *,
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
) -> np.ndarray:
    j_norm = np.asarray(jacobian, dtype=float).copy()
    row = 0
    for _body_id in body_ids:
        j_norm[row, :] /= 10.0
        row += 1
    for constraint in compiled:
        values = constraint.residual_fn(poses)
        for value in values:
            if constraint.constraint_type in {
                "axis_parallel",
                "axis_coaxial",
                "plane_coincident",
            }:
                scale = 1.0
            else:
                scale = max(1.0, abs(float(value)))
            j_norm[row, :] /= scale
            row += 1
    return j_norm


def _build_row_map(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
) -> tuple[list[int], dict[str, tuple[int, int]], set[str]]:
    mating_rows: list[int] = []
    constraint_ranges: dict[str, tuple[int, int]] = {}
    mating_ids: set[str] = set()
    row = len(body_ids)
    for constraint in compiled:
        dim = len(constraint.residual_fn(poses))
        constraint_ranges[constraint.constraint_id] = (row, row + dim)
        if _is_mating_constraint(constraint):
            mating_rows.extend(range(row, row + dim))
            mating_ids.add(constraint.constraint_id)
        row += dim
    return mating_rows, constraint_ranges, mating_ids


def _sensitive_constraint_ids(
    jacobian: np.ndarray,
    null_vector: np.ndarray,
    constraint_ranges: dict[str, tuple[int, int]],
    *,
    epsilon: float,
    only_ids: set[str] | None = None,
) -> list[str]:
    ids: list[str] = []
    for cid, (start, end) in constraint_ranges.items():
        if only_ids is not None and cid not in only_ids:
            continue
        block = jacobian[start:end, :]
        if block.size == 0:
            continue
        if float(np.linalg.norm(block @ null_vector)) > epsilon:
            ids.append(cid)
    return ids


def _gauge_category(
    *,
    trans: list[str],
    rot: list[str],
) -> str:
    if rot == ["z"] or (rot and "z" in rot and not {"x", "y"} & set(rot)):
        return "spin_z_on_support"
    if rot:
        return "spin_" + "_".join(rot)
    if trans:
        return "trans_drift"
    return "gauge_residual"


def classify_free_directions(
    jacobian: np.ndarray,
    *,
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    ground: str,
    constraints: list[dict[str, Any]],
    relative_epsilon: float = RELATIVE_MATING_EPSILON,
) -> dict[str, Any]:
    j_norm = normalize_jacobian_rows(
        jacobian,
        body_ids=body_ids,
        compiled=compiled,
        poses=poses,
    )
    singular_values = np.linalg.svd(j_norm, compute_uv=False)
    rank = int(np.sum(singular_values > SINGULAR_THRESHOLD))
    dof_deficit = max(0, j_norm.shape[1] - rank)
    epsilon_mating = (
        float(relative_epsilon * singular_values[0]) if singular_values.size else 1e-6
    )

    mating_rows, constraint_ranges, mating_ids = _build_row_map(
        body_ids, compiled, poses
    )
    mating_block = j_norm[mating_rows, :] if mating_rows else np.zeros((0, j_norm.shape[1]))

    mating_free: list[dict[str, Any]] = []
    gauge_free: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    if dof_deficit > 0 and j_norm.shape[0] > 0:
        _, _, vh = np.linalg.svd(j_norm, full_matrices=True)
        null_vectors = vh[rank:].T
        for vector_index in range(null_vectors.shape[1]):
            null_vector = null_vectors[:, vector_index]
            mating_sens = (
                float(np.linalg.norm(mating_block @ null_vector))
                if mating_block.size
                else 0.0
            )

            for body_index, body_id in enumerate(body_ids):
                if body_id == ground:
                    continue
                offset = body_index * STATE_DIM
                body_slice = null_vector[offset : offset + STATE_DIM]
                trans = _trans_axes_from_null(body_slice)
                rot = _rotation_axes_from_null(body_slice)
                if not trans and not rot:
                    continue
                key = (body_id, ",".join(trans), ",".join(rot))
                if key in seen:
                    continue
                seen.add(key)

                affects = _sensitive_constraint_ids(
                    j_norm,
                    null_vector,
                    constraint_ranges,
                    epsilon=epsilon_mating,
                    only_ids=mating_ids if mating_sens > epsilon_mating else None,
                )

                entry: dict[str, Any] = {
                    "body": body_id,
                    "trans": trans,
                    "rot": rot,
                    "affects": affects[:8],
                }
                if mating_sens > epsilon_mating:
                    entry["category"] = "mating"
                    mating_free.append(entry)
                else:
                    entry["category"] = _gauge_category(trans=trans, rot=rot)
                    gauge_free.append(entry)

    return {
        "rank": rank,
        "dof_deficit": dof_deficit,
        "mating_free": mating_free[:8],
        "gauge_free": gauge_free[:8],
        "epsilon_mating": epsilon_mating,
    }


def _support_parent(body_id: str, constraints: list[dict[str, Any]], ground: str) -> str:
    for constraint in constraints:
        if constraint.get("type") not in {"plane_coincident", "contact"}:
            continue
        a_ref = str(constraint.get("a", ""))
        b_ref = str(constraint.get("b", ""))
        if a_ref.startswith(f"{body_id}.") and ".-z" in a_ref:
            return b_ref.split(".", 1)[0]
        if b_ref.startswith(f"{body_id}.") and ".-z" in b_ref:
            return a_ref.split(".", 1)[0]
    return ground


def pick_gauge_lock_constraints(
    gauge_entry: dict[str, Any],
    *,
    ground: str,
    constraints: list[dict[str, Any]],
    next_id: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    body_id = str(gauge_entry["body"])
    category = str(gauge_entry.get("category", ""))
    parent = _support_parent(body_id, constraints, ground)

    if category == "spin_z_on_support" or gauge_entry.get("rot") == ["z"]:
        new_constraints: list[dict[str, Any]] = []
        for axis in ("axis_x", "axis_y"):
            cid = f"c_auto_{next_id}"
            next_id += 1
            new_constraints.append(
                {
                    "id": cid,
                    "type": "axis_parallel",
                    "a": f"{body_id}.{axis}",
                    "b": f"{parent}.{axis}",
                    "triggered_by": "auto_lock:spin_z_on_support",
                }
            )
        return new_constraints, {
            "body": body_id,
            "rule": "fixed_orthogonal_to_support",
            "added": [c["id"] for c in new_constraints],
            "reason": category or "spin_z_on_support",
        }

    return [], None


def _rotate_pose_about_world_axis(
    pose: BodyPose,
    axis: tuple[float, float, float],
    angle_deg: float,
) -> BodyPose:
    axis_vec = np.asarray(axis, dtype=float)
    axis_vec = axis_vec / (np.linalg.norm(axis_vec) + 1e-15)
    rotation = Rotation.from_rotvec(axis_vec * math.radians(angle_deg))
    base = Rotation.from_quat(pose.quaternion_xyzw)
    combined = rotation * base
    quat = normalize_quaternion_xyzw(tuple(combined.as_quat()))
    return BodyPose(pose.translation, quat)


def _spin_z_yaw_witness_specs(
    body_id: str,
    current_pose: BodyPose,
    *,
    start_id: int,
) -> list[dict[str, Any]]:
    """Analytic yaw samples about +Z for spin-z gauge (P2d)."""
    specs: list[dict[str, Any]] = []
    for index, angle in enumerate((0, 90, 180, 270)):
        rotated = _rotate_pose_about_world_axis(current_pose, (0.0, 0.0, 1.0), angle)
        specs.append(
            {
                "constraint": None,
                "rule": f"yaw_{angle}",
                "description": f"{body_id} rotated {angle}° about support normal (+Z)",
                "pose": rotated,
                "analytic": True,
            }
        )
    return specs


def _witness_lock_specs(
    gauge_entry: dict[str, Any],
    *,
    ground: str,
    constraints: list[dict[str, Any]],
    next_id: int,
) -> tuple[list[dict[str, Any]], int]:
    """Discrete axis_parallel locks for witness enumeration (P2d)."""
    body_id = str(gauge_entry.get("body", ""))
    category = str(gauge_entry.get("category", ""))
    rot = list(gauge_entry.get("rot", []))
    parent = _support_parent(body_id, constraints, ground)
    specs: list[dict[str, Any]] = []

    def add(
        child_axis: str,
        parent_axis: str,
        opposed: bool,
        rule_suffix: str,
        *,
        yaw_label: str,
    ) -> None:
        cid = f"witness_{next_id + len(specs)}"
        specs.append(
            {
                "constraint": {
                    "id": cid,
                    "type": "axis_parallel",
                    "a": f"{body_id}.{child_axis}",
                    "b": f"{parent}.{parent_axis}",
                    "opposed": opposed,
                    "triggered_by": f"witness:{rule_suffix}",
                },
                "rule": rule_suffix,
                "description": (
                    f"{body_id}.{child_axis} parallel to {parent}.{parent_axis} "
                    f"({yaw_label}, {'opposed' if opposed else 'same'} sense)"
                ),
            }
        )

    if category == "spin_z_on_support" or rot == ["z"]:
        return [], next_id
    elif len(rot) == 1:
        axis = f"axis_{rot[0]}"
        add(axis, axis, False, f"{axis}_aligned_same", yaw_label="same sense")
        add(axis, axis, True, f"{axis}_aligned_opposed", yaw_label="opposed sense")
    elif rot:
        axis = f"axis_{rot[0]}"
        add(axis, axis, False, f"{axis}_aligned_same", yaw_label="same sense")
        add(axis, axis, True, f"{axis}_aligned_opposed", yaw_label="opposed sense")

    return specs[:MAX_WITNESS_CANDIDATES], next_id + len(specs)


def _pose_delta(
    from_pose: BodyPose,
    to_pose: BodyPose,
) -> dict[str, list[float]]:
    return {
        "delta_translation": [
            float(to_pose.translation[index] - from_pose.translation[index]) for index in range(3)
        ],
        "delta_quaternion_xyzw": [
            float(to_pose.quaternion_xyzw[index] - from_pose.quaternion_xyzw[index])
            for index in range(4)
        ],
    }


def enumerate_witnesses(
    gauge_free: list[dict[str, Any]],
    *,
    current_poses: dict[str, BodyPose],
    ground: str,
    constraints: list[dict[str, Any]],
    trial_solve,
    residual_tol: float = 1e-5,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Enumerate discrete gauge witness branches (P2d).

    ``trial_solve(extra_constraints)`` must return new poses on success or ``None``.
    """
    warnings: list[str] = []
    branches: dict[str, list[dict[str, Any]]] = {}
    next_id = 1

    for entry in gauge_free:
        body_id = str(entry.get("body", ""))
        if not body_id or body_id not in current_poses:
            continue
        category = str(entry.get("category", ""))
        rot = list(entry.get("rot", []))
        base_pose = current_poses[body_id]

        if category == "spin_z_on_support" or rot == ["z"]:
            lock_specs = _spin_z_yaw_witness_specs(
                body_id, base_pose, start_id=next_id
            )
            next_id += len(lock_specs)
        else:
            lock_specs, next_id = _witness_lock_specs(
                entry,
                ground=ground,
                constraints=constraints,
                next_id=next_id,
            )

        if not lock_specs:
            continue
        if len(lock_specs) > MAX_WITNESS_CANDIDATES:
            warnings.append(f"witness_truncated:{body_id}")

        candidates: list[dict[str, Any]] = []
        seen_deltas: list[tuple[float, ...]] = []

        for index, spec in enumerate(lock_specs[:MAX_WITNESS_CANDIDATES]):
            if spec.get("analytic"):
                trial_pose = spec["pose"]
                delta = _pose_delta(base_pose, trial_pose)
                delta_key = tuple(delta["delta_translation"] + delta["delta_quaternion_xyzw"])
                if any(
                    max(abs(delta_key[i] - seen[i]) for i in range(len(delta_key))) < 1e-6
                    for seen in seen_deltas
                ):
                    continue
                seen_deltas.append(delta_key)
                candidates.append(
                    {
                        "id": f"cand_{chr(ord('a') + index)}",
                        "rule": spec["rule"],
                        "description": spec["description"],
                        "resolved": index == 0,
                        **delta,
                    }
                )
                continue

            constraint = spec.get("constraint")
            if constraint is None:
                continue
            try:
                trial_poses = trial_solve([constraint])
            except Exception:
                continue
            if trial_poses is None or body_id not in trial_poses:
                continue
            trial_pose = trial_poses[body_id]
            delta = _pose_delta(base_pose, trial_pose)
            delta_key = tuple(delta["delta_translation"] + delta["delta_quaternion_xyzw"])
            if any(
                max(abs(delta_key[i] - seen[i]) for i in range(len(delta_key))) < 1e-6
                for seen in seen_deltas
            ):
                continue
            seen_deltas.append(delta_key)
            candidates.append(
                {
                    "id": f"cand_{chr(ord('a') + index)}",
                    "rule": spec["rule"],
                    "description": spec["description"],
                    "constraint_id": constraint["id"],
                    "triggered_by": constraint.get("triggered_by"),
                    "resolved": True,
                    **delta,
                }
            )

        if candidates:
            branches[body_id] = candidates[:MAX_WITNESS_CANDIDATES]

    return branches, warnings


def apply_gauge_auto_lock(
    gauge_free: list[dict[str, Any]],
    *,
    ground: str,
    constraints: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    extra: list[dict[str, Any]] = []
    assumed: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    next_id = 1

    for entry in gauge_free:
        new_c, lock = pick_gauge_lock_constraints(
            entry,
            ground=ground,
            constraints=constraints,
            next_id=next_id,
        )
        next_id += len(new_c)
        if lock is None:
            unmatched.append(entry)
        else:
            extra.extend(new_c)
            assumed.append(lock)

    return extra, assumed, unmatched


def suggest_relations(
    mating_free: list[dict[str, Any]],
    *,
    constraints: list[dict[str, Any]],
    ground: str,
    gauge_free: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    gauge_free = gauge_free or []

    for entry in mating_free:
        body_id = str(entry.get("body", ""))
        trans = list(entry.get("trans", []))
        rot = list(entry.get("rot", []))
        parent = _support_parent(body_id, constraints, ground)
        affects = {"trans": trans, "rot": rot}

        if set(trans) >= {"x", "y"} or trans == ["x", "y"]:
            suggestions.append(
                {
                    "type": "flat_on",
                    "child": body_id,
                    "on": f"{parent}.+z",
                    "at": [0, 0],
                    "affects": affects,
                    "note": "fill at:[u,v] for in-plane placement",
                }
            )
        elif trans == ["z"] or trans == ["x", "y", "z"]:
            suggestions.append(
                {
                    "type": "coax",
                    "a": f"{body_id}.axis_z",
                    "b": f"{parent}.axis_z",
                    "offset": 0,
                    "affects": affects,
                    "note": "axial placement along support axis",
                }
            )
        elif len(trans) == 1:
            suggestions.append(
                {
                    "type": "point_plane_offset",
                    "child": body_id,
                    "in_plane": trans[0],
                    "affects": affects,
                    "note": f"add in_plane lock for {','.join(trans)}",
                }
            )

        if rot and rot != ["z"]:
            suggestions.append(
                {
                    "type": "align",
                    "a": f"{body_id}.axis_z",
                    "b": f"{parent}.axis_z",
                    "affects": affects,
                    "note": "align primary axis to support",
                }
            )

    for entry in gauge_free:
        body_id = str(entry.get("body", ""))
        rot = list(entry.get("rot", []))
        parent = _support_parent(body_id, constraints, ground)
        category = str(entry.get("category", ""))
        affects = {"trans": entry.get("trans", []), "rot": rot}

        if "spin_z" in category or rot == ["z"]:
            suggestions.append(
                {
                    "type": "lock_orthogonal_to",
                    "child": body_id,
                    "target": parent,
                    "affects": affects,
                    "note": "fully orthogonalize to support (removes spin-z gauge)",
                }
            )
        elif len(rot) == 1:
            axis = rot[0]
            suggestions.append(
                {
                    "type": "yaw_free",
                    "child": body_id,
                    "target": parent,
                    "yaw_axis": f"+{axis}",
                    "affects": affects,
                    "note": f"lock two axes, leave yaw about {axis} free",
                }
            )
        elif rot:
            suggestions.append(
                {
                    "type": "lock_orthogonal_to",
                    "child": body_id,
                    "target": parent,
                    "affects": affects,
                    "note": f"lock rotation ({','.join(rot)}) to support",
                }
            )

    return suggestions[:8]


def gauge_free_to_rotation_issues(gauge_free: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for entry in gauge_free:
        body_id = str(entry.get("body", "?"))
        category = str(entry.get("category", "gauge"))
        if "spin_z" in category:
            issues.append(
                {
                    "body": body_id,
                    "reason": category,
                    "hint": f"add axis_parallel for {body_id}.axis_x or .axis_y to support",
                }
            )
        elif entry.get("rot"):
            issues.append(
                {
                    "body": body_id,
                    "reason": category,
                    "hint": (
                        f"add axis_parallel locks for rotation "
                        f"({','.join(entry['rot'])})"
                    ),
                }
            )
    return issues[:8]


def constraint_residual_max(
    constraint: CompiledConstraint,
    poses: dict[str, BodyPose],
) -> float:
    values = constraint.residual_fn(poses)
    if not values:
        return 0.0
    return float(np.max(np.abs(values)))


def find_overconstrained_constraints(
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    threshold: float,
) -> list[CompiledConstraint]:
    over: list[CompiledConstraint] = []
    for constraint in compiled:
        if constraint.constraint_id == "ground_fix":
            continue
        if constraint_residual_max(constraint, poses) > threshold:
            over.append(constraint)
    return over


def _constraint_type_label(constraint_id: str, raw_constraints: list[dict[str, Any]]) -> str:
    for constraint in raw_constraints:
        if str(constraint.get("id")) == constraint_id:
            return str(constraint.get("type", "constraint"))
    return "constraint"


def describe_conflict_set(
    mus_ids: list[str],
    raw_constraints: list[dict[str, Any]],
) -> str:
    types: list[str] = []
    for cid in mus_ids:
        label = _constraint_type_label(cid, raw_constraints)
        if label not in types:
            types.append(label)
    if len(types) == 1:
        return f"{types[0]} 自相矛盾或重复约束"
    return " + ".join(types) + " 矛盾"


def find_mus(
    *,
    compiled: list[CompiledConstraint],
    raw_constraints: list[dict[str, Any]],
    poses: dict[str, BodyPose],
    threshold: float,
    subset_solve,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Delta-debug a minimal unsatisfiable subset (P2b).

    ``subset_solve(exclude_id)`` re-solves without the given constraint id and
    returns new body poses.
    """
    warnings: list[str] = []
    over = find_overconstrained_constraints(compiled, poses, threshold)
    if not over:
        return [], warnings

    over_ids = [constraint.constraint_id for constraint in over]
    if len(over) > MUS_MAX_OVER:
        warnings.append("conflict_set_too_large: MUS skipped, returning candidates")
        return [
            {
                "hint": "conflict_set_too_large",
                "candidates": over_ids[:MUS_MAX_OVER],
            }
        ], warnings

    by_id = {constraint.constraint_id: constraint for constraint in compiled}
    mus_ids = list(over_ids)

    for cid in list(mus_ids):
        try:
            trial_poses = subset_solve(cid)
        except Exception:
            continue
        still_over = False
        for other_id in mus_ids:
            if other_id == cid:
                continue
            other = by_id.get(other_id)
            if other is None:
                continue
            if constraint_residual_max(other, trial_poses) > threshold:
                still_over = True
                break
        if not still_over:
            mus_ids.remove(cid)

    if not mus_ids:
        return [], warnings

    return [
        {
            "ids": mus_ids[:MUS_REPORT_LIMIT],
            "reason": describe_conflict_set(mus_ids, raw_constraints),
        }
    ], warnings


def derive_status_v2(
    *,
    solve_ok: bool,
    residual_max: float,
    mating_free: list[dict[str, Any]],
    gauge_free: list[dict[str, Any]],
    assumed_locks: list[dict[str, Any]],
    unmatched_gauge: list[dict[str, Any]],
    dof_policy: dict[str, Any],
    conflicts: list[dict[str, Any]] | None = None,
    witness_branches: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    ot = float(dof_policy.get("overconstrained_threshold", 1e-4))
    mating_policy = str(dof_policy.get("mating_policy", "strict"))
    gauge_policy = str(dof_policy.get("gauge_policy", "require"))
    strict_ok = bool(dof_policy.get("strict_ok", False))
    conflicts = conflicts or []

    if not solve_ok:
        return "solve_failed", warnings

    if residual_max > ot and conflicts and not conflicts[0].get("hint"):
        return "overconstrained", warnings

    if residual_max > ot and not conflicts:
        return "solve_failed", warnings

    if mating_free:
        if mating_policy == "permissive":
            warnings.append("mating_policy=permissive: mating DOF left at solved pose")
            if not gauge_free and not unmatched_gauge:
                return ("ok_assumed" if assumed_locks else "ok"), warnings
        else:
            return "underconstrained", warnings

    if gauge_free or unmatched_gauge:
        if gauge_policy == "require":
            return "underconstrained", warnings
        if gauge_policy == "enumerate":
            if witness_branches:
                return "underconstrained", warnings
            if gauge_free:
                warnings.append("witness_branches_empty: no discrete gauge candidates resolved")
            return "underconstrained", warnings
        if unmatched_gauge:
            warnings.append(
                "unmatched_gauge: "
                + ", ".join(str(g.get("body", "?")) for g in unmatched_gauge)
            )
            return "underconstrained", warnings
        if assumed_locks:
            status = "ok_assumed"
            if strict_ok:
                warnings.append("strict_ok: assumed_locks present")
            return status, warnings
        return "underconstrained", warnings

    if assumed_locks:
        if strict_ok:
            warnings.append("strict_ok: assumed_locks present")
        return "ok_assumed", warnings

    return "ok", warnings
