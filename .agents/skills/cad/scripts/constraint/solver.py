from __future__ import annotations

import math
from typing import Any

import numpy as np

from .audit import axis_lock_preflight_warnings, rotation_audit_issues
from .constraints import CompiledConstraint, compile_constraints
from .dof import numeric_jacobian, summarize_dof
from .emit import transforms_for_instances
from .errors import ConstraintSolveError
from .graph import expand_constraints, static_preflight
from .report import build_llm_report
from .schema import validate_assembly_spec
from .state import (
    STATE_DIM,
    BodyPose,
    identity_pose,
    pack_poses,
    quaternion_residual,
    unpack_poses,
)


RESIDUAL_TOL = 1e-6
MAX_NFEV = 4000


def solve_assembly(spec: dict[str, Any], *, verbose: bool = False) -> dict[str, Any]:
    validated = validate_assembly_spec(spec)
    ground = validated["ground"]
    catalog = validated["catalog"]
    body_ids = tuple(sorted(catalog.keys()))
    constraints = expand_constraints(validated["constraints"])

    if not any(constraint.get("type") == "fix" and constraint.get("body", constraint.get("a")) == ground for constraint in constraints):
        constraints = [{"id": "ground_fix", "type": "fix", "body": ground}, *constraints]

    warnings = list(validated.get("scale_warnings", []))
    warnings.extend(static_preflight(ground=ground, body_ids=body_ids, constraints=constraints))
    warnings.extend(axis_lock_preflight_warnings(ground=ground, constraints=constraints, catalog=catalog))
    compiled = compile_constraints(constraints, catalog)

    poses0 = _initial_poses(body_ids, ground=ground, catalog=catalog, initial_guess=validated["initial_guess"])
    vector0 = pack_poses(body_ids, poses0)

    def residual_vector(vector: np.ndarray) -> np.ndarray:
        poses = unpack_poses(body_ids, vector)
        values: list[float] = []
        for body_id in body_ids:
            values.append(quaternion_residual(poses[body_id].quaternion_xyzw))
        for constraint in compiled:
            values.extend(constraint.residual_fn(poses))
        return np.asarray(values, dtype=float)

    if verbose:
        initial_residual = residual_vector(vector0)
        print(f"initial residual max={float(np.max(np.abs(initial_residual))):.6g}")

    solution_vector, solver_message, success_flag, nfev = _run_optimizer(residual_vector, vector0)

    poses = unpack_poses(body_ids, solution_vector)
    final_residual = residual_vector(solution_vector)
    residual_max = float(np.max(np.abs(final_residual))) if final_residual.size else 0.0
    solve_ok = residual_max < RESIDUAL_TOL * 10.0

    jacobian = numeric_jacobian(residual_vector, solution_vector)
    dof_summary = summarize_dof(jacobian, body_ids=body_ids)

    rotation_issues = rotation_audit_issues(
        ground=ground,
        poses=poses,
        constraints=constraints,
        catalog=catalog,
    )
    if rotation_issues:
        for issue in rotation_issues[:3]:
            warnings.append(issue.get("hint", issue.get("reason", "rotation audit issue")))

    status = "ok"
    free_entries = dof_summary.get("free", [])
    bodies_with_trans_free = {str(entry.get("body")) for entry in free_entries if entry.get("trans")}
    has_rotation_issue = bool(rotation_issues)
    if solve_ok and has_rotation_issue:
        status = "underconstrained"
    elif solve_ok and len(bodies_with_trans_free) >= 2:
        status = "underconstrained"
    elif solve_ok and any("likely_underconstrained" in warning for warning in warnings):
        status = "underconstrained"
    elif solve_ok and any("missing_in_plane_axis_lock" in warning for warning in warnings):
        status = "underconstrained"
    if not solve_ok:
        status = "overconstrained" if residual_max > 1.0 else "solve_failed"

    llm_report = build_llm_report(
        status=status,
        ground=ground,
        solve_ok=solve_ok,
        residual_max=residual_max,
        dof_summary=dof_summary,
        warnings=warnings,
        rotation_issues=rotation_issues,
    )

    output = {
        "status": status,
        "solve_ok": solve_ok,
        "residual_max": residual_max,
        "poses": poses,
        "transforms": transforms_for_instances(poses),
        "report": llm_report,
        "warnings": warnings,
        "rotation_issues": rotation_issues,
        "solver_message": solver_message,
        "nfev": int(nfev),
    }

    if status not in {"ok", "underconstrained"} and not solve_ok:
        raise ConstraintSolveError(
            f"constraint solve failed: {solver_message}",
            report=llm_report,
        )

    return output


def _run_optimizer(
    residual_vector,
    vector0: np.ndarray,
) -> tuple[np.ndarray, str, bool, int]:
    try:
        from scipy.optimize import least_squares

        result = least_squares(
            residual_vector,
            vector0,
            method="trf",
            ftol=RESIDUAL_TOL,
            xtol=RESIDUAL_TOL,
            gtol=RESIDUAL_TOL,
            max_nfev=MAX_NFEV,
        )
        return result.x, str(result.message), bool(result.success), int(result.nfev)
    except ImportError:
        return _damped_gauss_newton(residual_vector, vector0)


def _damped_gauss_newton(
    residual_vector,
    vector0: np.ndarray,
    *,
    max_iter: int = 500,
) -> tuple[np.ndarray, str, bool, int]:
    vector = np.asarray(vector0, dtype=float).copy()
    nfev = 0
    for _ in range(max_iter):
        residual = residual_vector(vector)
        nfev += 1
        if float(np.max(np.abs(residual))) < RESIDUAL_TOL:
            return vector, "numpy damped gauss-newton converged", True, nfev
        jacobian = numeric_jacobian(residual_vector, vector)
        try:
            step, *_ = np.linalg.lstsq(jacobian, -residual, rcond=None)
        except np.linalg.LinAlgError:
            return vector, "numpy solver failed: singular jacobian", False, nfev
        vector = vector + step
    residual = residual_vector(vector)
    nfev += 1
    success = float(np.max(np.abs(residual))) < RESIDUAL_TOL * 10.0
    message = "numpy damped gauss-newton converged" if success else "numpy solver max iterations"
    return vector, message, success, nfev


def _initial_poses(
    body_ids: tuple[str, ...],
    *,
    ground: str,
    catalog,
    initial_guess: dict[str, object],
) -> dict[str, BodyPose]:
    poses: dict[str, BodyPose] = {body_id: identity_pose() for body_id in body_ids}
    ground_top = 0.0
    if ground in catalog and catalog[ground].primitive == "box":
        ground_top = float(catalog[ground].parameters.get("lz", 0.0)) / 2.0
    offset = 0.0
    for body_id in body_ids:
        if body_id == ground:
            continue
        primitive = catalog[body_id]
        z_shift = 0.0
        if primitive.primitive == "box":
            z_shift = float(primitive.parameters.get("lz", 0.0)) / 2.0
        elif primitive.primitive == "cylinder":
            z_shift = float(primitive.parameters.get("height", 0.0)) / 2.0
        elif primitive.primitive == "sphere":
            z_shift = float(primitive.parameters.get("radius", 0.0))
        poses[body_id] = BodyPose((0.0, 0.0, ground_top + z_shift + 5.0 + offset), (0.0, 0.0, 0.0, 1.0))
        offset += 2.0

    for body_id, raw_guess in initial_guess.items():
        if body_id not in poses:
            continue
        if isinstance(raw_guess, (list, tuple)) and len(raw_guess) == 16:
            matrix = np.asarray(raw_guess, dtype=float).reshape(4, 4)
            rotation = matrix[:3, :3]
            translation = matrix[:3, 3]
            from .state import rotation_matrix_to_quaternion_xyzw

            poses[body_id] = BodyPose(
                (float(translation[0]), float(translation[1]), float(translation[2])),
                rotation_matrix_to_quaternion_xyzw(rotation),
            )
        elif isinstance(raw_guess, (list, tuple)) and len(raw_guess) == 7:
            poses[body_id] = BodyPose(
                (float(raw_guess[0]), float(raw_guess[1]), float(raw_guess[2])),
                (float(raw_guess[3]), float(raw_guess[4]), float(raw_guess[5]), float(raw_guess[6])),
            )
    return poses


def validate_only(spec: dict[str, Any]) -> dict[str, Any]:
    validated = validate_assembly_spec(spec)
    ground = validated["ground"]
    catalog = validated["catalog"]
    body_ids = tuple(sorted(catalog.keys()))
    constraints = expand_constraints(validated["constraints"])
    warnings = list(validated.get("scale_warnings", []))
    warnings.extend(static_preflight(ground=ground, body_ids=body_ids, constraints=constraints))
    warnings.extend(axis_lock_preflight_warnings(ground=ground, constraints=constraints, catalog=catalog))
    return {
        "status": "validated",
        "ground": ground,
        "body_ids": body_ids,
        "limits": validated.get("limits"),
        "warnings": warnings,
        "feature_index": validated["feature_index"],
    }
