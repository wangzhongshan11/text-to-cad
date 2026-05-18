from __future__ import annotations

import math
from typing import Any

import numpy as np

from .analytic import bucket_bodies, try_place_analytic_bodies
from .free_solve import solve_free_bucket
from .yaw_solve import solve_yaw_bucket
from .bfs_init import bfs_initial_poses
from .subgraph import solve_sub_spec_hierarchy
from .audit import axis_lock_preflight_warnings, rotation_audit_issues
from .constraints import CompiledConstraint, compile_constraints
from .diagnostics import (
    apply_gauge_auto_lock,
    classify_free_directions,
    derive_status_v2,
    enumerate_witnesses,
    find_mus,
    gauge_free_to_rotation_issues,
    suggest_relations,
)
from .dof import numeric_jacobian, summarize_dof
from .dsl import DEFAULT_DOF_POLICY
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


def _residual_vector(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    *,
    active_bodies: frozenset[str] | None = None,
) -> np.ndarray:
    values: list[float] = []
    active = active_bodies
    for body_id in body_ids:
        if active is not None and body_id not in active:
            continue
        values.append(quaternion_residual(poses[body_id].quaternion_xyzw))
    for constraint in compiled:
        if active is not None and not any(
            body_id in active for body_id in constraint.body_ids
        ):
            continue
        values.extend(constraint.residual_fn(poses))
    return np.asarray(values, dtype=float)


def _residual_max(
    body_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    poses: dict[str, BodyPose],
    *,
    active_bodies: frozenset[str] | None = None,
) -> float:
    residual = _residual_vector(
        body_ids,
        compiled,
        poses,
        active_bodies=active_bodies,
    )
    if residual.size == 0:
        return 0.0
    return float(np.max(np.abs(residual)))


def _solve_body_ids(
    body_ids: tuple[str, ...],
    layout_only_ids: frozenset[str],
) -> tuple[str, ...]:
    return tuple(body_id for body_id in body_ids if body_id not in layout_only_ids)


def _with_ground_fix_if_needed(
    constraints: list[dict[str, Any]],
    *,
    ground: str,
) -> list[dict[str, Any]]:
    """Add a ground ``fix`` only when the ground body is not already anchored."""
    if any(
        constraint.get("type") == "fix"
        and constraint.get("body", constraint.get("a")) == ground
        for constraint in constraints
    ):
        return constraints
    if any(
        constraint.get("type") == "fix_to" and constraint.get("parent") == ground
        for constraint in constraints
    ):
        return constraints
    if any(
        isinstance(constraint.get("triggered_by"), str)
        and "fix_to" in constraint["triggered_by"]
        and any(
            isinstance(value, str) and value.split(".", 1)[0] == ground
            for value in constraint.values()
        )
        for constraint in constraints
    ):
        return constraints
    return [{"id": "ground_fix", "type": "fix", "body": ground}, *constraints]


def _merge_poses(
    body_ids: tuple[str, ...],
    *,
    solved: dict[str, BodyPose],
    fixed: dict[str, BodyPose],
) -> dict[str, BodyPose]:
    poses: dict[str, BodyPose] = {}
    for body_id in body_ids:
        if body_id in fixed:
            poses[body_id] = fixed[body_id]
        else:
            poses[body_id] = solved.get(body_id, identity_pose())
    return poses


def _scipy_seed_poses(
    *,
    body_ids: tuple[str, ...],
    solve_ids: tuple[str, ...],
    ground: str,
    catalog,
    constraints: list[dict[str, Any]],
    initial_guess: dict[str, object],
    layout_poses: dict[str, BodyPose],
    initial_poses: dict[str, BodyPose] | None,
    use_bfs: bool = True,
) -> dict[str, BodyPose]:
    fixed: dict[str, BodyPose] = {ground: identity_pose(), **layout_poses}
    poses: dict[str, BodyPose] = dict(fixed)
    if initial_poses:
        poses.update(initial_poses)
        for body_id, pose in fixed.items():
            poses[body_id] = pose

    if use_bfs:
        bfs_poses = bfs_initial_poses(
            body_ids=body_ids,
            ground=ground,
            catalog=catalog,
            constraints=constraints,
            layout_poses=layout_poses,
            solved_poses=poses,
        )
        for body_id in solve_ids:
            if body_id not in poses and body_id in bfs_poses:
                poses[body_id] = bfs_poses[body_id]

    z_fallback = _initial_poses(
        solve_ids,
        ground=ground,
        catalog=catalog,
        initial_guess=initial_guess if not use_bfs else {},
    )
    for body_id in solve_ids:
        if body_id not in poses:
            poses[body_id] = z_fallback[body_id]
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
                (
                    float(raw_guess[3]),
                    float(raw_guess[4]),
                    float(raw_guess[5]),
                    float(raw_guess[6]),
                ),
            )
    return poses


def _run_scipy_solve(
    *,
    body_ids: tuple[str, ...],
    solve_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    catalog,
    ground: str,
    constraints: list[dict[str, Any]],
    initial_guess: dict[str, object],
    layout_poses: dict[str, BodyPose] | None = None,
    initial_poses: dict[str, BodyPose] | None = None,
    use_bfs: bool = True,
    verbose: bool = False,
    residual_active_bodies: frozenset[str] | None = None,
) -> tuple[dict[str, BodyPose], float, bool, str, int, bool]:
    layout_poses = layout_poses or {}
    initial_poses = initial_poses or {}
    fixed_poses = dict(layout_poses)
    solve_set = set(solve_ids)
    for body_id, pose in initial_poses.items():
        if body_id not in solve_set:
            fixed_poses[body_id] = pose
    poses0 = _scipy_seed_poses(
        body_ids=body_ids,
        solve_ids=solve_ids,
        ground=ground,
        catalog=catalog,
        constraints=constraints,
        initial_guess=initial_guess,
        layout_poses=layout_poses,
        initial_poses=initial_poses,
        use_bfs=use_bfs,
    )
    vector0 = pack_poses(solve_ids, poses0)

    def residual_vector(vector: np.ndarray) -> np.ndarray:
        partial = unpack_poses(solve_ids, vector)
        poses = _merge_poses(body_ids, solved=partial, fixed=fixed_poses)
        if ground not in poses:
            poses[ground] = identity_pose()
        return _residual_vector(body_ids, compiled, poses)

    if verbose:
        initial_residual = residual_vector(vector0)
        print(f"initial residual max={float(np.max(np.abs(initial_residual))):.6g}")

    solution_vector, solver_message, scipy_converged, nfev = _run_optimizer(
        residual_vector, vector0
    )
    partial = unpack_poses(solve_ids, solution_vector)
    poses = _merge_poses(body_ids, solved=partial, fixed=fixed_poses)
    if ground not in poses:
        poses[ground] = identity_pose()
    residual_max = _residual_max(
        body_ids,
        compiled,
        poses,
        active_bodies=residual_active_bodies,
    )
    solve_ok = residual_max < RESIDUAL_TOL * 10.0 or (
        scipy_converged and residual_max < 1e-4
    )
    return poses, residual_max, solve_ok, solver_message, nfev, scipy_converged


def solve_assembly(
    spec: dict[str, Any],
    *,
    spec_path: str | None = None,
    verbose: bool = False,
    verify_jacobian: bool = False,
) -> dict[str, Any]:
    from pathlib import Path

    path = Path(spec_path).resolve() if spec_path is not None else None
    validated = validate_assembly_spec(spec, spec_path=path)
    if validated.get("sub_bundle") is not None and path is not None:
        return solve_sub_spec_hierarchy(
            spec,
            spec_path=path,
            solve_core=_solve_validated_core,
            verbose=verbose,
            verify_jacobian=verify_jacobian,
        )

    return _solve_validated_core(validated, verbose=verbose, verify_jacobian=verify_jacobian)


def _solve_validated_core(
    validated: dict[str, Any],
    *,
    verbose: bool = False,
    verify_jacobian: bool = False,
) -> dict[str, Any]:
    ground = validated["ground"]
    catalog = validated["catalog"]
    body_ids = tuple(sorted(catalog.keys()))
    rotation_modes: dict[str, str] = validated.get("rotation_modes", {})
    yaw_axes: dict[str, str] = validated.get("yaw_axes", {})
    spec_version = int(validated.get("spec_version", 1))
    dof_policy: dict[str, Any] = validated.get("dof_policy") or dict(DEFAULT_DOF_POLICY)
    layout_only_ids: frozenset[str] = validated.get("layout_only_ids", frozenset())
    layout_poses: dict[str, BodyPose] = validated.get("layout_poses", {})
    verify_only: bool = bool(validated.get("verify_only", False))
    solve_ids = _solve_body_ids(body_ids, layout_only_ids)
    constraints = expand_constraints(validated["constraints"])
    constraints = _with_ground_fix_if_needed(constraints, ground=ground)

    warnings = list(validated.get("scale_warnings", []))
    warnings.extend(static_preflight(ground=ground, body_ids=body_ids, constraints=constraints))
    if spec_version == 1:
        warnings.extend(
            axis_lock_preflight_warnings(ground=ground, constraints=constraints, catalog=catalog)
        )
    compiled = compile_constraints(constraints, catalog)

    scipy_converged = False
    if verify_only:
        poses = _merge_poses(
            body_ids,
            solved={},
            fixed={ground: identity_pose(), **layout_poses},
        )
        residual_max = _residual_max(body_ids, compiled, poses)
        solve_ok = residual_max < RESIDUAL_TOL * 10.0
        nfev = 0
        solver_message = "verify_only (layout poses, no optimization)"
        solve_method = "verify_only"
        scipy_converged = True
        free_clusters = []
    else:
        (
            poses,
            residual_max,
            solve_ok,
            solver_message,
            nfev,
            scipy_converged,
            solve_method,
            free_clusters,
        ) = _solve_bucketed(
            body_ids=body_ids,
            solve_ids=solve_ids,
            compiled=compiled,
            catalog=catalog,
            ground=ground,
            constraints=constraints,
            rotation_modes=rotation_modes,
            yaw_axes=yaw_axes,
            layout_poses=layout_poses,
            layout_only_ids=layout_only_ids,
            initial_guess=validated["initial_guess"],
            use_bfs=spec_version >= 2,
            verbose=verbose,
            dof_policy=dof_policy,
        )

    solution_vector = pack_poses(body_ids, poses)
    residual_vector_fn = lambda vector: _residual_vector(
        body_ids, compiled, unpack_poses(body_ids, vector)
    )
    jacobian = numeric_jacobian(
        residual_vector_fn,
        solution_vector,
        body_ids=body_ids,
        compiled=compiled,
        poses=poses,
    )
    dof_summary = summarize_dof(jacobian, body_ids=body_ids)

    jacobian_verify: dict[str, Any] | None = None
    if verify_jacobian:
        from .jacobian import verify_analytic_jacobian

        jacobian_verify = verify_analytic_jacobian(
            body_ids,
            compiled,
            poses,
            numeric_fn=residual_vector_fn,
            vector=solution_vector,
        )
        if verbose:
            print(f"jacobian verify: {jacobian_verify}")

    mating_free: list[dict[str, Any]] = []
    gauge_free: list[dict[str, Any]] = []
    assumed_locks: list[dict[str, Any]] = []
    unmatched_gauge: list[dict[str, Any]] = []
    witness_branches: dict[str, Any] = {}
    suggested: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    ot = float(dof_policy.get("overconstrained_threshold", 1e-4))

    if spec_version == 2:
        classified = classify_free_directions(
            jacobian,
            body_ids=body_ids,
            compiled=compiled,
            poses=poses,
            ground=ground,
            constraints=constraints,
        )
        mating_free = classified.get("mating_free", [])
        gauge_free = classified.get("gauge_free", [])

        if str(dof_policy.get("gauge_policy")) == "auto_lock" and gauge_free:
            extra, assumed_locks, unmatched_gauge = apply_gauge_auto_lock(
                gauge_free,
                ground=ground,
                constraints=constraints,
            )
            if extra:
                constraints = [*constraints, *extra]
                compiled = compile_constraints(constraints, catalog)
                poses, residual_max, solve_ok, solver_message, nfev, scipy_converged = (
                    _run_scipy_solve(
                        body_ids=body_ids,
                        solve_ids=solve_ids,
                        compiled=compiled,
                        catalog=catalog,
                        ground=ground,
                        constraints=constraints,
                        initial_guess=validated["initial_guess"],
                        layout_poses=layout_poses,
                        initial_poses=poses,
                        use_bfs=spec_version >= 2,
                        verbose=verbose,
                    )
                )
                solve_method = "scipy+auto_lock"
                solution_vector = pack_poses(body_ids, poses)
                jacobian = numeric_jacobian(
                    lambda vector: _residual_vector(
                        body_ids, compiled, unpack_poses(body_ids, vector)
                    ),
                    solution_vector,
                    body_ids=body_ids,
                    compiled=compiled,
                    poses=poses,
                )
                dof_summary = summarize_dof(jacobian, body_ids=body_ids)
                classified = classify_free_directions(
                    jacobian,
                    body_ids=body_ids,
                    compiled=compiled,
                    poses=poses,
                    ground=ground,
                    constraints=constraints,
                )
                mating_free = classified.get("mating_free", [])
                gauge_free = classified.get("gauge_free", [])
                if gauge_free:
                    unmatched_gauge = [
                        entry
                        for entry in unmatched_gauge
                        if str(entry.get("body", ""))
                        in {str(item.get("body", "")) for item in gauge_free}
                    ]
                else:
                    unmatched_gauge = []

        if str(dof_policy.get("gauge_policy")) == "enumerate" and gauge_free:
            def _witness_trial(extra_constraints: list[dict[str, Any]]) -> dict[str, BodyPose] | None:
                return _solve_with_extra_constraints(
                    validated=validated,
                    extra_constraints=extra_constraints,
                    initial_poses=poses,
                    layout_poses=layout_poses,
                    layout_only_ids=layout_only_ids,
                    solve_ids=solve_ids,
                    spec_version=spec_version,
                    verbose=verbose,
                )

            witness_branches, witness_warnings = enumerate_witnesses(
                gauge_free,
                current_poses=poses,
                ground=ground,
                constraints=constraints,
                trial_solve=_witness_trial,
                residual_tol=RESIDUAL_TOL * 10.0,
            )
            warnings.extend(witness_warnings)

        suggested = suggest_relations(
            mating_free,
            constraints=constraints,
            ground=ground,
            gauge_free=gauge_free,
        )
        rotation_issues = gauge_free_to_rotation_issues(gauge_free)
        if not rotation_issues and assumed_locks:
            rotation_issues = []
    else:
        rotation_issues = rotation_audit_issues(
            ground=ground,
            poses=poses,
            constraints=constraints,
            catalog=catalog,
        )
        if rotation_issues:
            for issue in rotation_issues[:3]:
                warnings.append(issue.get("hint", issue.get("reason", "rotation audit issue")))

    if (
        scipy_converged
        and residual_max > ot
        and solve_method not in {"verify_only", "analytic"}
    ):
        def _subset_solve(exclude_id: str) -> dict[str, BodyPose]:
            return _solve_without_constraint(
                validated=validated,
                exclude_constraint_id=exclude_id,
                initial_poses=poses,
                layout_poses=layout_poses,
                layout_only_ids=layout_only_ids,
                solve_ids=solve_ids,
                spec_version=spec_version,
                verbose=verbose,
            )

        mus_conflicts, mus_warnings = find_mus(
            compiled=compiled,
            raw_constraints=constraints,
            poses=poses,
            threshold=ot,
            subset_solve=_subset_solve,
        )
        conflicts.extend(mus_conflicts)
        warnings.extend(mus_warnings)

    if spec_version == 2:
        status, diag_warnings = derive_status_v2(
            solve_ok=solve_ok,
            residual_max=residual_max,
            mating_free=mating_free,
            gauge_free=gauge_free,
            assumed_locks=assumed_locks,
            unmatched_gauge=unmatched_gauge,
            dof_policy=dof_policy,
            conflicts=conflicts,
            witness_branches=witness_branches,
        )
        warnings.extend(diag_warnings)
    else:
        status = "ok"
        if conflicts and not conflicts[0].get("hint"):
            status = "overconstrained"
        elif not solve_ok:
            status = "solve_failed"
        else:
            free_entries = dof_summary.get("free", [])
            bodies_with_trans_free = {
                str(entry.get("body")) for entry in free_entries if entry.get("trans")
            }
            has_rotation_issue = bool(rotation_issues)
            if has_rotation_issue:
                status = "underconstrained"
            elif len(bodies_with_trans_free) >= 2:
                status = "underconstrained"
            elif any("likely_underconstrained" in warning for warning in warnings):
                status = "underconstrained"
            elif any("missing_in_plane_axis_lock" in warning for warning in warnings):
                status = "underconstrained"

    llm_report = build_llm_report(
        status=status,
        ground=ground,
        solve_ok=solve_ok,
        residual_max=residual_max,
        dof_summary=dof_summary,
        warnings=warnings,
        conflicts=conflicts,
        rotation_issues=rotation_issues,
        schema_version=spec_version,
        mating_free=mating_free if spec_version == 2 else None,
        gauge_free=gauge_free if spec_version == 2 else None,
        assumed_locks=assumed_locks if spec_version == 2 else None,
        witness_branches=witness_branches if spec_version == 2 else None,
        suggested_relations=suggested if spec_version == 2 else None,
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
        "solve_method": solve_method,
    }
    if len(free_clusters) > 1:
        output["free_clusters"] = free_clusters
    if jacobian_verify is not None:
        output["jacobian_verify"] = jacobian_verify

    if (
        status not in {"ok", "underconstrained", "ok_assumed", "overconstrained"}
        and not solve_ok
        and solve_method != "verify_only"
    ):
        raise ConstraintSolveError(
            f"constraint solve failed: {solver_message}",
            report=llm_report,
        )

    return output


def _solve_bucketed(
    *,
    body_ids: tuple[str, ...],
    solve_ids: tuple[str, ...],
    compiled: list[CompiledConstraint],
    catalog,
    ground: str,
    constraints: list[dict[str, Any]],
    rotation_modes: dict[str, str],
    yaw_axes: dict[str, str],
    layout_poses: dict[str, BodyPose],
    layout_only_ids: frozenset[str],
    initial_guess: dict[str, object],
    use_bfs: bool,
    verbose: bool,
    dof_policy: dict[str, Any],
) -> tuple[dict[str, BodyPose], float, bool, str, int, bool, str, list[dict[str, Any]]]:
    """Ground → layout → analytic → yaw 4D → free 7D solve pipeline (P2e)."""
    buckets = bucket_bodies(body_ids, rotation_modes, ground=ground)
    yaw_ids = tuple(sorted(bid for bid in buckets["yaw"] if bid not in layout_only_ids))
    free_ids = tuple(sorted(bid for bid in buckets["free"] if bid not in layout_only_ids))

    poses: dict[str, BodyPose] = {ground: identity_pose(), **layout_poses}
    analytic_poses = try_place_analytic_bodies(
        ground=ground,
        body_ids=body_ids,
        catalog=catalog,
        constraints=constraints,
        rotation_modes=rotation_modes,
        base_poses=poses,
    )
    if analytic_poses is not None:
        poses = analytic_poses

    nfev = 0
    messages: list[str] = []
    scipy_converged = True
    solve_method = "analytic"
    free_clusters: list[dict[str, Any]] = []
    free_subcluster_min = int(dof_policy.get("free_subcluster_min_bodies", 2))

    def residual_from_poses(poses_dict: dict[str, BodyPose]) -> np.ndarray:
        merged = dict(poses_dict)
        if ground not in merged:
            merged[ground] = identity_pose()
        return _residual_vector(body_ids, compiled, merged)

    if yaw_ids:
        yaw_seed = _scipy_seed_poses(
            body_ids=body_ids,
            solve_ids=yaw_ids,
            ground=ground,
            catalog=catalog,
            constraints=constraints,
            initial_guess=initial_guess,
            layout_poses=layout_poses,
            initial_poses=poses,
            use_bfs=use_bfs,
        )
        fixed_for_yaw = {body_id: poses[body_id] for body_id in body_ids if body_id not in yaw_ids}
        yaw_solved, yaw_residual, yaw_ok, yaw_msg, yaw_nfev = solve_yaw_bucket(
            yaw_ids,
            body_ids=body_ids,
            compiled=compiled,
            residual_vector_fn=residual_from_poses,
            fixed_poses=fixed_for_yaw,
            yaw_axes=yaw_axes,
            seed_poses=yaw_seed,
            run_optimizer=_run_optimizer,
            residual_tol=RESIDUAL_TOL * 10.0,
        )
        poses.update(yaw_solved)
        nfev += yaw_nfev
        messages.append(yaw_msg)
        scipy_converged = scipy_converged and yaw_ok
        solve_method = "yaw4d+analytic" if analytic_poses else "yaw4d"
        if verbose:
            print(f"yaw bucket residual max={yaw_residual:.6g} ({yaw_msg})")

    if free_ids:
        free_seed = _scipy_seed_poses(
            body_ids=body_ids,
            solve_ids=free_ids,
            ground=ground,
            catalog=catalog,
            constraints=constraints,
            initial_guess=initial_guess,
            layout_poses=layout_poses,
            initial_poses=poses,
            use_bfs=use_bfs,
        )
        poses.update(free_seed)
        scipy_kwargs = {
            "body_ids": body_ids,
            "compiled": compiled,
            "catalog": catalog,
            "ground": ground,
            "constraints": constraints,
            "initial_guess": initial_guess,
            "layout_poses": layout_poses,
            "initial_poses": poses,
            "use_bfs": use_bfs,
            "verbose": verbose,
        }

        def _scipy_solve_cluster(*, solve_ids: tuple[str, ...], **kwargs) -> tuple:
            merged = {**scipy_kwargs, **kwargs}
            return _run_scipy_solve(solve_ids=solve_ids, **merged)

        (
            poses,
            free_residual,
            free_ok,
            free_msg,
            free_nfev,
            free_conv,
            free_clusters,
            used_free_dr,
        ) = solve_free_bucket(
            free_ids,
            scipy_solve_fn=_scipy_solve_cluster,
            scipy_solve_kwargs=scipy_kwargs,
            min_subcluster_bodies=free_subcluster_min,
        )
        nfev += free_nfev
        messages.append(free_msg)
        scipy_converged = free_conv
        if used_free_dr:
            solve_method = (
                f"{solve_method}+free_dr" if solve_method != "analytic" else "free_dr"
            )
        else:
            solve_method = "scipy" if not yaw_ids else f"{solve_method}+free"
        if verbose:
            print(f"free bucket residual max={free_residual:.6g} clusters={len(free_clusters)}")

    if not yaw_ids and not free_ids:
        if analytic_poses is None and buckets["analytic"]:
            poses, residual_max, solve_ok, solver_message, nfev, scipy_converged = (
                _run_scipy_solve(
                    body_ids=body_ids,
                    solve_ids=solve_ids,
                    compiled=compiled,
                    catalog=catalog,
                    ground=ground,
                    constraints=constraints,
                    initial_guess=initial_guess,
                    layout_poses=layout_poses,
                    use_bfs=use_bfs,
                    verbose=verbose,
                )
            )
            return (
                poses,
                residual_max,
                solve_ok,
                solver_message,
                nfev,
                scipy_converged,
                "scipy",
                [],
            )
        if analytic_poses is None and not buckets["analytic"]:
            solver_message = "fixed poses (ground/layout)"
        else:
            solver_message = "analytic placement (axis_aligned)"
    elif not free_ids:
        solver_message = "; ".join(messages) if messages else solve_method
    else:
        solver_message = "; ".join(messages)

    residual_max = _residual_max(body_ids, compiled, poses)
    solve_ok = residual_max < RESIDUAL_TOL * 10.0 or (
        scipy_converged and residual_max < 1e-4
    )
    return (
        poses,
        residual_max,
        solve_ok,
        solver_message,
        nfev,
        scipy_converged,
        solve_method,
        free_clusters,
    )


def _solve_with_extra_constraints(
    *,
    validated: dict[str, Any],
    extra_constraints: list[dict[str, Any]],
    initial_poses: dict[str, BodyPose],
    layout_poses: dict[str, BodyPose],
    layout_only_ids: frozenset[str],
    solve_ids: tuple[str, ...],
    spec_version: int,
    verbose: bool,
) -> dict[str, BodyPose] | None:
    """Re-solve with additional constraints (witness branch trial, P2d)."""
    ground = validated["ground"]
    catalog = validated["catalog"]
    body_ids = tuple(sorted(catalog.keys()))
    constraints = [*expand_constraints(validated["constraints"]), *extra_constraints]
    constraints = _with_ground_fix_if_needed(constraints, ground=ground)
    compiled = compile_constraints(constraints, catalog)
    trial_poses, residual_max, solve_ok, _, _, _ = _run_scipy_solve(
        body_ids=body_ids,
        solve_ids=solve_ids,
        compiled=compiled,
        catalog=catalog,
        ground=ground,
        constraints=constraints,
        initial_guess=validated["initial_guess"],
        layout_poses=layout_poses,
        initial_poses=initial_poses,
        use_bfs=spec_version >= 2,
        verbose=verbose,
    )
    if not solve_ok or residual_max >= RESIDUAL_TOL * 10.0:
        return None
    return trial_poses


def _solve_without_constraint(
    *,
    validated: dict[str, Any],
    exclude_constraint_id: str,
    initial_poses: dict[str, BodyPose],
    layout_poses: dict[str, BodyPose],
    layout_only_ids: frozenset[str],
    solve_ids: tuple[str, ...],
    spec_version: int,
    verbose: bool,
) -> dict[str, BodyPose]:
    """Re-solve while omitting one constraint (used by MUS delta-debugging)."""
    ground = validated["ground"]
    catalog = validated["catalog"]
    body_ids = tuple(sorted(catalog.keys()))
    constraints = [
        constraint
        for constraint in expand_constraints(validated["constraints"])
        if str(constraint.get("id")) != exclude_constraint_id
    ]
    constraints = _with_ground_fix_if_needed(constraints, ground=ground)
    compiled = compile_constraints(constraints, catalog)
    poses, _, _, _, _, _ = _run_scipy_solve(
        body_ids=body_ids,
        solve_ids=solve_ids,
        compiled=compiled,
        catalog=catalog,
        ground=ground,
        constraints=constraints,
        initial_guess=validated["initial_guess"],
        layout_poses=layout_poses,
        initial_poses=initial_poses,
        use_bfs=spec_version >= 2,
        verbose=verbose,
    )
    return poses


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
        poses[body_id] = BodyPose(
            (0.0, 0.0, ground_top + z_shift + 5.0 + offset),
            (0.0, 0.0, 0.0, 1.0),
        )
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
                (
                    float(raw_guess[3]),
                    float(raw_guess[4]),
                    float(raw_guess[5]),
                    float(raw_guess[6]),
                ),
            )
    return poses


def validate_only(
    spec: dict[str, Any],
    *,
    spec_path: str | None = None,
) -> dict[str, Any]:
    from pathlib import Path

    path = Path(spec_path).resolve() if spec_path is not None else None
    validated = validate_assembly_spec(spec, spec_path=path)
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
