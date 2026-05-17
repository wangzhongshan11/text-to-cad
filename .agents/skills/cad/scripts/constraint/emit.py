from __future__ import annotations

from .state import BodyPose, pose_to_transform_matrix


def transforms_for_instances(poses: dict[str, BodyPose]) -> dict[str, tuple[float, ...]]:
    return {body_id: pose_to_transform_matrix(pose) for body_id, pose in poses.items()}
