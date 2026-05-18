"""P2e: 4D joint numerical solve for ``yaw_only`` bodies."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .clustering import cluster_coupled_bodies
from .constraints import CompiledConstraint
from .state import BodyPose, identity_pose
from .yaw_state import pack_yaw_poses, unpack_yaw_poses


def cluster_yaw_bodies(
    yaw_body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
) -> list[tuple[str, ...]]:
    """Group coupled ``yaw_only`` bodies into clusters (union-find on shared constraints)."""
    return cluster_coupled_bodies(yaw_body_ids, compiled)


def solve_yaw_cluster(
    cluster_ids: tuple[str, ...],
    *,
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    residual_vector_fn: Callable[[dict[str, BodyPose]], np.ndarray],
    fixed_poses: dict[str, BodyPose],
    yaw_axes: dict[str, str],
    vector0: np.ndarray,
    run_optimizer: Callable[[Callable[[np.ndarray], np.ndarray], np.ndarray], tuple],
    residual_tol: float,
) -> tuple[dict[str, BodyPose], float, bool, str, int]:
    """4·|cluster| dimensional scipy solve; other bodies held in ``fixed_poses``."""

    def residual_fn(vector: np.ndarray) -> np.ndarray:
        yaw_partial = unpack_yaw_poses(cluster_ids, vector, yaw_axes)
        poses: dict[str, BodyPose] = dict(fixed_poses)
        poses.update(yaw_partial)
        for body_id in body_ids:
            poses.setdefault(body_id, identity_pose())
        return residual_vector_fn(poses)

    solution_vector, message, converged, nfev = run_optimizer(residual_fn, vector0)
    yaw_partial = unpack_yaw_poses(cluster_ids, solution_vector, yaw_axes)
    poses: dict[str, BodyPose] = dict(fixed_poses)
    poses.update(yaw_partial)
    residual = residual_vector_fn(poses)
    residual_max = float(np.max(np.abs(residual))) if residual.size else 0.0
    solve_ok = residual_max < residual_tol or (
        converged and residual_max < max(residual_tol, 1e-4)
    )
    return yaw_partial, residual_max, solve_ok, message, nfev


def solve_yaw_bucket(
    yaw_body_ids: tuple[str, ...],
    *,
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    residual_vector_fn: Callable[[dict[str, BodyPose]], np.ndarray],
    fixed_poses: dict[str, BodyPose],
    yaw_axes: dict[str, str],
    seed_poses: dict[str, BodyPose],
    run_optimizer: Callable[[Callable[[np.ndarray], np.ndarray], np.ndarray], tuple],
    residual_tol: float,
) -> tuple[dict[str, BodyPose], float, bool, str, int]:
    """Solve all yaw clusters sequentially; return merged yaw body poses."""
    if not yaw_body_ids:
        return {}, 0.0, True, "no yaw bodies", 0

    clusters = cluster_yaw_bodies(yaw_body_ids, compiled)
    merged_yaw: dict[str, BodyPose] = {}
    total_nfev = 0
    residual_max = 0.0
    solve_ok = True
    messages: list[str] = []

    for cluster in clusters:
        vector0 = pack_yaw_poses(cluster, seed_poses, yaw_axes)
        yaw_partial, cluster_residual, cluster_ok, message, nfev = solve_yaw_cluster(
            cluster,
            body_ids=body_ids,
            compiled=compiled,
            residual_vector_fn=residual_vector_fn,
            fixed_poses={**fixed_poses, **merged_yaw},
            yaw_axes=yaw_axes,
            vector0=vector0,
            run_optimizer=run_optimizer,
            residual_tol=residual_tol,
        )
        merged_yaw.update(yaw_partial)
        fixed_poses = {**fixed_poses, **merged_yaw}
        seed_poses.update(yaw_partial)
        residual_max = max(residual_max, cluster_residual)
        solve_ok = solve_ok and cluster_ok
        total_nfev += nfev
        messages.append(message)

    return merged_yaw, residual_max, solve_ok, "; ".join(messages), total_nfev
