from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_llm_report(
    *,
    status: str,
    ground: str,
    solve_ok: bool,
    residual_max: float,
    dof_summary: dict[str, Any],
    warnings: list[str],
    conflicts: Optional[List[Dict[str, str]]] = None,
    rotation_issues: Optional[List[Dict[str, str]]] = None,
    schema_version: int = 1,
    mating_free: Optional[List[Dict[str, Any]]] = None,
    gauge_free: Optional[List[Dict[str, Any]]] = None,
    assumed_locks: Optional[List[Dict[str, Any]]] = None,
    witness_branches: Optional[Dict[str, Any]] = None,
    suggested_relations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if schema_version == 2:
        return _build_v2_report(
            status=status,
            ground=ground,
            solve_ok=solve_ok,
            residual_max=residual_max,
            dof_summary=dof_summary,
            warnings=warnings,
            conflicts=conflicts,
            rotation_issues=rotation_issues,
            mating_free=mating_free or [],
            gauge_free=gauge_free or [],
            assumed_locks=assumed_locks or [],
            witness_branches=witness_branches or {},
            suggested_relations=suggested_relations or [],
        )

    report: dict[str, Any] = {
        "status": status,
        "ground": ground,
        "solve_ok": solve_ok,
        "residual_max": round(float(residual_max), 9),
        "dof_deficit": int(dof_summary.get("dof_deficit", 0)),
        "free": dof_summary.get("free", [])[:5],
        "rotation_issues": (rotation_issues or [])[:5],
        "hint": _build_hints(
            status,
            dof_summary,
            warnings,
            conflicts or [],
            rotation_issues or [],
        ),
        "conflict": (conflicts or [])[:3],
    }
    return report


def _build_v2_report(
    *,
    status: str,
    ground: str,
    solve_ok: bool,
    residual_max: float,
    dof_summary: dict[str, Any],
    warnings: list[str],
    conflicts: Optional[List[Dict[str, str]]],
    rotation_issues: Optional[List[Dict[str, str]]],
    mating_free: list[dict[str, Any]],
    gauge_free: list[dict[str, Any]],
    assumed_locks: list[dict[str, Any]],
    witness_branches: dict[str, Any],
    suggested_relations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "status": status,
        "ground": ground,
        "solve_ok": solve_ok,
        "residual_max": round(float(residual_max), 9),
        "dof_deficit": int(dof_summary.get("dof_deficit", 0)),
        "mating_free": mating_free[:8],
        "gauge_free": gauge_free[:8],
        "assumed_locks": assumed_locks[:8],
        "rotation_issues": (rotation_issues or [])[:5],
        "conflict": (conflicts or [])[:3],
        "witness_branches": witness_branches,
        "suggested_relations": suggested_relations[:5],
        "hint": _build_hints_v2(
            status,
            warnings,
            conflicts or [],
            rotation_issues or [],
            mating_free,
            gauge_free,
            assumed_locks,
        ),
    }


def _build_hints(
    status: str,
    dof_summary: dict[str, Any],
    warnings: list[str],
    conflicts: list[dict[str, str]],
    rotation_issues: list[dict[str, str]],
) -> list[str]:
    hints: list[str] = []
    for warning in warnings[:2]:
        hints.append(warning)
    for issue in rotation_issues[:2]:
        hints.append(issue.get("hint", issue.get("reason", "rotation issue")))
    for conflict in conflicts[:2]:
        hints.append(conflict.get("reason", "constraint conflict"))
    if status == "underconstrained":
        for free in dof_summary.get("free", [])[:2]:
            body = free.get("body", "?")
            trans = ",".join(free.get("trans", []))
            rot = ",".join(free.get("rot", []))
            if trans:
                hints.append(f"为 {body} 增加相对支撑面的 in_plane 偏移（{trans}）")
            if rot:
                hints.append(f"为 {body} 增加 axis_parallel 锁定旋转（{rot}）")
        if not hints:
            hints.append("补充 point_plane_offset 或 point_coincident 约束")
    if status == "overconstrained" and not conflicts:
        hints.append("检查矛盾的 plane_coincident 与 plane_distance")
    return hints[:6]


def _build_hints_v2(
    status: str,
    warnings: list[str],
    conflicts: list[dict[str, str]],
    rotation_issues: list[dict[str, str]],
    mating_free: list[dict[str, Any]],
    gauge_free: list[dict[str, Any]],
    assumed_locks: list[dict[str, Any]],
) -> list[str]:
    hints: list[str] = []
    for warning in warnings[:2]:
        hints.append(warning)
    for issue in rotation_issues[:2]:
        hints.append(issue.get("hint", issue.get("reason", "rotation issue")))
    for conflict in conflicts[:2]:
        hints.append(conflict.get("reason", "constraint conflict"))
    if status == "underconstrained":
        for entry in mating_free[:2]:
            body = entry.get("body", "?")
            trans = ",".join(entry.get("trans", []))
            if trans:
                hints.append(f"为 {body} 增加 mating 约束（in_plane: {trans}）")
        for entry in gauge_free[:2]:
            body = entry.get("body", "?")
            hints.append(
                f"为 {body} 声明 gauge 破缺（category={entry.get('category', '?')}）"
            )
        if assumed_locks:
            hints.append(f"已自动补全 {len(assumed_locks)} 条 gauge 锁（见 assumed_locks）")
        if not hints:
            hints.append("补充 relations 或 constraints")
    if status == "ok_assumed" and assumed_locks:
        hints.append("gauge DOF 已由 assumed_locks 规则补全；生产环境可设 strict_ok")
    return hints[:6]
