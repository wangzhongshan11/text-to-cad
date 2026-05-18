"""P3a: DR-style sub-cluster solve for the ``free`` rotation bucket."""

from __future__ import annotations

from typing import Any, Callable

from .clustering import cluster_coupled_bodies, should_decompose_free_bucket
from .constraints import CompiledConstraint
from .state import BodyPose


def _cluster_has_constraints(
    cluster: tuple[str, ...],
    compiled: list[CompiledConstraint],
) -> bool:
    """True when any compiled constraint references a cluster member."""
    cluster_set = set(cluster)
    for constraint in compiled:
        if any(body_id in cluster_set for body_id in constraint.body_ids):
            return True
    return False


def free_cluster_summary(
    free_body_ids: tuple[str, ...],
    compiled: list,
) -> list[dict[str, Any]]:
    """Report sub-clusters for LLM / debug (transparent to spec author)."""
    clusters = cluster_coupled_bodies(free_body_ids, compiled)
    return [
        {
            "id": f"free_{index}",
            "bodies": list(cluster),
            "size": len(cluster),
        }
        for index, cluster in enumerate(clusters, start=1)
    ]


def solve_free_bucket(
    free_body_ids: tuple[str, ...],
    *,
    scipy_solve_fn: Callable[..., tuple],
    scipy_solve_kwargs: dict[str, Any],
    min_subcluster_bodies: int = 2,
) -> tuple[
    dict[str, BodyPose],
    float,
    bool,
    str,
    int,
    bool,
    list[dict[str, Any]],
    bool,
]:
    """Solve free bodies, using per-cluster scipy when the constraint graph splits."""
    if not free_body_ids:
        return {}, 0.0, True, "no free bodies", 0, True, [], False

    cluster_report = free_cluster_summary(free_body_ids, scipy_solve_kwargs["compiled"])

    if not should_decompose_free_bucket(
        free_body_ids,
        scipy_solve_kwargs["compiled"],
        min_bodies=min_subcluster_bodies,
    ):
        poses, residual_max, solve_ok, message, nfev, converged = scipy_solve_fn(
            solve_ids=free_body_ids,
            **scipy_solve_kwargs,
        )
        return poses, residual_max, solve_ok, message, nfev, converged, cluster_report, False

    clusters = cluster_coupled_bodies(free_body_ids, scipy_solve_kwargs["compiled"])

    poses = dict(scipy_solve_kwargs.get("initial_poses") or {})
    residual_max = 0.0
    solve_ok = True
    messages: list[str] = []
    total_nfev = 0
    converged = True

    compiled = scipy_solve_kwargs["compiled"]
    ordered = sorted(clusters, key=len, reverse=True)
    for cluster in ordered:
        if not _cluster_has_constraints(cluster, compiled):
            continue
        cluster_poses, cluster_residual, cluster_ok, message, nfev, cluster_conv = scipy_solve_fn(
            solve_ids=cluster,
            initial_poses=poses,
            residual_active_bodies=frozenset(cluster),
            **{k: v for k, v in scipy_solve_kwargs.items() if k != "initial_poses"},
        )
        poses = cluster_poses
        residual_max = max(residual_max, cluster_residual)
        solve_ok = solve_ok and (cluster_ok or cluster_conv)
        converged = converged and cluster_conv
        total_nfev += nfev
        messages.append(f"cluster[{','.join(cluster)}]: {message}")

    polish_kwargs = {
        k: v for k, v in scipy_solve_kwargs.items() if k != "initial_poses"
    }
    poses, polish_residual, polish_ok, polish_msg, polish_nfev, polish_conv = scipy_solve_fn(
        solve_ids=free_body_ids,
        initial_poses=poses,
        **polish_kwargs,
    )
    total_nfev += polish_nfev
    messages.append(f"polish: {polish_msg}")

    return (
        poses,
        polish_residual,
        polish_ok,
        "; ".join(messages),
        total_nfev,
        polish_conv,
        cluster_report,
        True,
    )
