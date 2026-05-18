from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .constraints import CompiledConstraint
from .state import STATE_DIM, BodyPose, unpack_poses


def numeric_jacobian(
    residual_fn: Callable[[np.ndarray], np.ndarray],
    vector: np.ndarray,
    *,
    eps: float = 1e-7,
    body_ids: tuple[str, ...] | None = None,
    compiled: list[CompiledConstraint] | None = None,
    poses: dict[str, BodyPose] | None = None,
    use_analytic: bool = True,
) -> np.ndarray:
    """Jacobian for assembly residual.

    Prefers analytic constraint blocks (P2c-2) when available, with quaternion rows
    from sparse numeric FD. Falls back to P2c-1 sparse numeric Jacobian.
    """
    if (
        use_analytic
        and body_ids is not None
        and compiled is not None
        and poses is not None
    ):
        from .jacobian import analytic_assembly_jacobian

        analytic = analytic_assembly_jacobian(
            body_ids,
            compiled,
            poses,
            numeric_fn=residual_fn,
            vector=vector,
        )
        if analytic is not None:
            return analytic
    if body_ids is not None and compiled is not None:
        return sparse_numeric_jacobian(
            residual_fn,
            vector,
            body_ids=body_ids,
            compiled=compiled,
            eps=eps,
        )
    return dense_numeric_jacobian(residual_fn, vector, eps=eps)


def dense_numeric_jacobian(
    residual_fn: Callable[[np.ndarray], np.ndarray],
    vector: np.ndarray,
    *,
    eps: float = 1e-7,
) -> np.ndarray:
    base = np.asarray(residual_fn(vector), dtype=float)
    rows = base.size
    cols = vector.size
    jacobian = np.zeros((rows, cols), dtype=float)
    for index in range(cols):
        step = np.zeros(cols, dtype=float)
        step[index] = eps
        forward = np.asarray(residual_fn(vector + step), dtype=float)
        jacobian[:, index] = (forward - base) / eps
    return jacobian


def _body_column_range(body_ids: tuple[str, ...]) -> dict[str, tuple[int, int]]:
    return {
        body_id: (index * STATE_DIM, (index + 1) * STATE_DIM)
        for index, body_id in enumerate(body_ids)
    }


def _constraint_row_blocks(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
) -> list[tuple[int, int, tuple[str, ...]]]:
    """Return ``(row_start, row_end, body_ids)`` for each compiled constraint block."""
    blocks: list[tuple[int, int, tuple[str, ...]]] = []
    row = len(body_ids)
    for constraint in compiled:
        dim = len(constraint.residual_fn(poses))
        blocks.append((row, row + dim, constraint.body_ids))
        row += dim
    return blocks


def sparse_numeric_jacobian(
    residual_fn: Callable[[np.ndarray], np.ndarray],
    vector: np.ndarray,
    *,
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    eps: float = 1e-7,
    eval_counter: list[int] | None = None,
) -> np.ndarray:
    """Sparse-pattern numeric Jacobian (P2c-1)."""
    vector = np.asarray(vector, dtype=float)
    cols = vector.size

    def counted_residual(value: np.ndarray) -> np.ndarray:
        if eval_counter is not None:
            eval_counter[0] += 1
        return np.asarray(residual_fn(value), dtype=float)

    base = counted_residual(vector)
    rows = base.size
    jacobian = np.zeros((rows, cols), dtype=float)

    column_ranges = _body_column_range(body_ids)
    bodies_in_constraints: set[str] = set()
    for constraint in compiled:
        bodies_in_constraints.update(constraint.body_ids)

    columns_to_perturb: list[int] = []
    for body_id in bodies_in_constraints:
        start, end = column_ranges[body_id]
        columns_to_perturb.extend(range(start, end))

    poses = unpack_poses(body_ids, vector)
    col_to_rows: dict[int, set[int]] = {}
    for row_start, row_end, block_body_ids in _constraint_row_blocks(
        body_ids, compiled, poses
    ):
        affected_rows = list(range(row_start, row_end))
        for body_id in block_body_ids:
            start, end = column_ranges[body_id]
            for col in range(start, end):
                col_to_rows.setdefault(col, set()).update(affected_rows)

    for col in columns_to_perturb:
        step = np.zeros(cols, dtype=float)
        step[col] = eps
        forward = counted_residual(vector + step)
        body_index = col // STATE_DIM
        quat_row = body_index
        if col >= body_index * STATE_DIM + 3:
            jacobian[quat_row, col] = (forward[quat_row] - base[quat_row]) / eps
        for residual_row in col_to_rows.get(col, set()):
            jacobian[residual_row, col] = (forward[residual_row] - base[residual_row]) / eps

    return jacobian


def count_sparse_jacobian_evaluations(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
) -> int:
    """Expected residual_fn evaluations for :func:`sparse_numeric_jacobian`."""
    bodies_in_constraints: set[str] = set()
    for constraint in compiled:
        bodies_in_constraints.update(constraint.body_ids)
    return 1 + STATE_DIM * len(bodies_in_constraints)


def count_dense_jacobian_evaluations(vector: np.ndarray) -> int:
    return 1 + int(vector.size)


def structural_nnz(jacobian: np.ndarray, *, tol: float = 1e-12) -> int:
    return int(np.sum(np.abs(jacobian) > tol))


def _rotation_axes_from_null(null_vector: np.ndarray, *, threshold: float = 0.15) -> list[str]:
    quat = null_vector[3:7]
    norm = float(np.linalg.norm(quat))
    if norm <= threshold:
        return []
    axes: list[str] = []
    if abs(float(quat[0])) > threshold:
        axes.append("x")
    if abs(float(quat[1])) > threshold:
        axes.append("y")
    if abs(float(quat[2])) > threshold:
        axes.append("z")
    return axes


def summarize_dof(
    jacobian: np.ndarray,
    *,
    body_ids: tuple[str, ...],
    singular_threshold: float = 1e-4,
) -> dict[str, Any]:
    if jacobian.size == 0:
        return {"rank": 0, "dof_deficit": 0, "free": []}

    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    rank = int(np.sum(singular_values > singular_threshold))
    expected_columns = jacobian.shape[1]
    dof_deficit = max(0, expected_columns - rank)

    free: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    if dof_deficit > 0 and jacobian.shape[0] > 0:
        _, _, vh = np.linalg.svd(jacobian, full_matrices=True)
        null_vectors = vh[rank:].T
        for vector_index in range(null_vectors.shape[1]):
            null_vector = null_vectors[:, vector_index]
            for body_index, body_id in enumerate(body_ids):
                offset = body_index * STATE_DIM
                translation = null_vector[offset : offset + 3]
                trans_axes: list[str] = []
                if abs(float(translation[0])) > 0.35:
                    trans_axes.append("x")
                if abs(float(translation[1])) > 0.35:
                    trans_axes.append("y")
                if abs(float(translation[2])) > 0.35:
                    trans_axes.append("z")
                rot_axes = _rotation_axes_from_null(null_vector[offset : offset + STATE_DIM])
                if not trans_axes and not rot_axes:
                    continue
                key = (body_id, ",".join(trans_axes + rot_axes))
                if key in seen:
                    continue
                seen.add(key)
                free.append({"body": body_id, "trans": trans_axes, "rot": rot_axes})
                if len(free) >= 5:
                    break
            if len(free) >= 5:
                break

    return {
        "rank": rank,
        "dof_deficit": dof_deficit,
        "singular_min": float(singular_values[-1]) if singular_values.size else 0.0,
        "free": free[:5],
    }
