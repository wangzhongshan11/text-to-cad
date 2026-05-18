"""Constraint-graph clustering for coupled bodies (P3a / P2e)."""

from __future__ import annotations

from .constraints import CompiledConstraint


def cluster_coupled_bodies(
    member_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
) -> list[tuple[str, ...]]:
    """Group bodies that share at least one compiled constraint (union-find)."""
    members = tuple(sorted(set(member_ids)))
    if not members:
        return []

    member_set = set(members)
    parent = {body_id: body_id for body_id in members}

    def find(body_id: str) -> str:
        while parent[body_id] != body_id:
            parent[body_id] = parent[parent[body_id]]
            body_id = parent[body_id]
        return body_id

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for constraint in compiled:
        involved = [body_id for body_id in constraint.body_ids if body_id in member_set]
        if len(involved) < 2:
            continue
        anchor = involved[0]
        for other in involved[1:]:
            union(anchor, other)

    buckets: dict[str, list[str]] = {}
    for body_id in members:
        root = find(body_id)
        buckets.setdefault(root, []).append(body_id)

    return [tuple(sorted(cluster)) for cluster in buckets.values()]


def should_decompose_free_bucket(
    free_body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    *,
    min_bodies: int = 2,
) -> bool:
    """True when DR-style sub-clustering should replace one monolithic free solve."""
    if len(free_body_ids) < min_bodies:
        return False
    return len(cluster_coupled_bodies(free_body_ids, compiled)) > 1
