"""P1: v2 spec compiler.

This module performs three jobs:

1. ``detect_spec_version(spec)`` distinguishes v1 (legacy ``constraints`` only)
   from v2 (``relations`` / ``dof_policy`` / body modes / ``sub_spec`` etc.).
   Per ``constraint-assembly-optimize1.md §6.6`` a spec carrying any v2-only
   field but lacking explicit ``"version": 2`` is rejected with a schema error.
2. ``compile_v2_to_v1(spec)`` validates v2-only mutex rules, applies dof_policy
   defaults, expands every ``relations[]`` entry into v1 basic constraints via
   :mod:`.macros`, and returns an equivalent v1 spec ready to be passed
   straight to :func:`constraint.schema.validate_assembly_spec`.
3. For v1 inputs both functions are pass-throughs, so introducing v2 has zero
   observable effect on existing v1 callers (see §14.2).

Layout ↔ relation helpers live in :mod:`.layout_tools` (P3c).
"""

from __future__ import annotations

from typing import Any

from .errors import ConstraintSchemaError
from .macros import expand_relation
from .state import BodyPose


V2_TOP_FIELDS: frozenset[str] = frozenset(
    {"relations", "dof_policy", "interface_spec"}
)
V2_BODY_FIELDS: frozenset[str] = frozenset(
    {"rotation_mode", "place", "layout_only", "sub_spec", "anchor_body"}
)

DEFAULT_DOF_POLICY: dict[str, Any] = {
    "default_box_on_plane": "fixed_orthogonal",
    "mating_policy": "strict",
    "gauge_policy": "require",
    "strict_ok": False,
    "overconstrained_threshold": 1e-4,
    "free_subcluster_min_bodies": 2,
}


def extract_layout_places(
    spec: dict[str, Any],
) -> tuple[frozenset[str], dict[str, BodyPose]]:
    """Read ``layout_only`` bodies and their fixed ``place`` poses from a v2 spec."""
    layout_only: set[str] = set()
    places: dict[str, BodyPose] = {}
    bodies = spec.get("bodies") or {}
    for body_id, body in bodies.items():
        if not isinstance(body, dict) or not body.get("layout_only"):
            continue
        layout_only.add(str(body_id))
        place = body.get("place")
        if isinstance(place, (list, tuple)) and len(place) == 3:
            places[str(body_id)] = BodyPose(
                (float(place[0]), float(place[1]), float(place[2])),
                (0.0, 0.0, 0.0, 1.0),
            )
    return frozenset(layout_only), places


def is_verify_only_spec(spec: dict[str, Any]) -> bool:
    """True when all non-ground bodies are ``layout_only`` with ``place`` (§13.2)."""
    if detect_spec_version(spec) != 2:
        return False
    dof = merged_dof_policy(spec) or {}
    if str(dof.get("mating_policy")) != "permissive":
        return False
    ground = spec.get("ground")
    bodies = spec.get("bodies") or {}
    for body_id, body in bodies.items():
        if body_id == ground:
            continue
        if not isinstance(body, dict):
            return False
        if not body.get("layout_only") or "place" not in body:
            return False
    return len(bodies) > 1


def extract_yaw_axes(spec: dict[str, Any]) -> dict[str, str]:
    """Read per-body ``yaw_axis`` (default ``+z``) for ``yaw_only`` bodies."""
    bodies = spec.get("bodies") or {}
    axes: dict[str, str] = {}
    for body_id, body in bodies.items():
        if isinstance(body, dict) and "yaw_axis" in body:
            axes[str(body_id)] = str(body["yaw_axis"])
    return axes


def extract_rotation_modes(spec: dict[str, Any]) -> dict[str, str]:
    """Read per-body ``rotation_mode`` before v2 fields are stripped at compile.

    v2 defaults to ``axis_aligned``; v1 defaults to ``free`` (full numerical
    solve) so existing specs keep legacy behaviour.
    """
    version = detect_spec_version(spec)
    default_mode = "axis_aligned" if version == 2 else "free"
    bodies = spec.get("bodies") or {}
    modes: dict[str, str] = {}
    for body_id, body in bodies.items():
        if isinstance(body, dict):
            modes[str(body_id)] = str(body.get("rotation_mode", default_mode))
        else:
            modes[str(body_id)] = default_mode
    return modes


def detect_spec_version(spec: dict[str, Any]) -> int:
    """Return 1 or 2.

    Reject specs that include v2-only fields but omit explicit
    ``"version": 2``; this prevents silent v1 misinterpretation of newer
    schemas (see optimize1.md §6.6 trigger rules).
    """
    if not isinstance(spec, dict):
        raise ConstraintSchemaError("assembly spec must be an object")

    explicit = spec.get("version")

    has_v2_top = any(field in spec for field in V2_TOP_FIELDS)
    has_v2_body = False
    bodies = spec.get("bodies")
    if isinstance(bodies, dict):
        for body in bodies.values():
            if isinstance(body, dict) and any(
                field in body for field in V2_BODY_FIELDS
            ):
                has_v2_body = True
                break
    has_v2_any = has_v2_top or has_v2_body

    if explicit == 2:
        return 2
    if explicit is None or explicit == 1:
        if has_v2_any:
            raise ConstraintSchemaError(
                "spec contains v2-only fields (relations / dof_policy / "
                "interface_spec / bodies[*].rotation_mode / place / "
                "layout_only / sub_spec / anchor_body) but lacks "
                "'version': 2; set top-level 'version': 2 explicitly"
            )
        return 1

    raise ConstraintSchemaError(
        f"unsupported spec version: {explicit!r} (expected 1 or 2)"
    )


def _validate_v2_mutex(spec: dict[str, Any]) -> None:
    """Enforce v2 mutual-exclusion rules from optimize1.md Appendix A."""
    bodies = spec.get("bodies", {}) or {}
    relations = spec.get("relations", []) or []
    constraints = spec.get("constraints", []) or []

    bodies_in_relations: set[str] = set()
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        child = rel.get("child")
        if isinstance(child, str):
            bodies_in_relations.add(child)
        on = rel.get("on")
        if isinstance(on, str) and "." in on:
            bodies_in_relations.add(on.split(".", 1)[0])
        for key in ("a", "b", "parent"):
            value = rel.get(key)
            if not isinstance(value, str):
                continue
            if "." in value:
                bodies_in_relations.add(value.split(".", 1)[0])
            else:
                bodies_in_relations.add(value)

    for body_id, body in bodies.items():
        if not isinstance(body, dict):
            continue
        has_primitive = "primitive" in body
        has_sub_spec = "sub_spec" in body
        has_place = "place" in body
        has_layout_only = bool(body.get("layout_only", False))
        has_rotation_mode = "rotation_mode" in body
        has_anchor_body = "anchor_body" in body

        if has_sub_spec and has_primitive:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'sub_spec' and 'primitive' are mutually exclusive"
            )
        if has_sub_spec and has_place:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'sub_spec' cannot coexist with 'place'"
            )
        if has_sub_spec and has_layout_only:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'sub_spec' cannot coexist with 'layout_only'"
            )
        if has_sub_spec and has_rotation_mode:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'sub_spec' cannot coexist with 'rotation_mode' "
                f"(rotation is controlled by the sub spec)"
            )
        if has_anchor_body and not has_sub_spec:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'anchor_body' requires 'sub_spec'"
            )
        if has_layout_only and not has_place:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'layout_only: true' requires 'place: [x, y, z]'"
            )
        if has_place and body_id in bodies_in_relations:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: 'place' conflicts with the same body appearing "
                f"in 'relations'"
            )

    # constraints id namespace isolation: relation expansions own 'r*' ids
    for index, constraint in enumerate(constraints, start=1):
        if not isinstance(constraint, dict):
            continue
        cid = constraint.get("id")
        if isinstance(cid, str) and cid.startswith("r"):
            raise ConstraintSchemaError(
                f"constraints[{index}].id={cid!r} must not start with 'r' "
                f"(reserved for relation expansion); rename to e.g. 'c{index}'"
            )


def _merged_dof_policy(spec: dict[str, Any]) -> dict[str, Any]:
    user = spec.get("dof_policy") or {}
    if not isinstance(user, dict):
        raise ConstraintSchemaError("dof_policy must be an object")
    merged = dict(DEFAULT_DOF_POLICY)
    merged.update(user)
    return merged


def merged_dof_policy(spec: dict[str, Any]) -> dict[str, Any] | None:
    """Return merged dof_policy for v2 specs, else ``None``."""
    if detect_spec_version(spec) != 2:
        return None
    return _merged_dof_policy(spec)


def _reject_unimplemented_v2_features(spec: dict[str, Any]) -> None:
    """Raise a clear error for v2 fields not yet implemented in R1."""
    bodies = spec.get("bodies", {}) or {}
    for body_id, body in bodies.items():
        if not isinstance(body, dict):
            continue
        rotation_mode = body.get("rotation_mode", "axis_aligned")
        if rotation_mode not in {"axis_aligned", "yaw_only", "free"}:
            raise ConstraintSchemaError(
                f"bodies[{body_id}]: rotation_mode={rotation_mode!r} invalid "
                f"(expected axis_aligned | yaw_only | free)"
            )
def compile_v2_to_v1(spec: dict[str, Any]) -> dict[str, Any]:
    """Translate a v2 spec into an equivalent v1 spec.

    For v1 specs (no v2 fields, no explicit ``version``) the input is returned
    unchanged. For v2 specs the function:

    * validates mutex constraints (§ Appendix A),
    * rejects unimplemented v2 features with clear messages,
    * expands ``relations[]`` into basic constraints (each tagged with
      ``triggered_by``),
    * strips v2-only body fields so the downstream v1 schema validator does
      not see unknown keys,
    * preserves user-authored ``constraints[]`` and concatenates them after
      the macro-expanded constraints.
    """
    version = detect_spec_version(spec)
    if version == 1:
        return spec

    _validate_v2_mutex(spec)
    _reject_unimplemented_v2_features(spec)

    dof_policy = _merged_dof_policy(spec)
    bodies = spec.get("bodies", {}) or {}
    relations = spec.get("relations", []) or []
    user_constraints = list(spec.get("constraints", []) or [])

    expanded: list[dict[str, Any]] = []
    for idx, rel in enumerate(relations, start=1):
        if not isinstance(rel, dict):
            raise ConstraintSchemaError(
                f"relations[{idx - 1}] must be an object, got {type(rel).__name__}"
            )
        expanded.extend(expand_relation(rel, bodies, dof_policy, idx))

    cleaned_bodies: dict[str, Any] = {}
    for body_id, body in bodies.items():
        if isinstance(body, dict):
            cleaned_bodies[body_id] = {
                k: v for k, v in body.items() if k not in V2_BODY_FIELDS
            }
        else:
            cleaned_bodies[body_id] = body

    v1_spec: dict[str, Any] = {
        "ground": spec.get("ground"),
        "bodies": cleaned_bodies,
        "constraints": expanded + user_constraints,
    }
    if "limits" in spec:
        v1_spec["limits"] = spec["limits"]
    if "initial_guess" in spec:
        v1_spec["initial_guess"] = spec["initial_guess"]
    return v1_spec


def layout_to_relations(layout, **kwargs):
    """Re-export :func:`constraint.layout_tools.layout_to_relations`."""
    from .layout_tools import layout_to_relations as _fn

    return _fn(layout, **kwargs)


def relations_to_layout(spec, **kwargs):
    """Re-export :func:`constraint.layout_tools.relations_to_layout`."""
    from .layout_tools import relations_to_layout as _fn

    return _fn(spec, **kwargs)
