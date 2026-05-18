"""P1: geometric/strategy macro expansion for v2 constraint specs.

This module expands a single v2 ``relation`` into one or more v1 basic
constraints. Each emitted constraint carries a ``triggered_by`` field so the
relation that produced it can be recovered from the dry-run output or from
solver diagnostics.

Identifier convention (see optimize1.md §7.4):
    - The relation's ``id`` (or auto-generated ``r{i}``) is used as prefix.
    - Each expanded constraint id is ``{relation_id}_{slot}`` where slot is one
      of ``pc`` / ``oux`` / ``ouy`` / ``off`` / ``par_x`` / ``par_y`` /
      ``par_z``.
    - The ``triggered_by`` value is ``"{relation_id}:{relation_type}[:{sub_role}]"``.
"""

from __future__ import annotations

from typing import Any

from .errors import ConstraintSchemaError


SUPPORTED_RELATION_TYPES: frozenset[str] = frozenset(
    {
        "flat_on",
        "coax",
        "align",
        "fix_to",
        "hinge",
        "slider",
        "lock_orthogonal_to",
        "yaw_free",
    }
)


_AXIS_CHAR_TO_INDEX = {"x": 0, "y": 1, "z": 2}
_VALID_FACES = frozenset({"+x", "-x", "+y", "-y", "+z", "-z"})

_BOX_PARENT_FACE_ALIASES = {
    "plane_px": "+x", "plane_nx": "-x",
    "plane_py": "+y", "plane_ny": "-y",
    "plane_pz": "+z", "plane_nz": "-z",
    "+x_plane": "+x", "-x_plane": "-x",
    "+y_plane": "+y", "-y_plane": "-y",
    "+z_plane": "+z", "-z_plane": "-z",
}


def _axis_of(face: str) -> str:
    return face[1]


def _sign_of(face: str) -> int:
    """Return the sign of the normal-offset for a ``flat_on`` face.

    See ``constraint-assembly-optimize1.md §C.3``: if the child's negative face
    (e.g. ``-z``) is mated to the parent plane, the child centre lies on the
    +normal side of that plane, so the signed distance is positive and the
    ``point_plane_offset`` must use ``+half``.
    """
    return +1 if face.startswith("-") else -1


def _opposite_face(face: str) -> str:
    return ("-" if face.startswith("+") else "+") + face[1]


def _parent_face_literal(on_str: str) -> str | None:
    """Return the canonical ±x/±y/±z parent face token if on_str references one.

    Recognises bare faces (``parent.+z``) and the box plane aliases
    (``parent.plane_pz``, ``parent.+z_plane``) emitted by
    :mod:`constraint.primitives`. Returns ``None`` for any other feature.
    """
    if "." not in on_str:
        return None
    feature = on_str.split(".", 1)[1]
    if feature in _VALID_FACES:
        return feature
    return _BOX_PARENT_FACE_ALIASES.get(feature)


def _child_half_box(size: list[float], face: str) -> float:
    axis = _axis_of(face)
    return float(size[_AXIS_CHAR_TO_INDEX[axis]]) / 2.0


def expand_flat_on(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    """Expand a single ``flat_on`` relation into v1 basic constraints.

    The expansion always emits ``plane_coincident`` + three
    ``point_plane_offset`` (in_plane x, in_plane y, normal offset). When the
    child runs in ``rotation_mode == "axis_aligned"`` and the policy
    ``default_box_on_plane`` is ``"fixed_orthogonal"`` (both default in v2),
    three ``axis_parallel`` constraints are appended; these are part of the
    macro definition (see §7.2.1) and are not counted as ``assumed_locks``.
    """
    rid = str(rel.get("id") or f"r{rel_index}")

    child_id = rel.get("child")
    on_str = rel.get("on")
    at = rel.get("at")
    if not isinstance(child_id, str) or not child_id.strip():
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: 'child' must be a non-empty body id"
        )
    if not isinstance(on_str, str) or "." not in on_str:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: 'on' must be '<parent>.<plane_feature>'"
        )
    if not isinstance(at, (list, tuple)) or len(at) != 2:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: 'at' must be [u, v]"
        )

    gap = float(rel.get("gap", 0.0))

    parent_id = on_str.split(".", 1)[0]
    parent_face = _parent_face_literal(on_str)

    # face defaulting: if the parent feature is a literal box face we can
    # auto-pick the opposed child face (the only physically valid choice
    # under axis_aligned). Otherwise fall back to "-z" to preserve the most
    # common authoring convention.
    explicit_face = "face" in rel
    if explicit_face:
        face = str(rel["face"])
    else:
        face = _opposite_face(parent_face) if parent_face is not None else "-z"
    if face not in _VALID_FACES:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: invalid face {face!r}, must be one of "
            f"{sorted(_VALID_FACES)}"
        )
    if child_id not in bodies_spec:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: child {child_id!r} not found in bodies"
        )
    if parent_id not in bodies_spec:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: parent {parent_id!r} (from 'on') not found in bodies"
        )

    child = bodies_spec[child_id] or {}
    parent = bodies_spec[parent_id] or {}
    child_primitive = str(child.get("primitive", ""))
    parent_primitive = str(parent.get("primitive", ""))

    # box-box only for full axis lock; cylinder/sphere matrix deferred to P2e.
    if parent_primitive == "sphere":
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: parent {parent_id!r} primitive='sphere' is "
            f"unsupported (no orientable face)"
        )
    if parent_primitive != "box":
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: parent primitive={parent_primitive!r} not yet "
            f"supported (only 'box' in P1)"
        )
    if child_primitive != "box":
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: child primitive={child_primitive!r} not yet "
            f"supported (only 'box' in P1)"
        )

    size = child.get("size")
    if not isinstance(size, (list, tuple)) or len(size) != 3:
        raise ConstraintSchemaError(
            f"flat_on[{rid}]: child {child_id!r} 'size' must be [lx, ly, lz]"
        )
    child_half = _child_half_box(list(size), face)
    offset_value = float(_sign_of(face)) * (child_half + gap)

    rotation_mode = str(child.get("rotation_mode", "axis_aligned"))

    # Under axis_aligned the child cannot rotate. Two consequences:
    #
    # 1. We need the parent feature to be a literal box face so we can read
    #    its world normal symbolically.
    # 2. The child face must point along the same axis but with the opposite
    #    sign (so ``opposed=True`` in the emitted plane_coincident is
    #    geometrically feasible).
    #
    # Mating to non-axis-aligned parent planes or to lateral child faces both
    # require yaw_only / free rotation modes and are deferred to P0b/P2e.
    if rotation_mode == "axis_aligned":
        if parent_face is None:
            raise ConstraintSchemaError(
                f"flat_on[{rid}]: on={on_str!r} parent feature must be a "
                f"literal box face such as '+z' under "
                f"rotation_mode='axis_aligned' (planned P0b/P2e for "
                f"non-axis-aligned parent faces)"
            )
        if _axis_of(face) != _axis_of(parent_face):
            raise ConstraintSchemaError(
                f"flat_on[{rid}]: face={face!r} axis is incompatible with "
                f"parent face {parent_face!r} under "
                f"rotation_mode='axis_aligned' (axes must match; lateral "
                f"mating planned for P0b/P2e)"
            )
        if _sign_of(face) == _sign_of(parent_face):
            raise ConstraintSchemaError(
                f"flat_on[{rid}]: face={face!r} must be opposite to parent "
                f"face {parent_face!r} under rotation_mode='axis_aligned' "
                f"(opposed mating requires inverted normals; "
                f"use '{_opposite_face(parent_face)}' or omit the field)"
            )

    u = float(at[0])
    v = float(at[1])

    expanded: list[dict[str, Any]] = [
        {
            "id": f"{rid}_pc",
            "type": "plane_coincident",
            "a": f"{child_id}.{face}",
            "b": on_str,
            "opposed": True,
            "triggered_by": f"{rid}:flat_on:contact",
        },
        {
            "id": f"{rid}_oux",
            "type": "point_plane_offset",
            "point": f"{child_id}.center",
            "plane": on_str,
            "in_plane": "x",
            "value": u,
            "triggered_by": f"{rid}:flat_on:tangent_u",
        },
        {
            "id": f"{rid}_ouy",
            "type": "point_plane_offset",
            "point": f"{child_id}.center",
            "plane": on_str,
            "in_plane": "y",
            "value": v,
            "triggered_by": f"{rid}:flat_on:tangent_v",
        },
        {
            "id": f"{rid}_off",
            "type": "point_plane_offset",
            "point": f"{child_id}.center",
            "plane": on_str,
            "offset": offset_value,
            "triggered_by": f"{rid}:flat_on:normal",
        },
    ]

    box_on_plane = str(dof_policy.get("default_box_on_plane", "fixed_orthogonal"))
    if rotation_mode == "axis_aligned" and box_on_plane == "fixed_orthogonal":
        for axis_name in ("axis_x", "axis_y", "axis_z"):
            expanded.append(
                {
                    "id": f"{rid}_par_{axis_name[-1]}",
                    "type": "axis_parallel",
                    "a": f"{child_id}.{axis_name}",
                    "b": f"{parent_id}.{axis_name}",
                    "triggered_by": f"{rid}:flat_on:lock_orthogonal",
                }
            )

    return expanded


def _relation_id(rel: dict[str, Any], rel_index: int) -> str:
    return str(rel.get("id") or f"r{rel_index}")


def _body_id_from_ref(ref: str) -> str:
    return ref.split(".", 1)[0] if "." in ref else ref


def _plane_for_axis_offset(body_id: str, axis_ref: str, bodies_spec: dict[str, dict[str, Any]]) -> str:
    """Pick a plane feature whose normal aligns with the given axis ref."""
    feature = axis_ref.split(".", 1)[1] if "." in axis_ref else "axis_z"
    body = bodies_spec.get(body_id) or {}
    primitive = str(body.get("primitive", "box"))
    if feature == "axis_z":
        return f"{body_id}.top_plane" if primitive == "cylinder" else f"{body_id}.plane_pz"
    if feature == "axis_y":
        return f"{body_id}.plane_py"
    if feature == "axis_x":
        return f"{body_id}.plane_px"
    return f"{body_id}.plane_pz"


def _yaw_axis_to_feature(yaw_axis: str) -> str:
    axis = str(yaw_axis).lstrip("+-")
    if axis not in {"x", "y", "z"}:
        raise ConstraintSchemaError(f"invalid yaw_axis {yaw_axis!r}, expected +x|-x|+y|-y|+z|-z")
    return f"axis_{axis}"


def expand_coax(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    a_ref = rel.get("a")
    b_ref = rel.get("b")
    if not isinstance(a_ref, str) or not isinstance(b_ref, str):
        raise ConstraintSchemaError(f"coax[{rid}]: 'a' and 'b' axis refs are required")

    expanded: list[dict[str, Any]] = [
        {
            "id": f"{rid}_pc_ax",
            "type": "axis_coaxial",
            "a": a_ref,
            "b": b_ref,
            "triggered_by": f"{rid}:coax:axis",
        }
    ]
    if "offset" in rel:
        a_body = _body_id_from_ref(a_ref)
        b_body = _body_id_from_ref(b_ref)
        plane = _plane_for_axis_offset(b_body, b_ref, bodies_spec)
        a_origin = f"{a_body}.origin" if "." in a_ref else f"{a_body}.origin"
        expanded.append(
            {
                "id": f"{rid}_off",
                "type": "point_plane_offset",
                "point": a_origin,
                "plane": plane,
                "offset": float(rel["offset"]),
                "triggered_by": f"{rid}:coax:offset",
            }
        )
    return expanded


def expand_align(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    a_ref = rel.get("a")
    b_ref = rel.get("b")
    if not isinstance(a_ref, str) or not isinstance(b_ref, str):
        raise ConstraintSchemaError(f"align[{rid}]: 'a' and 'b' axis refs are required")
    return [
        {
            "id": f"{rid}_par",
            "type": "axis_parallel",
            "a": a_ref,
            "b": b_ref,
            "opposed": bool(rel.get("opposed", False)),
            "triggered_by": f"{rid}:align",
        }
    ]


def expand_fix_to(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    child_id = rel.get("child")
    parent_id = rel.get("parent")
    if not isinstance(child_id, str) or not isinstance(parent_id, str):
        raise ConstraintSchemaError(f"fix_to[{rid}]: 'child' and 'parent' are required")
    parent = bodies_spec.get(parent_id) or {}
    if str(parent.get("primitive", "")) != "box":
        raise ConstraintSchemaError(
            f"fix_to[{rid}]: parent {parent_id!r} must be primitive='box'"
        )
    local = rel.get("local", [0.0, 0.0, 0.0])
    if not isinstance(local, (list, tuple)) or len(local) != 3:
        raise ConstraintSchemaError(f"fix_to[{rid}]: 'local' must be [x, y, z]")

    expanded: list[dict[str, Any]] = []
    for axis_name, plane_suffix, value in (
        ("x", "plane_px", float(local[0])),
        ("y", "plane_py", float(local[1])),
        ("z", "plane_pz", float(local[2])),
    ):
        expanded.append(
            {
                "id": f"{rid}_off_{axis_name}",
                "type": "point_plane_offset",
                "point": f"{child_id}.center",
                "plane": f"{parent_id}.{plane_suffix}",
                "offset": value,
                "triggered_by": f"{rid}:fix_to:offset_{axis_name}",
            }
        )
    for axis_name in ("axis_x", "axis_y", "axis_z"):
        expanded.append(
            {
                "id": f"{rid}_par_{axis_name[-1]}",
                "type": "axis_parallel",
                "a": f"{child_id}.{axis_name}",
                "b": f"{parent_id}.{axis_name}",
                "triggered_by": f"{rid}:fix_to:lock",
            }
        )
    return expanded


def expand_hinge(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    a_ref = rel.get("a")
    b_ref = rel.get("b")
    if not isinstance(a_ref, str) or not isinstance(b_ref, str):
        raise ConstraintSchemaError(f"hinge[{rid}]: 'a' and 'b' axis refs are required")
    expanded: list[dict[str, Any]] = [
        {
            "id": f"{rid}_pc_ax",
            "type": "axis_coaxial",
            "a": a_ref,
            "b": b_ref,
            "triggered_by": f"{rid}:hinge:axis",
        },
        {
            "id": f"{rid}_pt",
            "type": "point_coincident",
            "a": rel.get("point_a", a_ref),
            "b": rel.get("point_b", b_ref),
            "triggered_by": f"{rid}:hinge:pivot",
        },
    ]
    return expanded


def expand_slider(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    a_ref = rel.get("a")
    b_ref = rel.get("b")
    if not isinstance(a_ref, str) or not isinstance(b_ref, str):
        raise ConstraintSchemaError(f"slider[{rid}]: 'a' and 'b' axis refs are required")
    expanded: list[dict[str, Any]] = [
        {
            "id": f"{rid}_pc_ax",
            "type": "axis_coaxial",
            "a": a_ref,
            "b": b_ref,
            "triggered_by": f"{rid}:slider:axis",
        }
    ]
    if "displacement" in rel:
        a_body = _body_id_from_ref(a_ref)
        b_body = _body_id_from_ref(b_ref)
        plane = _plane_for_axis_offset(b_body, b_ref, bodies_spec)
        expanded.append(
            {
                "id": f"{rid}_off",
                "type": "point_plane_offset",
                "point": f"{a_body}.origin",
                "plane": plane,
                "offset": float(rel["displacement"]),
                "triggered_by": f"{rid}:slider:displacement",
            }
        )
    return expanded


def expand_lock_orthogonal_to(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    child_id = rel.get("child")
    target_id = rel.get("target")
    if not isinstance(child_id, str) or not isinstance(target_id, str):
        raise ConstraintSchemaError(
            f"lock_orthogonal_to[{rid}]: 'child' and 'target' are required"
        )
    expanded: list[dict[str, Any]] = []
    for axis_name in ("axis_x", "axis_y", "axis_z"):
        expanded.append(
            {
                "id": f"{rid}_par_{axis_name[-1]}",
                "type": "axis_parallel",
                "a": f"{child_id}.{axis_name}",
                "b": f"{target_id}.{axis_name}",
                "triggered_by": f"{rid}:lock_orthogonal_to",
            }
        )
    return expanded


def expand_yaw_free(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    rid = _relation_id(rel, rel_index)
    child_id = rel.get("child")
    target_id = rel.get("target")
    yaw_axis = rel.get("yaw_axis", "+z")
    if not isinstance(child_id, str):
        raise ConstraintSchemaError(f"yaw_free[{rid}]: 'child' is required")
    if not isinstance(target_id, str):
        raise ConstraintSchemaError(f"yaw_free[{rid}]: 'target' is required")
    yaw_feature = _yaw_axis_to_feature(str(yaw_axis))
    expanded: list[dict[str, Any]] = []
    for axis_name in ("axis_x", "axis_y", "axis_z"):
        if axis_name == yaw_feature:
            continue
        expanded.append(
            {
                "id": f"{rid}_par_{axis_name[-1]}",
                "type": "axis_parallel",
                "a": f"{child_id}.{axis_name}",
                "b": f"{target_id}.{axis_name}",
                "triggered_by": f"{rid}:yaw_free",
            }
        )
    return expanded


_EXPANDERS = {
    "flat_on": expand_flat_on,
    "coax": expand_coax,
    "align": expand_align,
    "fix_to": expand_fix_to,
    "hinge": expand_hinge,
    "slider": expand_slider,
    "lock_orthogonal_to": expand_lock_orthogonal_to,
    "yaw_free": expand_yaw_free,
}


def expand_relation(
    rel: dict[str, Any],
    bodies_spec: dict[str, dict[str, Any]],
    dof_policy: dict[str, Any],
    rel_index: int,
) -> list[dict[str, Any]]:
    """Dispatch on relation type. Raises for unknown relation types."""
    rtype = rel.get("type")
    expander = _EXPANDERS.get(str(rtype))
    if expander is None:
        raise ConstraintSchemaError(
            f"relations[{rel_index - 1}].type={rtype!r} unsupported "
            f"(expected one of {sorted(SUPPORTED_RELATION_TYPES)})"
        )
    return expander(rel, bodies_spec, dof_policy, rel_index)
