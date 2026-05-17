from __future__ import annotations

from typing import Any

import numpy as np

from .state import STATE_DIM


def numeric_jacobian(
    residual_fn,
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


def _rotation_axes_from_null(null_vector: np.ndarray, *, threshold: float = 0.15) -> list[str]:
    quat = null_vector[3:7]
    norm = float(np.linalg.norm(quat))
    if norm <= threshold:
        return []
    # Small quaternion increment: dominant component suggests spin axis.
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
