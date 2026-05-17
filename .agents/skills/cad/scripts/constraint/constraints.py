from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .features import (
    FeatureRef,
    parse_feature_ref,
    world_axis,
    world_plane,
    world_point,
)
from .primitives import PrimitiveBody
from .state import BodyPose, identity_pose, quaternion_residual


ResidualFn = Callable[[dict[str, BodyPose]], list[float]]


@dataclass(frozen=True)
class CompiledConstraint:
    constraint_id: str
    constraint_type: str
    residual_fn: ResidualFn
    body_ids: tuple[str, ...]


def _direction_parallel_residual(d1: np.ndarray, d2: np.ndarray, *, opposed: bool = False) -> list[float]:
    d1 = d1 / (np.linalg.norm(d1) + 1e-15)
    d2 = d2 / (np.linalg.norm(d2) + 1e-15)
    if opposed:
        target = -d2
    else:
        target = d2
    return [float(d1[0] - target[0]), float(d1[1] - target[1]), float(d1[2] - target[2])]


def _point_line_distance_residual(point: np.ndarray, axis_origin: np.ndarray, axis_dir: np.ndarray) -> list[float]:
    axis_dir = axis_dir / (np.linalg.norm(axis_dir) + 1e-15)
    delta = point - axis_origin
    along = float(np.dot(delta, axis_dir)) * axis_dir
    perpendicular = delta - along
    return [float(perpendicular[0]), float(perpendicular[1]), float(perpendicular[2])]


def compile_constraints(
    constraints: list[dict[str, Any]],
    catalog: dict[str, PrimitiveBody],
) -> list[CompiledConstraint]:
    compiled: list[CompiledConstraint] = []
    for constraint in constraints:
        compiled.append(_compile_one(constraint, catalog))
    return compiled


def _compile_one(constraint: dict[str, Any], catalog: dict[str, PrimitiveBody]) -> CompiledConstraint:
    constraint_id = str(constraint.get("id", "c"))
    constraint_type = str(constraint["type"])

    if constraint_type == "fix":
        body_id = str(constraint.get("body", constraint.get("a", "")))
        target = constraint.get("pose", "identity")

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            pose = poses[body_id]
            target_pose = identity_pose()
            values: list[float] = []
            values.extend(float(pose.translation[index] - target_pose.translation[index]) for index in range(3))
            values.extend(
                float(pose.quaternion_xyzw[index] - target_pose.quaternion_xyzw[index]) for index in range(4)
            )
            return values

        return CompiledConstraint(constraint_id, constraint_type, residual_fn, (body_id,))

    if constraint_type == "point_coincident":
        ref_a = parse_feature_ref(str(constraint["a"]))
        ref_b = parse_feature_ref(str(constraint["b"]))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            pa = world_point(catalog, poses, ref_a).position
            pb = world_point(catalog, poses, ref_b).position
            delta = pa - pb
            return [float(delta[0]), float(delta[1]), float(delta[2])]

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (ref_a.body_id, ref_b.body_id),
        )

    if constraint_type == "plane_coincident":
        ref_a = parse_feature_ref(str(constraint["a"]))
        ref_b = parse_feature_ref(str(constraint["b"]))
        opposed = bool(constraint.get("opposed", constraint.get("contact", False)))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            plane_a = world_plane(catalog, poses, ref_a)
            plane_b = world_plane(catalog, poses, ref_b)
            normal_residual = _direction_parallel_residual(plane_a.normal, plane_b.normal, opposed=opposed)
            coplanar = float(np.dot(plane_a.origin - plane_b.origin, plane_b.normal))
            return normal_residual + [coplanar]

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (ref_a.body_id, ref_b.body_id),
        )

    if constraint_type == "axis_coaxial":
        ref_a = parse_feature_ref(str(constraint["a"]))
        ref_b = parse_feature_ref(str(constraint["b"]))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            axis_a = world_axis(catalog, poses, ref_a)
            axis_b = world_axis(catalog, poses, ref_b)
            parallel = _direction_parallel_residual(axis_a.direction, axis_b.direction, opposed=False)
            delta = axis_a.origin - axis_b.origin
            cross = np.cross(axis_a.direction, axis_b.direction)
            cross_norm = float(np.linalg.norm(cross))
            if cross_norm < 1e-8:
                along = axis_b.direction / (np.linalg.norm(axis_b.direction) + 1e-15)
                perpendicular = delta - along * float(np.dot(delta, along))
                line_distance = float(np.linalg.norm(perpendicular))
            else:
                line_distance = float(np.linalg.norm(np.cross(delta, cross)) / cross_norm)
            return parallel + [line_distance]

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (ref_a.body_id, ref_b.body_id),
        )

    if constraint_type == "axis_parallel":
        ref_a = parse_feature_ref(str(constraint["a"]))
        ref_b = parse_feature_ref(str(constraint["b"]))
        opposed = bool(constraint.get("opposed", False))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            axis_a = world_axis(catalog, poses, ref_a)
            axis_b = world_axis(catalog, poses, ref_b)
            return _direction_parallel_residual(axis_a.direction, axis_b.direction, opposed=opposed)

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (ref_a.body_id, ref_b.body_id),
        )

    if constraint_type == "plane_distance":
        ref_a = parse_feature_ref(str(constraint["a"]))
        ref_b = parse_feature_ref(str(constraint["b"]))
        distance = float(constraint.get("distance", constraint.get("d", 0.0)))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            plane_a = world_plane(catalog, poses, ref_a)
            plane_b = world_plane(catalog, poses, ref_b)
            signed = plane_b.signed_distance(plane_a.origin)
            return [signed - distance]

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (ref_a.body_id, ref_b.body_id),
        )

    if constraint_type == "point_plane_offset":
        point_ref = parse_feature_ref(str(constraint.get("point", constraint.get("a", ""))))
        plane_ref = parse_feature_ref(str(constraint.get("plane", constraint.get("b", ""))))
        in_plane = constraint.get("in_plane")
        if in_plane is not None:
            axis = str(in_plane).lower()
            value = float(constraint.get("value", 0.0))

            def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
                point = world_point(catalog, poses, point_ref).position
                plane = world_plane(catalog, poses, plane_ref)
                u, v = plane.tangent_axes()
                delta = point - plane.origin
                if axis == "x":
                    tangent = u
                elif axis == "y":
                    tangent = v
                else:
                    raise ValueError(f"in_plane must be x or y, got {axis!r}")
                return [float(np.dot(delta, tangent) - value)]

            return CompiledConstraint(
                constraint_id,
                constraint_type,
                residual_fn,
                (point_ref.body_id, plane_ref.body_id),
            )

        offset = float(constraint.get("offset", constraint.get("distance", constraint.get("d", 0.0))))

        def residual_fn(poses: dict[str, BodyPose]) -> list[float]:
            point = world_point(catalog, poses, point_ref).position
            plane = world_plane(catalog, poses, plane_ref)
            return [plane.signed_distance(point) - offset]

        return CompiledConstraint(
            constraint_id,
            constraint_type,
            residual_fn,
            (point_ref.body_id, plane_ref.body_id),
        )

    raise ValueError(f"unsupported constraint type: {constraint_type!r}")
