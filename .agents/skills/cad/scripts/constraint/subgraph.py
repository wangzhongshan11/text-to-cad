"""P2a: sub_spec subgraph loading, validation, proxy injection, and transform compose."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .dsl import V2_BODY_FIELDS, detect_spec_version
from .errors import ConstraintSchemaError, SubSpecCycleError

MAX_SUB_SPEC_DEPTH = 3

REF_KEYS = frozenset(
    {
        "a",
        "b",
        "body",
        "child",
        "parent",
        "point",
        "plane",
        "on",
        "point_a",
        "point_b",
        "target",
    }
)

@dataclass(frozen=True)
class SubSpecInstance:
    instance_id: str
    sub_spec_path: str
    anchor_body: str
    exports: tuple[str, ...]
    child_body_ids: tuple[str, ...]
    child_spec: dict[str, Any]


@dataclass
class SubGraphBundle:
    instances: list[SubSpecInstance]
    solve_cache: dict[str, dict[str, Any]] = field(default_factory=dict)


def resolve_sub_spec_path(base_dir: Path, ref: str) -> Path:
    path = Path(ref)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    if not path.is_file():
        raise ConstraintSchemaError(f"sub_spec file not found: {path}")
    return path


def load_spec_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConstraintSchemaError(f"sub_spec root must be an object: {path}")
    return payload


def _parse_interface_spec(sub_spec: dict[str, Any], *, path: Path) -> tuple[str, list[str]]:
    iface = sub_spec.get("interface_spec")
    if not isinstance(iface, dict):
        raise ConstraintSchemaError(
            f"sub_spec {path.name}: missing top-level 'interface_spec'"
        )
    anchor = iface.get("interface_body")
    if not isinstance(anchor, str) or not anchor.strip():
        raise ConstraintSchemaError(
            f"sub_spec {path.name}: interface_spec.interface_body is required"
        )
    bodies = sub_spec.get("bodies") or {}
    if anchor not in bodies:
        raise ConstraintSchemaError(
            f"sub_spec {path.name}: interface_body {anchor!r} not found in bodies"
        )
    exports = iface.get("exports")
    if not isinstance(exports, list) or not exports:
        raise ConstraintSchemaError(
            f"sub_spec {path.name}: interface_spec.exports must be a non-empty array"
        )
    if len(exports) > 3:
        raise ConstraintSchemaError(
            f"sub_spec {path.name}: interface_spec.exports exceeds limit of 3"
        )
    normalized: list[str] = []
    for index, export in enumerate(exports, start=1):
        if not isinstance(export, str) or "." not in export:
            raise ConstraintSchemaError(
                f"sub_spec {path.name}: exports[{index - 1}] must be '<body>.<feature>'"
            )
        if not export.startswith(f"{anchor}."):
            raise ConstraintSchemaError(
                f"sub_spec {path.name}: export {export!r} must start with "
                f"{anchor + '.'!r}"
            )
        normalized.append(export)
    return anchor, normalized


def _proxy_primitive_from_anchor(anchor_spec: dict[str, Any]) -> dict[str, Any]:
    skip = set(V2_BODY_FIELDS) | {"sub_spec", "anchor_body"}
    proxy = {key: value for key, value in anchor_spec.items() if key not in skip}
    if "primitive" not in proxy:
        raise ConstraintSchemaError("anchor body for sub_spec proxy lacks 'primitive'")
    return proxy


def _collect_feature_refs(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in REF_KEYS and isinstance(item, str) and "." in item:
                refs.append(item)
            else:
                refs.extend(_collect_feature_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_collect_feature_refs(item))
    return refs


def _split_body_feature(ref: str) -> tuple[str, str]:
    body_id, feature = ref.split(".", 1)
    return body_id, feature


def _export_suffixes(anchor: str, exports: list[str]) -> set[str]:
    prefix = f"{anchor}."
    return {export[len(prefix) :] for export in exports if export.startswith(prefix)}


def _allowed_instance_refs(instance_id: str, anchor: str, exports: list[str]) -> set[str]:
    allowed: set[str] = set()
    for suffix in _export_suffixes(anchor, exports):
        allowed.add(f"{instance_id}.{suffix}")
    return allowed


def validate_parent_cross_layer_refs(
    parent_spec: dict[str, Any],
    instances: list[SubSpecInstance],
) -> None:
    """Reject references to private child bodies or non-exported instance features."""
    internal_ids: dict[str, set[str]] = {}
    allowed_refs: dict[str, set[str]] = {}
    for instance in instances:
        internal = set(instance.child_body_ids) - {instance.anchor_body}
        internal_ids[instance.instance_id] = internal
        allowed_refs[instance.instance_id] = _allowed_instance_refs(
            instance.instance_id, instance.anchor_body, list(instance.exports)
        )

    for ref in _collect_feature_refs(parent_spec):
        body_id, feature = _split_body_feature(ref)
        for instance in instances:
            if body_id in internal_ids.get(instance.instance_id, set()):
                raise ConstraintSchemaError(
                    f"error.cross_layer_internal_ref: {ref!r} references private "
                    f"body {body_id!r} inside sub_spec {instance.sub_spec_path!r}"
                )
            if body_id == instance.instance_id:
                full_ref = f"{body_id}.{feature}"
                if full_ref not in allowed_refs[instance.instance_id]:
                    raise ConstraintSchemaError(
                        f"error.cross_layer_internal_ref: {ref!r} is not listed in "
                        f"sub_spec exports {list(instance.exports)!r}"
                    )


def check_sub_spec_dag(root_file: Path, *, max_depth: int = MAX_SUB_SPEC_DEPTH) -> None:
    """DFS cycle detection and depth limit (L ≤ max_depth) over sub_spec references."""
    visiting: set[Path] = set()
    visited: set[Path] = set()
    stack: list[Path] = []

    def dfs(path: Path, depth: int) -> None:
        if depth > max_depth:
            raise ConstraintSchemaError(
                f"error.depth: sub_spec nesting depth {depth} exceeds L={max_depth} "
                f"at {path.name}"
            )
        resolved = path.resolve()
        if resolved in visiting:
            start = stack.index(resolved)
            cycle = " → ".join(p.name for p in stack[start:]) + f" → {path.name}"
            raise SubSpecCycleError(f"error.cycle: sub_spec cycle: {cycle}")
        if resolved in visited:
            return
        visiting.add(resolved)
        stack.append(resolved)
        spec = load_spec_file(resolved)
        if detect_spec_version(spec) != 2:
            raise ConstraintSchemaError(
                f"sub_spec {path.name}: nested spec must declare 'version': 2"
            )
        for body in (spec.get("bodies") or {}).values():
            if isinstance(body, dict) and "sub_spec" in body:
                child_path = resolve_sub_spec_path(path.parent, str(body["sub_spec"]))
                dfs(child_path, depth + 1)
        stack.pop()
        visiting.remove(resolved)
        visited.add(resolved)

    dfs(root_file.resolve(), depth=1)


def prepare_spec_with_subgraphs(
    spec: dict[str, Any],
    spec_path: Path | None,
) -> tuple[dict[str, Any], SubGraphBundle | None]:
    """Resolve ``sub_spec`` bodies into proxy primitives; return parent spec + metadata."""
    bodies = spec.get("bodies") or {}
    sub_entries = [
        (body_id, body)
        for body_id, body in bodies.items()
        if isinstance(body, dict) and "sub_spec" in body
    ]
    if not sub_entries:
        return spec, None

    if spec_path is None:
        raise ConstraintSchemaError(
            "spec contains sub_spec bodies but no spec_path was provided for resolution"
        )
    root_file = spec_path.resolve()
    base_dir = root_file.parent

    child_cache: dict[str, dict[str, Any]] = {}
    for _instance_id, body in sub_entries:
        sub_path = resolve_sub_spec_path(base_dir, str(body["sub_spec"]))
        child_cache[str(sub_path.resolve())] = load_spec_file(sub_path)

    check_sub_spec_dag(root_file)

    instances: list[SubSpecInstance] = []
    parent_bodies = dict(bodies)

    for instance_id, body in sub_entries:
        sub_ref = str(body["sub_spec"])
        sub_path = resolve_sub_spec_path(base_dir, sub_ref)
        child_spec = child_cache[str(sub_path.resolve())]
        anchor, exports = _parse_interface_spec(child_spec, path=sub_path)
        anchor = str(body.get("anchor_body") or anchor)
        child_bodies = child_spec.get("bodies") or {}
        if anchor not in child_bodies:
            raise ConstraintSchemaError(
                f"bodies[{instance_id}]: anchor_body {anchor!r} not found in "
                f"sub_spec {sub_path.name}"
            )
        parent_bodies[instance_id] = _proxy_primitive_from_anchor(child_bodies[anchor])
        instances.append(
            SubSpecInstance(
                instance_id=instance_id,
                sub_spec_path=str(sub_path.resolve()),
                anchor_body=anchor,
                exports=tuple(exports),
                child_body_ids=tuple(child_bodies.keys()),
                child_spec=child_spec,
            )
        )

    parent_spec = {**spec, "bodies": parent_bodies}
    validate_parent_cross_layer_refs(parent_spec, instances)
    return parent_spec, SubGraphBundle(instances=instances)


def multiply_transform_4x4(
    parent: tuple[float, ...],
    child: tuple[float, ...],
) -> tuple[float, ...]:
    matrix = np.asarray(parent, dtype=float).reshape(4, 4) @ np.asarray(
        child, dtype=float
    ).reshape(4, 4)
    return tuple(float(value) for value in matrix.reshape(-1))


def compose_world_transforms(
    parent_transforms: dict[str, tuple[float, ...]],
    bundle: SubGraphBundle,
) -> dict[str, tuple[float, ...]]:
    """World transforms = parent_T(instance) · sub_local_T(child body)."""
    world = dict(parent_transforms)
    for instance in bundle.instances:
        sub_result = bundle.solve_cache.get(instance.sub_spec_path)
        if sub_result is None:
            continue
        sub_transforms = sub_result.get("transforms", {})
        if not isinstance(sub_transforms, dict):
            continue
        parent_matrix = parent_transforms.get(instance.instance_id)
        if parent_matrix is None:
            continue
        for body_id, local_matrix in sub_transforms.items():
            if body_id == instance.anchor_body:
                continue
            if not isinstance(local_matrix, (list, tuple)) or len(local_matrix) != 16:
                continue
            local_tuple = tuple(float(value) for value in local_matrix)
            world[body_id] = multiply_transform_4x4(parent_matrix, local_tuple)
    return world


def merge_child_catalogs(
    parent_catalog: dict[str, Any],
    bundle: SubGraphBundle,
    *,
    child_catalogs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    merged = dict(parent_catalog)
    for instance in bundle.instances:
        child_catalog = child_catalogs.get(instance.sub_spec_path, {})
        for body_id, primitive in child_catalog.items():
            if body_id in merged and body_id != instance.instance_id:
                raise ConstraintSchemaError(
                    f"sub_spec body id collision: {body_id!r} appears in parent and "
                    f"child {instance.sub_spec_path!r}"
                )
            merged[body_id] = primitive
    return merged


def solve_sub_spec_hierarchy(
    spec: dict[str, Any],
    *,
    spec_path: str | Path,
    solve_core,
    verbose: bool = False,
    verify_jacobian: bool = False,
    cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Solve a spec and nested sub_spec files bottom-up; return composed world transforms."""
    resolved = Path(spec_path).resolve()
    cache = cache if cache is not None else {}
    key = str(resolved)
    if key in cache:
        return cache[key]

    from .schema import validate_assembly_spec

    validated = validate_assembly_spec(spec, spec_path=resolved)
    sub_bundle: SubGraphBundle | None = validated.get("sub_bundle")

    if sub_bundle is not None:
        for instance in sub_bundle.instances:
            solve_sub_spec_hierarchy(
                instance.child_spec,
                spec_path=instance.sub_spec_path,
                solve_core=solve_core,
                verbose=verbose,
                verify_jacobian=False,
                cache=cache,
            )
        parent_catalog = {
            body_id: validated["catalog"][body_id]
            for body_id in validated["bodies"]
            if body_id in validated["catalog"]
        }
        parent_validated = {**validated, "catalog": parent_catalog}
        parent_result = solve_core(
            parent_validated,
            verbose=verbose,
            verify_jacobian=verify_jacobian,
        )
        sub_bundle.solve_cache.clear()
        for instance in sub_bundle.instances:
            child_key = str(Path(instance.sub_spec_path).resolve())
            sub_bundle.solve_cache[child_key] = cache[child_key]
        world_transforms = compose_world_transforms(
            parent_result["transforms"],
            sub_bundle,
        )
        output = dict(parent_result)
        output["transforms"] = world_transforms
        output["solve_method"] = f"{parent_result.get('solve_method', 'scipy')}+sub_spec"
    else:
        output = solve_core(
            validated,
            verbose=verbose,
            verify_jacobian=verify_jacobian,
        )

    cache[key] = output
    return output
