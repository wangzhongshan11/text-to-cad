from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from common.render import relative_to_repo, sha256_file
from common.transforms import IDENTITY_TRANSFORM, relative_transform


ASSEMBLY_COMPOSITION_SCHEMA_VERSION = 1


class AssemblyCompositionError(ValueError):
    pass


def component_name(instance_path: Sequence[str]) -> str:
    return "__".join(str(part) for part in instance_path if str(part)) or "root"


def _relative_to_topology(topology_path: Path, target_path: Path) -> str:
    return os.path.relpath(target_path.resolve(), start=topology_path.resolve().parent).replace(os.sep, "/")


def _versioned_relative_url(topology_path: Path, target_path: Path, content_hash: str) -> str:
    suffix = f"?v={content_hash}" if content_hash else ""
    return f"{_relative_to_topology(topology_path, target_path)}{suffix}"


def _assembly_mesh_payload(topology_path: Path, mesh_path: Path) -> dict[str, Any]:
    mesh_hash = sha256_file(mesh_path) if mesh_path.exists() else ""
    return {
        "url": _versioned_relative_url(topology_path, mesh_path, mesh_hash)
        if mesh_hash
        else _relative_to_topology(topology_path, mesh_path),
        "hash": mesh_hash,
        "addressing": "gltf-node-extras",
        "occurrenceIdKey": "cadOccurrenceId",
    }


def build_native_assembly_composition(
    *,
    cad_ref: str,
    topology_path: Path,
    topology_manifest: dict[str, Any],
    mesh_path: Path,
) -> dict[str, Any]:
    occurrences = _rows(topology_manifest, "occurrences", "occurrenceColumns")
    if not occurrences:
        raise AssemblyCompositionError(f"Assembly topology has no occurrences: {cad_ref}")
    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    top_level: list[dict[str, Any]] = []
    for row in occurrences:
        parent_id = str(row.get("parentId") or "").strip()
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(row)
        else:
            top_level.append(row)

    root_occurrence = top_level[0] if len(top_level) == 1 else occurrences[0]
    root_children = top_level
    if len(top_level) == 1 and not children_by_parent.get(str(top_level[0].get("id") or "").strip()):
        root_children = top_level
    elif len(top_level) == 1:
        root_children = children_by_parent.get(str(top_level[0].get("id") or "").strip(), [])

    children = [
        _native_occurrence_node(
            row,
            children_by_parent=children_by_parent,
            topology_path=topology_path,
            parent_world_transform=IDENTITY_TRANSFORM,
        )
        for row in root_children
    ]
    if not children:
        row = root_occurrence
        children = [
            _native_part_node(
                row,
                topology_path=topology_path,
                parent_world_transform=IDENTITY_TRANSFORM,
            )
        ]
    return {
        "schemaVersion": ASSEMBLY_COMPOSITION_SCHEMA_VERSION,
        "mode": "native",
        "mesh": _assembly_mesh_payload(topology_path, mesh_path),
        "root": _assembly_root_node(cad_ref, root_occurrence, children),
    }


def _children_by_parent(occurrences: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    for row in occurrences:
        parent_id = str(row.get("parentId") or "").strip()
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(row)
    return children_by_parent


def _native_occurrence_node(
    row: dict[str, Any],
    *,
    children_by_parent: Mapping[str, list[dict[str, Any]]],
    topology_path: Path,
    parent_world_transform: tuple[float, ...],
) -> dict[str, Any]:
    row_id = str(row.get("id") or "").strip()
    children = children_by_parent.get(row_id, [])
    if not children:
        return _native_part_node(
            row,
            topology_path=topology_path,
            parent_world_transform=parent_world_transform,
        )
    world_transform = _row_transform(row)
    child_nodes = [
        _native_occurrence_node(
            child,
            children_by_parent=children_by_parent,
            topology_path=topology_path,
            parent_world_transform=world_transform,
        )
        for child in children
    ]
    return _assembly_node(
        id=row_id,
        occurrence_id=row_id,
        display_name=_occurrence_display_name(row),
        source_kind="native",
        source_path="",
        instance_path=str(row.get("path") or row_id),
        use_source_colors=True,
        local_transform=relative_transform(parent_world_transform, world_transform),
        world_transform=world_transform,
        bbox=row.get("bbox") or _merge_bbox([child.get("bbox") for child in child_nodes]),
        topology_counts=_public_topology_counts(_occurrence_topology_counts(row)),
        children=child_nodes,
    )


def _native_part_node(
    row: dict[str, Any],
    *,
    topology_path: Path,
    parent_world_transform: tuple[float, ...],
) -> dict[str, Any]:
    occurrence_id = str(row.get("id") or "").strip()
    if not occurrence_id:
        raise AssemblyCompositionError("Native assembly occurrence is missing an id")
    world_transform = _row_transform(row)
    return _part_node(
        id=occurrence_id,
        occurrence_id=occurrence_id,
        display_name=_occurrence_display_name(row),
        source_kind="native",
        source_path="",
        instance_path=str(row.get("path") or occurrence_id),
        use_source_colors=True,
        local_transform=relative_transform(parent_world_transform, world_transform),
        world_transform=world_transform,
        bbox=row.get("bbox"),
        topology_counts=_public_topology_counts(_occurrence_topology_counts(row)),
    )


def _part_node(
    *,
    id: str,
    occurrence_id: str,
    display_name: str,
    source_kind: str,
    source_path: str,
    instance_path: str,
    use_source_colors: bool,
    local_transform: Sequence[float],
    world_transform: Sequence[float],
    bbox: Any,
    topology_counts: Mapping[str, int],
    asset_url: str = "",
    asset_hash: str = "",
) -> dict[str, Any]:
    node = {
        "id": id,
        "occurrenceId": occurrence_id,
        "nodeType": "part",
        "displayName": display_name,
        "sourceKind": source_kind,
        "sourcePath": source_path,
        "instancePath": instance_path,
        "useSourceColors": use_source_colors,
        "localTransform": _transform_list(local_transform),
        "worldTransform": _transform_list(world_transform),
        "bbox": bbox,
        "topologyCounts": _public_topology_counts(topology_counts),
        "leafPartIds": [id],
        "children": [],
    }
    if asset_url:
        node["assets"] = {
            "glb": {
                "url": asset_url,
                "hash": asset_hash,
            }
        }
    return node


def _assembly_node(
    *,
    id: str,
    occurrence_id: str,
    display_name: str,
    source_kind: str,
    source_path: str,
    instance_path: str,
    use_source_colors: bool,
    local_transform: Sequence[float],
    world_transform: Sequence[float],
    bbox: Any,
    topology_counts: Mapping[str, int],
    children: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    leaf_part_ids = _leaf_part_ids(children)
    return {
        "id": id,
        "occurrenceId": occurrence_id,
        "nodeType": "assembly",
        "displayName": display_name,
        "sourceKind": source_kind,
        "sourcePath": source_path,
        "instancePath": instance_path,
        "useSourceColors": use_source_colors,
        "localTransform": _transform_list(local_transform),
        "worldTransform": _transform_list(world_transform),
        "bbox": bbox,
        "topologyCounts": _public_topology_counts(topology_counts),
        "leafPartIds": leaf_part_ids,
        "children": list(children),
    }


def _leaf_part_ids(children: Sequence[Mapping[str, Any]]) -> list[str]:
    ids: list[str] = []
    for child in children:
        child_ids = child.get("leafPartIds")
        if isinstance(child_ids, list):
            ids.extend(str(value) for value in child_ids if str(value or "").strip())
            continue
        child_id = str(child.get("id") or "").strip()
        if child_id:
            ids.append(child_id)
    return ids


def _assembly_root_node(cad_ref: str, root_occurrence: dict[str, Any], children: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts = _sum_public_counts(children)
    if not _counts_have_values(counts):
        counts = _public_topology_counts(_occurrence_topology_counts(root_occurrence))
    return _assembly_node(
        id="root",
        occurrence_id=str(root_occurrence.get("id") or "root").strip() or "root",
        display_name=_root_display_name(cad_ref, root_occurrence),
        source_kind="catalog",
        source_path="",
        instance_path="",
        use_source_colors=True,
        local_transform=IDENTITY_TRANSFORM,
        world_transform=IDENTITY_TRANSFORM,
        bbox=root_occurrence.get("bbox") or _merge_bbox([child.get("bbox") for child in children]),
        topology_counts=counts,
        children=children,
    )


def _root_display_name(cad_ref: str, root_occurrence: Mapping[str, Any]) -> str:
    display_name = str(root_occurrence.get("name") or "").strip()
    if not display_name or display_name.lower() == "root":
        return cad_ref.rsplit("/", 1)[-1]
    return display_name


def _rows(manifest: dict[str, Any], row_key: str, columns_key: str) -> list[dict[str, Any]]:
    columns = manifest.get("tables", {}).get(columns_key)
    rows = manifest.get(row_key)
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []
    output: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, list):
            output.append({str(column): row[index] if index < len(row) else None for index, column in enumerate(columns)})
    return output


def _occurrence_topology_counts(occurrence: Mapping[str, Any]) -> dict[str, int]:
    return {
        "shapes": int(occurrence.get("shapeCount") or 0),
        "faces": int(occurrence.get("faceCount") or 0),
        "edges": int(occurrence.get("edgeCount") or 0),
    }


def _public_topology_counts(counts: Mapping[str, int]) -> dict[str, int]:
    return {
        "shapes": int(counts.get("shapes") or 0),
        "faces": int(counts.get("faces") or 0),
        "edges": int(counts.get("edges") or 0),
    }


def _sum_public_counts(children: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    total = {"shapes": 0, "faces": 0, "edges": 0}
    for child in children:
        counts = child.get("topologyCounts")
        if not isinstance(counts, Mapping):
            continue
        for key in total:
            total[key] += int(counts.get(key) or 0)
    return total


def _counts_have_values(counts: Mapping[str, int]) -> bool:
    return any(int(counts.get(key) or 0) > 0 for key in ("shapes", "faces", "edges"))


def _occurrence_display_name(row: Mapping[str, Any]) -> str:
    name = str(row.get("name") or "").strip()
    source_name = str(row.get("sourceName") or "").strip()
    if name and not (name.startswith("=>[") and name.endswith("]")):
        return name
    return source_name or name or str(row.get("path") or row.get("id") or "component").strip()


def _row_transform(row: Mapping[str, Any]) -> tuple[float, ...]:
    raw_transform = row.get("transform")
    if not isinstance(raw_transform, list) or len(raw_transform) != 16:
        return IDENTITY_TRANSFORM
    return tuple(float(value) for value in raw_transform)


def _transform_list(transform: Sequence[float]) -> list[float]:
    return [float(value) for value in transform]


def _merge_bbox(boxes: Sequence[Any]) -> dict[str, Any]:
    valid_boxes = [
        box
        for box in boxes
        if isinstance(box, Mapping) and isinstance(box.get("min"), list) and isinstance(box.get("max"), list)
    ]
    if not valid_boxes:
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    mins = [list(box["min"]) for box in valid_boxes]
    maxs = [list(box["max"]) for box in valid_boxes]
    return {
        "min": [min(float(point[index]) for point in mins) for index in range(3)],
        "max": [max(float(point[index]) for point in maxs) for index in range(3)],
    }
