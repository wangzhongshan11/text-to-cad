"""P2e: 4D state (translation + yaw angle) for ``rotation_mode: yaw_only`` bodies."""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation

from .state import BodyPose, normalize_quaternion_xyzw


YAW_STATE_DIM = 4


def yaw_axis_unit_vector(yaw_axis: str) -> tuple[float, float, float]:
    axis = str(yaw_axis).strip().lower()
    if axis in {"+x", "x"}:
        return (1.0, 0.0, 0.0)
    if axis == "-x":
        return (-1.0, 0.0, 0.0)
    if axis in {"+y", "y"}:
        return (0.0, 1.0, 0.0)
    if axis == "-y":
        return (0.0, -1.0, 0.0)
    if axis in {"+z", "z"}:
        return (0.0, 0.0, 1.0)
    if axis == "-z":
        return (0.0, 0.0, -1.0)
    raise ValueError(f"invalid yaw_axis {yaw_axis!r}")


def pose_from_yaw_vector(
    translation: tuple[float, float, float] | np.ndarray,
    theta_rad: float,
    *,
    yaw_axis: str = "+z",
) -> BodyPose:
    """Build ``BodyPose`` from translation and rotation about body-local ``yaw_axis``."""
    axis = np.asarray(yaw_axis_unit_vector(yaw_axis), dtype=float)
    rotation = Rotation.from_rotvec(axis * float(theta_rad))
    quat = normalize_quaternion_xyzw(tuple(rotation.as_quat()))
    if isinstance(translation, np.ndarray):
        translation = tuple(float(translation[index]) for index in range(3))
    return BodyPose(translation, quat)


def yaw_vector_from_pose(pose: BodyPose, *, yaw_axis: str = "+z") -> np.ndarray:
    """Extract ``[tx, ty, tz, theta]`` from a pose (inverse of :func:`pose_from_yaw_vector`)."""
    axis = np.asarray(yaw_axis_unit_vector(yaw_axis), dtype=float)
    rotation = Rotation.from_quat(pose.quaternion_xyzw)
    theta = float(rotation.as_rotvec().dot(axis))
    return np.array(
        [
            float(pose.translation[0]),
            float(pose.translation[1]),
            float(pose.translation[2]),
            theta,
        ],
        dtype=float,
    )


def pack_yaw_poses(
    yaw_body_ids: tuple[str, ...],
    poses: dict[str, BodyPose],
    yaw_axes: dict[str, str],
) -> np.ndarray:
    values: list[float] = []
    for body_id in yaw_body_ids:
        axis = yaw_axes.get(body_id, "+z")
        values.extend(yaw_vector_from_pose(poses[body_id], yaw_axis=axis).tolist())
    return np.asarray(values, dtype=float)


def unpack_yaw_poses(
    yaw_body_ids: tuple[str, ...],
    vector: np.ndarray,
    yaw_axes: dict[str, str],
) -> dict[str, BodyPose]:
    vector = np.asarray(vector, dtype=float)
    poses: dict[str, BodyPose] = {}
    offset = 0
    for body_id in yaw_body_ids:
        block = vector[offset : offset + YAW_STATE_DIM]
        offset += YAW_STATE_DIM
        poses[body_id] = pose_from_yaw_vector(
            block[0:3],
            float(block[3]),
            yaw_axis=yaw_axes.get(body_id, "+z"),
        )
    return poses


