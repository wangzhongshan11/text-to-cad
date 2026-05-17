from __future__ import annotations

from typing import Any


def expand_constraints(raw_constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for constraint in raw_constraints:
        constraint_type = str(constraint["type"])
        constraint_id = str(constraint.get("id", ""))

        if constraint_type == "contact":
            expanded.append(
                {
                    "id": f"{constraint_id}_pc",
                    "type": "plane_coincident",
                    "a": constraint["a"],
                    "b": constraint["b"],
                    "opposed": True,
                }
            )
            continue

        if constraint_type == "hinge":
            expanded.append(
                {
                    "id": f"{constraint_id}_ax",
                    "type": "axis_coaxial",
                    "a": constraint["a"],
                    "b": constraint["b"],
                }
            )
            expanded.append(
                {
                    "id": f"{constraint_id}_pt",
                    "type": "point_coincident",
                    "a": constraint.get("point_a", constraint["a"]),
                    "b": constraint.get("point_b", constraint["b"]),
                }
            )
            continue

        expanded.append(dict(constraint))
    return expanded


def static_preflight(
    *,
    ground: str,
    body_ids: tuple[str, ...],
    constraints: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if not ground:
        warnings.append("missing_gauge: ground is required")
    plane_contacts = [
        constraint
        for constraint in constraints
        if constraint.get("type") in {"plane_coincident", "contact"}
    ]
    offsets = [constraint for constraint in constraints if constraint.get("type") == "point_plane_offset"]
    if len(plane_contacts) >= 2 and len(offsets) < 2:
        warnings.append("likely_underconstrained: multiple plane contacts without in-plane offsets")
    return warnings
