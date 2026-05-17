from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


# State per body: translation (3) + quaternion xyzw (4) = 7 scalars
STATE_DIM = 7
QUAT_NORM_WEIGHT = 10.0


@dataclass(frozen=True)
class BodyPose:
    translation: tuple[float, float, float]
    quaternion_xyzw: tuple[float, float, float, float]  # scipy / build123d style


def identity_pose() -> BodyPose:
    return BodyPose((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def normalize_quaternion_xyzw(quat: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, z, w = quat
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length <= 1e-15:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / length, y / length, z / length, w / length)


def quaternion_xyzw_to_rotation_matrix(quat: tuple[float, float, float, float]) -> np.ndarray:
    x, y, z, w = normalize_quaternion_xyzw(quat)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def rotation_matrix_to_quaternion_xyzw(matrix: np.ndarray) -> tuple[float, float, float, float]:
    m = np.asarray(matrix, dtype=float).reshape(3, 3)
    trace = float(m[0, 0] + m[1, 1] + m[2, 2])
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return normalize_quaternion_xyzw((x, y, z, w))


def transform_local_point(
    point: tuple[float, float, float],
    translation: tuple[float, float, float],
    quaternion_xyzw: tuple[float, float, float, float],
) -> np.ndarray:
    rotation = quaternion_xyzw_to_rotation_matrix(quaternion_xyzw)
    local = np.asarray(point, dtype=float)
    return rotation @ local + np.asarray(translation, dtype=float)


def transform_local_direction(
    direction: tuple[float, float, float],
    quaternion_xyzw: tuple[float, float, float, float],
) -> np.ndarray:
    rotation = quaternion_xyzw_to_rotation_matrix(quaternion_xyzw)
    local = np.asarray(direction, dtype=float)
    return rotation @ local


def pack_poses(body_ids: tuple[str, ...], poses: dict[str, BodyPose]) -> np.ndarray:
    values: list[float] = []
    for body_id in body_ids:
        pose = poses.get(body_id, identity_pose())
        values.extend(pose.translation)
        values.extend(pose.quaternion_xyzw)
    return np.asarray(values, dtype=float)


def unpack_poses(body_ids: tuple[str, ...], vector: np.ndarray) -> dict[str, BodyPose]:
    poses: dict[str, BodyPose] = {}
    offset = 0
    for body_id in body_ids:
        translation = tuple(float(vector[offset + index]) for index in range(3))
        quaternion = tuple(float(vector[offset + 3 + index]) for index in range(4))
        offset += STATE_DIM
        poses[body_id] = BodyPose(translation, normalize_quaternion_xyzw(quaternion))
    return poses


def pose_to_transform_matrix(pose: BodyPose) -> tuple[float, ...]:
    rotation = quaternion_xyzw_to_rotation_matrix(pose.quaternion_xyzw)
    translation = np.asarray(pose.translation, dtype=float)
    return (
        float(rotation[0, 0]),
        float(rotation[0, 1]),
        float(rotation[0, 2]),
        float(translation[0]),
        float(rotation[1, 0]),
        float(rotation[1, 1]),
        float(rotation[1, 2]),
        float(translation[1]),
        float(rotation[2, 0]),
        float(rotation[2, 1]),
        float(rotation[2, 2]),
        float(translation[2]),
        0.0,
        0.0,
        0.0,
        1.0,
    )


def quaternion_residual(quat: tuple[float, float, float, float]) -> float:
    x, y, z, w = quat
    return (x * x + y * y + z * z + w * w - 1.0) * QUAT_NORM_WEIGHT
