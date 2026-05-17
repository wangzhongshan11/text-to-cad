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
) -> Dict[str, Any]:
    report: dict[str, Any] = {
        "status": status,
        "ground": ground,
        "solve_ok": solve_ok,
        "residual_max": round(float(residual_max), 9),
        "dof_deficit": int(dof_summary.get("dof_deficit", 0)),
        "free": dof_summary.get("free", [])[:5],
        "rotation_issues": (rotation_issues or [])[:5],
        "hint": _build_hints(status, dof_summary, warnings, conflicts or [], rotation_issues or []),
        "conflict": (conflicts or [])[:3],
    }
    return report


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
