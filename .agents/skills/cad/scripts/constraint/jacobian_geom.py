"""Geometric Jacobians for world-frame features w.r.t. packed body pose (7D)."""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.spatial.transform import Rotation

from .state import (
    STATE_DIM,
    BodyPose,
    normalize_quaternion_xyzw,
    quaternion_xyzw_to_rotation_matrix,
    transform_local_direction,
    transform_local_point,
)


def normalize_quaternion_jacobian(q_raw: np.ndarray) -> np.ndarray:
    """4×4 Jacobian of normalized xyzw quaternion w.r.t. raw components."""
    q_raw = np.asarray(q_raw, dtype=float).reshape(4)
    scale = float(np.linalg.norm(q_raw))
    if scale <= 1e-15:
        return np.eye(4, dtype=float)
    unit = q_raw / scale
    return (np.eye(4, dtype=float) - np.outer(unit, q_raw)) / scale


def rotated_vector_jacobian_unit_quat(
    v_local: np.ndarray,
    quat_unit: np.ndarray,
    *,
    eps: float = 1e-7,
) -> np.ndarray:
    """∂(R(q) @ v)/∂q for unit quaternion q = (x, y, z, w). Returns 3×4."""
    quat = np.asarray(quat_unit, dtype=float).reshape(4)
    vector = np.asarray(v_local, dtype=float).reshape(3)
    base = Rotation.from_quat(quat).apply(vector)
    jacobian = np.zeros((3, 4), dtype=float)
    for index in range(4):
        step = np.zeros(4, dtype=float)
        step[index] = eps
        trial = quat + step
        trial = trial / (np.linalg.norm(trial) + 1e-15)
        forward = Rotation.from_quat(trial).apply(vector)
        jacobian[:, index] = (forward - base) / eps
    return jacobian


def normalized_vector_jacobian(vec: np.ndarray) -> np.ndarray:
    """3×3 Jacobian of v/||v|| w.r.t. v (before normalization)."""
    vec = np.asarray(vec, dtype=float).reshape(3)
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-15:
        return np.eye(3, dtype=float)
    unit = vec / norm
    return (np.eye(3, dtype=float) - np.outer(unit, unit)) / norm


def pose_to_vector(pose: BodyPose) -> np.ndarray:
    values = list(pose.translation) + list(pose.quaternion_xyzw)
    return np.asarray(values, dtype=float)


def point_world_jacobian(
    local_point: tuple[float, float, float],
    pose: BodyPose,
) -> np.ndarray:
    """3×7 Jacobian of world point w.r.t. translation + raw quaternion."""
    q_raw = np.asarray(pose.quaternion_xyzw, dtype=float)
    q_unit = np.asarray(normalize_quaternion_xyzw(pose.quaternion_xyzw), dtype=float)
    v_local = np.asarray(local_point, dtype=float)
    jacobian = np.zeros((3, STATE_DIM), dtype=float)
    jacobian[:, 0:3] = np.eye(3, dtype=float)
    d_rot = rotated_vector_jacobian_unit_quat(v_local, q_unit)
    jacobian[:, 3:7] = d_rot @ normalize_quaternion_jacobian(q_raw)
    return jacobian


def direction_world_jacobian(
    local_direction: tuple[float, float, float],
    pose: BodyPose,
) -> np.ndarray:
    """3×7 Jacobian of normalized world direction w.r.t. pose."""
    q_raw = np.asarray(pose.quaternion_xyzw, dtype=float)
    q_unit = np.asarray(normalize_quaternion_xyzw(pose.quaternion_xyzw), dtype=float)
    v_local = np.asarray(local_direction, dtype=float)
    rotated = quaternion_xyzw_to_rotation_matrix(tuple(q_unit)) @ v_local
    jacobian = np.zeros((3, STATE_DIM), dtype=float)
    d_rot = rotated_vector_jacobian_unit_quat(v_local, q_unit)
    d_unnorm = d_rot @ normalize_quaternion_jacobian(q_raw)
    jacobian[:, 3:7] = normalized_vector_jacobian(rotated) @ d_unnorm
    return jacobian


def plane_world_jacobians(
    local_origin: tuple[float, float, float],
    local_normal: tuple[float, float, float],
    pose: BodyPose,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (3×7 origin Jacobian, 3×7 unit-normal Jacobian)."""
    origin_jacobian = point_world_jacobian(local_origin, pose)
    normal_jacobian = direction_world_jacobian(local_normal, pose)
    return origin_jacobian, normal_jacobian


def body_column_offset(body_ids: tuple[str, ...], body_id: str) -> int:
    return body_ids.index(body_id) * STATE_DIM


def scatter_body_block(
    jacobian: np.ndarray,
    *,
    body_ids: tuple[str, ...],
    body_id: str,
    block: np.ndarray,
    row_start: int,
) -> None:
    col = body_column_offset(body_ids, body_id)
    rows = block.shape[0]
    jacobian[row_start : row_start + rows, col : col + STATE_DIM] = block


def perturb_pose(pose: BodyPose, column: int, eps: float) -> BodyPose:
    vector = pose_to_vector(pose)
    vector = vector.copy()
    vector[column] += eps
    return BodyPose(
        tuple(float(vector[index]) for index in range(3)),
        tuple(float(vector[3 + index]) for index in range(4)),
    )


def scalar_residual_pose_jacobian(
    value_fn: Callable[[dict[str, BodyPose]], float],
    poses: dict[str, BodyPose],
    body_id: str,
    *,
    eps: float = 1e-7,
) -> np.ndarray:
    """1×7 gradient of a scalar assembly residual w.r.t. one body's pose."""
    from typing import Callable as _Callable

    del _Callable
    base = float(value_fn(poses))
    gradient = np.zeros(STATE_DIM, dtype=float)
    for column in range(STATE_DIM):
        trial = dict(poses)
        trial[body_id] = perturb_pose(poses[body_id], column, eps)
        gradient[column] = (float(value_fn(trial)) - base) / eps
    return gradient


def point_world_jacobian_fd(
    local_point: tuple[float, float, float],
    pose: BodyPose,
    *,
    eps: float = 1e-7,
) -> np.ndarray:
    """Finite-difference reference for tests."""
    base = transform_local_point(
        local_point, pose.translation, pose.quaternion_xyzw
    )
    jacobian = np.zeros((3, STATE_DIM), dtype=float)
    vector = pose_to_vector(pose)
    for col in range(STATE_DIM):
        step = np.zeros(STATE_DIM, dtype=float)
        step[col] = eps
        trial_translation = tuple(float(vector[index] + step[index]) for index in range(3))
        trial_quat = tuple(float(vector[3 + index] + step[3 + index]) for index in range(4))
        trial_pose = BodyPose(trial_translation, trial_quat)
        forward = transform_local_point(
            local_point, trial_pose.translation, trial_pose.quaternion_xyzw
        )
        jacobian[:, col] = (forward - base) / eps
    return jacobian
