from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def constraint_assembly(
    constraints: dict[str, Any],
    parts: Mapping[str, object],
    *,
    spec_path: str | Path | None = None,
    report_path: str | Path | None = None,
) -> object:
    """Solve constraints and return a build123d Compound of placed parts.

    Parts stay in local coordinates (geometric center origin). Transforms from the
    solver are applied with build123d before composing the assembly.
    """
    import build123d
    from common.transforms import location_from_transform

    from .errors import ConstraintAssemblyError
    from .solver import solve_assembly

    if not isinstance(constraints, dict):
        raise TypeError("constraints must be a dict")
    if not isinstance(parts, Mapping) or not parts:
        raise TypeError("parts must be a non-empty mapping of body_id to build123d shapes")

    from .schema import validate_assembly_spec

    resolved_path = (
        Path(spec_path).expanduser().resolve()
        if spec_path is not None
        else None
    )
    validated = validate_assembly_spec(
        constraints,
        spec_path=resolved_path,
    )
    body_ids = set(validated["catalog"].keys())
    part_ids = set(parts.keys())
    if part_ids != body_ids:
        missing = sorted(body_ids - part_ids)
        extra = sorted(part_ids - body_ids)
        details: list[str] = []
        if missing:
            details.append(f"missing parts for bodies: {', '.join(missing)}")
        if extra:
            details.append(f"unknown part keys: {', '.join(extra)}")
        raise ValueError("; ".join(details))

    try:
        solve_result = solve_assembly(
            constraints,
            spec_path=str(resolved_path) if resolved_path is not None else None,
        )
    except ConstraintAssemblyError as exc:
        raise RuntimeError(str(exc)) from exc

    report = solve_result.get("report")
    if report_path is not None and isinstance(report, dict):
        target = Path(report_path).expanduser()
        if not target.is_absolute():
            target = (Path.cwd() / target).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    status = str(solve_result.get("status", ""))
    if status not in {"ok", "ok_assumed", "underconstrained"}:
        hint = report.get("hint") if isinstance(report, dict) else status
        raise RuntimeError(f"constraint solve failed: {hint}")

    transforms = solve_result.get("transforms")
    if not isinstance(transforms, dict):
        raise RuntimeError("constraint solve did not return transforms")

    children: list[object] = []
    for body_id, raw_shape in parts.items():
        if body_id not in transforms:
            raise RuntimeError(f"constraint solve missing transform for part {body_id!r}")
        matrix = transforms[body_id]
        if not isinstance(matrix, (list, tuple)) or len(matrix) != 16:
            raise RuntimeError(f"invalid transform for part {body_id!r}")
        placed = raw_shape.moved(location_from_transform(tuple(float(v) for v in matrix)))
        label = getattr(placed, "label", None)
        if label in (None, ""):
            placed.label = str(body_id)
        children.append(placed)

    return build123d.Compound(label="assembly", children=children)
