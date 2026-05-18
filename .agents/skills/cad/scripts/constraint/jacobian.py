"""Analytic constraint Jacobians (P2c-2)."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .constraints import CompiledConstraint
from .features import (
    FeatureKind,
    get_feature,
    parse_feature_ref,
    world_axis,
    world_plane,
    world_point,
)
from .jacobian_geom import (
    body_column_offset,
    direction_world_jacobian,
    plane_world_jacobians,
    point_world_jacobian,
    scalar_residual_pose_jacobian,
    scatter_body_block,
)
from .primitives import PrimitiveBody
from .state import STATE_DIM, BodyPose


JacobianFn = Callable[[dict[str, BodyPose], tuple[str, ...]], np.ndarray]


def _direction_parallel_jacobian_blocks(
    ja: np.ndarray,
    jb: np.ndarray,
    *,
    opposed: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    if opposed:
        return ja, jb
    return ja, -jb


def _axis_coaxial_distance(
    catalog: dict[str, PrimitiveBody],
    poses: dict[str, BodyPose],
    ref_a: Any,
    ref_b: Any,
) -> float:
    axis_a = world_axis(catalog, poses, ref_a)
    axis_b = world_axis(catalog, poses, ref_b)
    delta = axis_a.origin - axis_b.origin
    cross = np.cross(axis_a.direction, axis_b.direction)
    cross_norm = float(np.linalg.norm(cross))
    if cross_norm < 1e-8:
        along = axis_b.direction / (np.linalg.norm(axis_b.direction) + 1e-15)
        perpendicular = delta - along * float(np.dot(delta, along))
        return float(np.linalg.norm(perpendicular))
    return float(np.linalg.norm(np.cross(delta, cross)) / cross_norm)


def _compile_fix_jacobian(constraint: dict[str, Any]) -> JacobianFn:
    from .state import identity_pose, pack_poses, unpack_poses

    body_id = str(constraint.get("body", constraint.get("a", "")))

    def _fix_residual_values(poses: dict[str, BodyPose]) -> np.ndarray:
        pose = poses[body_id]
        target_pose = identity_pose()
        values: list[float] = []
        values.extend(float(pose.translation[index] - target_pose.translation[index]) for index in range(3))
        values.extend(
            float(pose.quaternion_xyzw[index] - target_pose.quaternion_xyzw[index]) for index in range(4)
        )
        return np.asarray(values, dtype=float)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        eps = 1e-7
        vector = pack_poses(body_ids, poses)
        base = _fix_residual_values(poses)
        jacobian = np.zeros((7, len(body_ids) * STATE_DIM), dtype=float)
        col = body_column_offset(body_ids, body_id)
        for column in range(STATE_DIM):
            step = np.zeros_like(vector)
            step[col + column] = eps
            trial_poses = unpack_poses(body_ids, vector + step)
            forward = _fix_residual_values(trial_poses)
            jacobian[:, col + column] = (forward - base) / eps
        return jacobian

    return jacobian_fn


def _compile_point_coincident_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    ref_a = parse_feature_ref(str(constraint["a"]))
    ref_b = parse_feature_ref(str(constraint["b"]))
    feature_a = get_feature(catalog, ref_a, FeatureKind.POINT)
    feature_b = get_feature(catalog, ref_b, FeatureKind.POINT)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        ja = point_world_jacobian(feature_a.position, poses[ref_a.body_id])
        jb = point_world_jacobian(feature_b.position, poses[ref_b.body_id])
        jacobian = np.zeros((3, len(body_ids) * STATE_DIM), dtype=float)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_a.body_id, block=ja, row_start=0)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_b.body_id, block=-jb, row_start=0)
        return jacobian

    return jacobian_fn


def _compile_plane_coincident_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    ref_a = parse_feature_ref(str(constraint["a"]))
    ref_b = parse_feature_ref(str(constraint["b"]))
    opposed = bool(constraint.get("opposed", constraint.get("contact", False)))
    feature_a = get_feature(catalog, ref_a, FeatureKind.PLANE)
    feature_b = get_feature(catalog, ref_b, FeatureKind.PLANE)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        plane_a = world_plane(catalog, poses, ref_a)
        plane_b = world_plane(catalog, poses, ref_b)
        ja_o, ja_n = plane_world_jacobians(feature_a.origin, feature_a.normal, poses[ref_a.body_id])
        jb_o, jb_n = plane_world_jacobians(feature_b.origin, feature_b.normal, poses[ref_b.body_id])
        block_a, block_b = _direction_parallel_jacobian_blocks(ja_n, jb_n, opposed=opposed)
        delta = plane_a.origin - plane_b.origin
        nb = plane_b.normal
        coplanar_a = nb.reshape(1, 3) @ ja_o
        coplanar_b = (-nb.reshape(1, 3) @ jb_o) + (delta.reshape(1, 3) @ jb_n)

        jacobian = np.zeros((4, len(body_ids) * STATE_DIM), dtype=float)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_a.body_id, block=block_a, row_start=0)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_b.body_id, block=block_b, row_start=0)
        col_a = body_column_offset(body_ids, ref_a.body_id)
        col_b = body_column_offset(body_ids, ref_b.body_id)
        jacobian[3, col_a : col_a + STATE_DIM] = coplanar_a.reshape(-1)
        jacobian[3, col_b : col_b + STATE_DIM] = coplanar_b.reshape(-1)
        return jacobian

    return jacobian_fn


def _compile_axis_parallel_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    ref_a = parse_feature_ref(str(constraint["a"]))
    ref_b = parse_feature_ref(str(constraint["b"]))
    opposed = bool(constraint.get("opposed", False))
    feature_a = get_feature(catalog, ref_a, FeatureKind.AXIS)
    feature_b = get_feature(catalog, ref_b, FeatureKind.AXIS)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        ja = direction_world_jacobian(feature_a.direction, poses[ref_a.body_id])
        jb = direction_world_jacobian(feature_b.direction, poses[ref_b.body_id])
        block_a, block_b = _direction_parallel_jacobian_blocks(ja, jb, opposed=opposed)
        jacobian = np.zeros((3, len(body_ids) * STATE_DIM), dtype=float)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_a.body_id, block=block_a, row_start=0)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_b.body_id, block=block_b, row_start=0)
        return jacobian

    return jacobian_fn


def _compile_axis_coaxial_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    ref_a = parse_feature_ref(str(constraint["a"]))
    ref_b = parse_feature_ref(str(constraint["b"]))
    feature_a = get_feature(catalog, ref_a, FeatureKind.AXIS)
    feature_b = get_feature(catalog, ref_b, FeatureKind.AXIS)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        ja_d = direction_world_jacobian(feature_a.direction, poses[ref_a.body_id])
        jb_d = direction_world_jacobian(feature_b.direction, poses[ref_b.body_id])
        block_a, block_b = _direction_parallel_jacobian_blocks(ja_d, jb_d, opposed=False)

        def distance_fn(trial_poses: dict[str, BodyPose]) -> float:
            return _axis_coaxial_distance(catalog, trial_poses, ref_a, ref_b)

        dist_a = scalar_residual_pose_jacobian(distance_fn, poses, ref_a.body_id)
        dist_b = scalar_residual_pose_jacobian(distance_fn, poses, ref_b.body_id)

        jacobian = np.zeros((4, len(body_ids) * STATE_DIM), dtype=float)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_a.body_id, block=block_a, row_start=0)
        scatter_body_block(jacobian, body_ids=body_ids, body_id=ref_b.body_id, block=block_b, row_start=0)
        col_a = body_column_offset(body_ids, ref_a.body_id)
        col_b = body_column_offset(body_ids, ref_b.body_id)
        jacobian[3, col_a : col_a + STATE_DIM] = dist_a
        jacobian[3, col_b : col_b + STATE_DIM] = dist_b
        return jacobian

    return jacobian_fn


def _compile_plane_distance_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    ref_a = parse_feature_ref(str(constraint["a"]))
    ref_b = parse_feature_ref(str(constraint["b"]))
    feature_a = get_feature(catalog, ref_a, FeatureKind.PLANE)
    feature_b = get_feature(catalog, ref_b, FeatureKind.PLANE)

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        plane_a = world_plane(catalog, poses, ref_a)
        plane_b = world_plane(catalog, poses, ref_b)
        ja_o, _ = plane_world_jacobians(feature_a.origin, feature_a.normal, poses[ref_a.body_id])
        jb_o, jb_n = plane_world_jacobians(feature_b.origin, feature_b.normal, poses[ref_b.body_id])
        nb = plane_b.normal
        delta = plane_a.origin - plane_b.origin
        row_a = nb.reshape(1, 3) @ ja_o
        row_b = (-nb.reshape(1, 3) @ jb_o) + (delta.reshape(1, 3) @ jb_n)
        jacobian = np.zeros((1, len(body_ids) * STATE_DIM), dtype=float)
        col_a = body_column_offset(body_ids, ref_a.body_id)
        col_b = body_column_offset(body_ids, ref_b.body_id)
        jacobian[0, col_a : col_a + STATE_DIM] = row_a.reshape(-1)
        jacobian[0, col_b : col_b + STATE_DIM] = row_b.reshape(-1)
        return jacobian

    return jacobian_fn


def _compile_point_plane_offset_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn:
    point_ref = parse_feature_ref(str(constraint.get("point", constraint.get("a", ""))))
    plane_ref = parse_feature_ref(str(constraint.get("plane", constraint.get("b", ""))))
    point_feature = get_feature(catalog, point_ref, FeatureKind.POINT)
    plane_feature = get_feature(catalog, plane_ref, FeatureKind.PLANE)
    in_plane = constraint.get("in_plane")

    if in_plane is not None:
        axis = str(in_plane).lower()

        def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
            def offset_fn(trial_poses: dict[str, BodyPose]) -> float:
                trial_point = world_point(catalog, trial_poses, point_ref).position
                trial_plane = world_plane(catalog, trial_poses, plane_ref)
                tu, tv = trial_plane.tangent_axes()
                tangent = tu if axis == "x" else tv
                return float(np.dot(trial_point - trial_plane.origin, tangent))

            row_p = scalar_residual_pose_jacobian(offset_fn, poses, point_ref.body_id)
            row_pl = scalar_residual_pose_jacobian(offset_fn, poses, plane_ref.body_id)
            jacobian = np.zeros((1, len(body_ids) * STATE_DIM), dtype=float)
            col_p = body_column_offset(body_ids, point_ref.body_id)
            col_pl = body_column_offset(body_ids, plane_ref.body_id)
            jacobian[0, col_p : col_p + STATE_DIM] = row_p
            jacobian[0, col_pl : col_pl + STATE_DIM] = row_pl
            return jacobian

        return jacobian_fn

    def jacobian_fn(poses: dict[str, BodyPose], body_ids: tuple[str, ...]) -> np.ndarray:
        point = world_point(catalog, poses, point_ref).position
        plane = world_plane(catalog, poses, plane_ref)
        jp = point_world_jacobian(point_feature.position, poses[point_ref.body_id])
        jo, jn = plane_world_jacobians(
            plane_feature.origin, plane_feature.normal, poses[plane_ref.body_id]
        )
        nb = plane.normal
        delta = point - plane.origin
        row_p = nb.reshape(1, 3) @ jp
        row_o = (-nb.reshape(1, 3) @ jo) + (delta.reshape(1, 3) @ jn)
        jacobian = np.zeros((1, len(body_ids) * STATE_DIM), dtype=float)
        col_p = body_column_offset(body_ids, point_ref.body_id)
        col_pl = body_column_offset(body_ids, plane_ref.body_id)
        jacobian[0, col_p : col_p + STATE_DIM] = row_p.reshape(-1)
        jacobian[0, col_pl : col_pl + STATE_DIM] = row_o.reshape(-1)
        return jacobian

    return jacobian_fn


def compile_constraint_jacobian(
    constraint: dict[str, Any],
    catalog: dict[str, PrimitiveBody],
) -> JacobianFn | None:
    constraint_type = str(constraint["type"])
    builders: dict[str, Callable[[], JacobianFn]] = {
        "fix": lambda: _compile_fix_jacobian(constraint),
        "point_coincident": lambda: _compile_point_coincident_jacobian(constraint, catalog),
        "plane_coincident": lambda: _compile_plane_coincident_jacobian(constraint, catalog),
        "axis_coaxial": lambda: _compile_axis_coaxial_jacobian(constraint, catalog),
        "axis_parallel": lambda: _compile_axis_parallel_jacobian(constraint, catalog),
        "plane_distance": lambda: _compile_plane_distance_jacobian(constraint, catalog),
        "point_plane_offset": lambda: _compile_point_plane_offset_jacobian(constraint, catalog),
    }
    builder = builders.get(constraint_type)
    if builder is None:
        return None
    return builder()


def attach_jacobian_fns(
    compiled: list[CompiledConstraint],
    constraints: list[dict[str, Any]],
    catalog: dict[str, PrimitiveBody],
) -> list[CompiledConstraint]:
    updated: list[CompiledConstraint] = []
    for constraint, compiled_row in zip(constraints, compiled):
        jacobian_fn = compile_constraint_jacobian(constraint, catalog)
        if jacobian_fn is None:
            updated.append(compiled_row)
            continue
        updated.append(
            CompiledConstraint(
                constraint_id=compiled_row.constraint_id,
                constraint_type=compiled_row.constraint_type,
                residual_fn=compiled_row.residual_fn,
                body_ids=compiled_row.body_ids,
                jacobian_fn=jacobian_fn,
            )
        )
    return updated


def quaternion_norm_jacobian_rows(
    body_ids: tuple[str, ...],
    poses: dict[str, BodyPose],
    *,
    numeric_fn: Callable[[np.ndarray], np.ndarray] | None = None,
    vector: np.ndarray | None = None,
) -> np.ndarray:
    """Quaternion normalization rows; zeros analytically (residual identically zero after normalize)."""
    del poses
    if numeric_fn is not None and vector is not None:
        from .dof import dense_numeric_jacobian

        full = dense_numeric_jacobian(numeric_fn, vector)
        return full[0 : len(body_ids), :]
    rows = len(body_ids)
    cols = len(body_ids) * STATE_DIM
    return np.zeros((rows, cols), dtype=float)


def analytic_assembly_jacobian(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    *,
    numeric_fn: Callable[[np.ndarray], np.ndarray] | None = None,
    vector: np.ndarray | None = None,
) -> np.ndarray | None:
    if numeric_fn is not None and vector is not None:
        quat_rows = quaternion_norm_jacobian_rows(
            body_ids, poses, numeric_fn=numeric_fn, vector=vector
        )
    else:
        quat_rows = quaternion_norm_jacobian_rows(body_ids, poses)

    rows = len(body_ids)
    for constraint in compiled:
        rows += len(constraint.residual_fn(poses))
    cols = len(body_ids) * STATE_DIM
    jacobian = np.zeros((rows, cols), dtype=float)
    row = len(body_ids)
    jacobian[0:row, :] = quat_rows

    for constraint in compiled:
        if constraint.jacobian_fn is None:
            return None
        block = constraint.jacobian_fn(poses, body_ids)
        height = block.shape[0]
        jacobian[row : row + height, :] = block
        row += height
    return jacobian


def verify_analytic_jacobian(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    *,
    numeric_fn: Callable[[np.ndarray], np.ndarray],
    vector: np.ndarray,
    tol: float = 1e-4,
) -> dict[str, Any]:
    from .dof import sparse_numeric_jacobian

    analytic = analytic_assembly_jacobian(
        body_ids, compiled, poses, numeric_fn=numeric_fn, vector=vector
    )
    numeric = sparse_numeric_jacobian(
        numeric_fn,
        vector,
        body_ids=body_ids,
        compiled=compiled,
    )
    if analytic is None:
        return {"ok": False, "reason": "missing_analytic_jacobian", "max_diff": None}
    max_diff = float(np.max(np.abs(analytic - numeric)))
    return {
        "ok": max_diff < tol,
        "max_diff": max_diff,
        "analytic_shape": list(analytic.shape),
        "numeric_shape": list(numeric.shape),
    }
