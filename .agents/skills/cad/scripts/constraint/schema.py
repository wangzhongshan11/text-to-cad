from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ConstraintSchemaError
from .limits import check_assembly_scale, resolve_limits
from .primitives import build_primitive_body, list_feature_ids


ALLOWED_CONSTRAINT_TYPES = frozenset(
    {
        "fix",
        "point_coincident",
        "plane_coincident",
        "axis_coaxial",
        "axis_parallel",
        "plane_distance",
        "point_plane_offset",
        "contact",
        "hinge",
    }
)


def _require_mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConstraintSchemaError(f"{field} must be an object")
    return value


def validate_assembly_spec(
    spec: dict[str, Any],
    *,
    spec_path: Path | str | None = None,
) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ConstraintSchemaError("assembly spec must be an object")

    # v2 -> v1 transparently. dsl.compile_v2_to_v1 is a pass-through for v1
    # specs, so existing callers see no behaviour change. Late import avoids a
    # cycle (dsl -> macros only; macros -> errors).
    from .dsl import (
        compile_v2_to_v1,
        detect_spec_version,
        extract_layout_places,
        extract_rotation_modes,
        extract_yaw_axes,
        is_verify_only_spec,
        merged_dof_policy,
    )
    from .subgraph import SubGraphBundle, merge_child_catalogs, prepare_spec_with_subgraphs

    path = Path(spec_path).resolve() if spec_path is not None else None

    spec_version = detect_spec_version(spec)
    rotation_modes = extract_rotation_modes(spec)
    yaw_axes = extract_yaw_axes(spec) if spec_version == 2 else {}
    dof_policy = merged_dof_policy(spec) if spec_version == 2 else None
    layout_only_ids, layout_poses = (
        extract_layout_places(spec) if spec_version == 2 else (frozenset(), {})
    )
    verify_only = is_verify_only_spec(spec) if spec_version == 2 else False

    sub_bundle: SubGraphBundle | None = None
    if spec_version == 2:
        spec, sub_bundle = prepare_spec_with_subgraphs(spec, path)

    spec = compile_v2_to_v1(spec)

    ground = spec.get("ground")
    if not isinstance(ground, str) or not ground.strip():
        raise ConstraintSchemaError("ground must be a non-empty string")
    ground = ground.strip()

    bodies = _require_mapping(spec.get("bodies"), field="bodies")
    if not bodies:
        raise ConstraintSchemaError("bodies must be non-empty")

    catalog: dict[str, Any] = {}
    for body_id, body_spec in bodies.items():
        if not isinstance(body_id, str) or not body_id.strip():
            raise ConstraintSchemaError("body ids must be non-empty strings")
        body_mapping = _require_mapping(body_spec, field=f"bodies[{body_id}]")
        primitive = body_mapping.get("primitive")
        if not isinstance(primitive, str):
            raise ConstraintSchemaError(f"bodies[{body_id}].primitive is required")
        try:
            catalog[body_id] = build_primitive_body(primitive, body_mapping)
        except ValueError as exc:
            raise ConstraintSchemaError(str(exc)) from exc

    if ground not in catalog:
        raise ConstraintSchemaError(f"ground body {ground!r} is not defined in bodies")

    raw_constraints = spec.get("constraints")
    if not isinstance(raw_constraints, list) or not raw_constraints:
        raise ConstraintSchemaError("constraints must be a non-empty array")

    normalized: list[dict[str, Any]] = []
    for index, raw_constraint in enumerate(raw_constraints, start=1):
        constraint = _require_mapping(raw_constraint, field=f"constraints[{index}]")
        constraint_type = constraint.get("type")
        if not isinstance(constraint_type, str):
            raise ConstraintSchemaError(f"constraints[{index}].type is required")
        if constraint_type not in ALLOWED_CONSTRAINT_TYPES:
            raise ConstraintSchemaError(f"unsupported constraint type: {constraint_type!r}")
        normalized.append({**constraint, "id": constraint.get("id", f"c{index}")})

    initial_guess = spec.get("initial_guess")
    if initial_guess is not None and not isinstance(initial_guess, dict):
        raise ConstraintSchemaError("initial_guess must be an object")

    limits = resolve_limits(spec)
    child_catalogs: dict[str, dict[str, Any]] = {}
    if sub_bundle is not None:
        for instance in sub_bundle.instances:
            if instance.sub_spec_path not in child_catalogs:
                child_validated = validate_assembly_spec(
                    instance.child_spec,
                    spec_path=instance.sub_spec_path,
                )
                child_catalogs[instance.sub_spec_path] = child_validated["catalog"]
                rotation_modes.update(child_validated.get("rotation_modes", {}))
        catalog = merge_child_catalogs(catalog, sub_bundle, child_catalogs=child_catalogs)

    scale_warnings = check_assembly_scale(
        body_count=len(catalog),
        constraint_count=len(normalized),
        limits=limits,
    )

    return {
        "ground": ground,
        "bodies": bodies,
        "catalog": catalog,
        "constraints": normalized,
        "initial_guess": initial_guess or {},
        "limits": limits,
        "scale_warnings": scale_warnings,
        "feature_index": {
            body_id: list_feature_ids(catalog[body_id]) for body_id in catalog
        },
        "rotation_modes": rotation_modes,
        "yaw_axes": yaw_axes,
        "spec_version": spec_version,
        "dof_policy": dof_policy,
        "layout_only_ids": layout_only_ids,
        "layout_poses": layout_poses,
        "verify_only": verify_only,
        "sub_bundle": sub_bundle,
        "spec_path": path,
    }
