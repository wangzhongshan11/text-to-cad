"""P3c: layout ↔ relations conversion for debugging and Location-style workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .errors import ConstraintSchemaError


def _as_float_triplet(value: object, *, field: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ConstraintSchemaError(
            f"{field} must be [x, y, z], got {value!r}"
        )
    return (float(value[0]), float(value[1]), float(value[2]))


def _as_float_pair(value: object, *, field: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ConstraintSchemaError(
            f"{field} must be [u, v], got {value!r}"
        )
    return (float(value[0]), float(value[1]))


def layout_to_relations(
    layout: Mapping[str, Any],
    *,
    ground: str | None = None,
    default_parent: str | None = None,
    default_on: str | None = None,
    mode: str = "auto",
) -> list[dict[str, Any]]:
    """Turn a Location-style layout dict into recommended v2 ``relations`` entries.

    Supported ``layout`` shapes:

    * ``{"pelvis": [x, y, z], ...}`` with ``ground=...`` (world translation).
    * ``{"ground": "base", "placements": {"b1": {"on": "base.+z", "at": [u, v]}}}``.
    * Per-body objects with ``type`` / ``on`` / ``at`` / ``parent`` / ``local``.
    """
    if not layout:
        return []

    parent = default_parent or ground
    support_on = default_on or (f"{parent}.+z" if parent else None)

    items: dict[str, Any]
    if "placements" in layout and isinstance(layout.get("placements"), dict):
        ground = str(layout.get("ground") or ground or "")
        if not ground:
            raise ConstraintSchemaError(
                "layout.placements requires 'ground' in layout or ground= argument"
            )
        parent = default_parent or ground
        support_on = default_on or f"{parent}.+z"
        items = layout["placements"]
    else:
        if ground is None:
            raise ConstraintSchemaError(
                "layout_to_relations: provide ground= for bare body→position maps"
            )
        items = dict(layout)

    relations: list[dict[str, Any]] = []
    for index, (body_id, raw) in enumerate(items.items(), start=1):
        if body_id in {"ground", "placements"}:
            continue
        if body_id == ground:
            continue

        if isinstance(raw, dict):
            relation = dict(raw)
            relation.setdefault("id", f"r{index}")
            relation.setdefault("child", body_id)
            relations.append(relation)
            continue

        if mode not in {"auto", "flat_on", "fix_to"}:
            raise ConstraintSchemaError(
                f"mode must be auto|flat_on|fix_to, got {mode!r}"
            )

        use_flat_on = mode == "flat_on"
        if mode == "auto":
            if isinstance(raw, (list, tuple)) and len(raw) == 2:
                use_flat_on = True
            else:
                use_flat_on = False

        if use_flat_on:
            if isinstance(raw, (list, tuple)) and len(raw) == 2:
                at = _as_float_pair(raw, field=f"layout[{body_id!r}]")
            elif isinstance(raw, (list, tuple)) and len(raw) == 3:
                at = (float(raw[0]), float(raw[1]))
            else:
                raise ConstraintSchemaError(
                    f"layout[{body_id!r}]: flat_on needs [u, v] or [x, y, z]"
                )
            if not support_on:
                raise ConstraintSchemaError("default_on or ground required for flat_on")
            relations.append(
                {
                    "id": f"r{index}",
                    "type": "flat_on",
                    "child": body_id,
                    "on": support_on,
                    "at": [at[0], at[1]],
                }
            )
        else:
            local = _as_float_triplet(raw, field=f"layout[{body_id!r}]")
            if parent is None:
                raise ConstraintSchemaError(
                    "default_parent or ground required for fix_to relations"
                )
            relations.append(
                {
                    "id": f"r{index}",
                    "type": "fix_to",
                    "child": body_id,
                    "parent": parent,
                    "local": [local[0], local[1], local[2]],
                }
            )

    return relations


def relations_to_layout(
    spec: dict[str, Any],
    *,
    transforms: Mapping[str, Any] | None = None,
    spec_path: str | Path | None = None,
    include_layout_only: bool = True,
) -> dict[str, list[float]]:
    """Export world-frame ``place`` positions from a spec (and optional solve transforms)."""
    from .dsl import detect_spec_version, extract_layout_places

    ground = spec.get("ground")
    if not isinstance(ground, str):
        raise ConstraintSchemaError("spec.ground must be a string")

    layout: dict[str, list[float]] = {}

    if detect_spec_version(spec) == 2 and include_layout_only:
        layout_only_ids, layout_poses = extract_layout_places(spec)
        for body_id in layout_only_ids:
            pose = layout_poses.get(body_id)
            if pose is not None:
                layout[body_id] = [pose.translation[0], pose.translation[1], pose.translation[2]]

    matrix_map = transforms
    if matrix_map is None:
        from .solver import solve_assembly

        path = Path(spec_path).resolve() if spec_path is not None else None
        result = solve_assembly(spec, spec_path=str(path) if path else None)
        matrix_map = result.get("transforms") or {}

    if not isinstance(matrix_map, Mapping):
        raise ConstraintSchemaError("transforms must be a mapping of body_id → 4×4 matrix")

    for body_id, matrix in matrix_map.items():
        if body_id == ground:
            continue
        if not isinstance(matrix, (list, tuple)) or len(matrix) != 16:
            continue
        layout[str(body_id)] = [
            float(matrix[3]),
            float(matrix[7]),
            float(matrix[11]),
        ]

    return layout
