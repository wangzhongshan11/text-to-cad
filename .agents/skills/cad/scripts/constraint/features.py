from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import numpy as np

from .primitives import (
    AxisFeature,
    FeatureKind,
    PlaneFeature,
    PointFeature,
    PrimitiveBody,
    build_primitive_body,
    plane_tangent_axes,
    resolve_feature_alias,
)
from .state import BodyPose, transform_local_direction, transform_local_point


@dataclass(frozen=True)
class FeatureRef:
    body_id: str
    feature_id: str


@dataclass(frozen=True)
class WorldPoint:
    position: np.ndarray


@dataclass(frozen=True)
class WorldAxis:
    origin: np.ndarray
    direction: np.ndarray


@dataclass(frozen=True)
class WorldPlane:
    origin: np.ndarray
    normal: np.ndarray

    def signed_distance(self, point: np.ndarray) -> float:
        normal = self.normal / (np.linalg.norm(self.normal) + 1e-15)
        return float(np.dot(point - self.origin, normal))

    def tangent_axes(self) -> tuple[np.ndarray, np.ndarray]:
        normal = self.normal / (np.linalg.norm(self.normal) + 1e-15)
        return plane_tangent_axes(normal)


def parse_feature_ref(text: str) -> FeatureRef:
    if "." not in text:
        raise ValueError(f"feature ref must be body.feature, got {text!r}")
    body_id, feature_id = text.split(".", 1)
    body_id = body_id.strip()
    feature_id = feature_id.strip()
    if not body_id or not feature_id:
        raise ValueError(f"invalid feature ref: {text!r}")
    return FeatureRef(body_id=body_id, feature_id=feature_id)


def build_body_catalog(bodies_spec: dict[str, dict[str, object]]) -> dict[str, PrimitiveBody]:
    catalog: dict[str, PrimitiveBody] = {}
    for body_id, body_spec in bodies_spec.items():
        primitive = str(body_spec.get("primitive", ""))
        catalog[body_id] = build_primitive_body(primitive, body_spec)
    return catalog


def _resolve_box_feature(
    primitive: PrimitiveBody,
    feature_id: str,
    expected_kind: FeatureKind,
) -> str:
    resolved = resolve_feature_alias(feature_id, primitive)
    if resolved in primitive.features:
        feature = primitive.features[resolved]
        if feature.kind == expected_kind:
            return resolved
    if primitive.primitive != "box":
        return resolved
    if expected_kind == FeatureKind.PLANE:
        plane_map = {
            "+x": "plane_px",
            "-x": "plane_nx",
            "+y": "plane_py",
            "-y": "plane_ny",
            "+z": "plane_pz",
            "-z": "plane_nz",
        }
        if feature_id in plane_map:
            return plane_map[feature_id]
    if expected_kind == FeatureKind.POINT and feature_id in {"+x", "-x", "+y", "-y", "+z", "-z"}:
        return feature_id
    if expected_kind == FeatureKind.AXIS and feature_id.startswith("edge_"):
        return feature_id
    return resolved


def get_feature(
    catalog: dict[str, PrimitiveBody],
    ref: FeatureRef,
    expected_kind: FeatureKind,
) -> Union[PointFeature, AxisFeature, PlaneFeature]:
    if ref.body_id not in catalog:
        raise KeyError(f"unknown body: {ref.body_id!r}")
    primitive = catalog[ref.body_id]
    feature_key = _resolve_box_feature(primitive, ref.feature_id, expected_kind)
    if feature_key not in primitive.features:
        raise KeyError(
            f"unknown feature {ref.feature_id!r} on body {ref.body_id!r} "
            f"(expected {expected_kind.value})"
        )
    feature = primitive.features[feature_key]
    if feature.kind != expected_kind:
        raise TypeError(
            f"feature {ref.body_id}.{ref.feature_id} is {feature.kind.value}, "
            f"expected {expected_kind.value}"
        )
    return feature


def world_point(
    catalog: dict[str, PrimitiveBody],
    poses: dict[str, BodyPose],
    ref: FeatureRef,
) -> WorldPoint:
    feature = get_feature(catalog, ref, FeatureKind.POINT)
    assert isinstance(feature, PointFeature)
    pose = poses[ref.body_id]
    return WorldPoint(transform_local_point(feature.position, pose.translation, pose.quaternion_xyzw))


def world_axis(
    catalog: dict[str, PrimitiveBody],
    poses: dict[str, BodyPose],
    ref: FeatureRef,
) -> WorldAxis:
    feature = get_feature(catalog, ref, FeatureKind.AXIS)
    assert isinstance(feature, AxisFeature)
    pose = poses[ref.body_id]
    origin = transform_local_point(feature.origin, pose.translation, pose.quaternion_xyzw)
    direction = transform_local_direction(feature.direction, pose.quaternion_xyzw)
    direction = direction / (np.linalg.norm(direction) + 1e-15)
    return WorldAxis(origin=origin, direction=direction)


def world_plane(
    catalog: dict[str, PrimitiveBody],
    poses: dict[str, BodyPose],
    ref: FeatureRef,
) -> WorldPlane:
    feature = get_feature(catalog, ref, FeatureKind.PLANE)
    assert isinstance(feature, PlaneFeature)
    pose = poses[ref.body_id]
    origin = transform_local_point(feature.origin, pose.translation, pose.quaternion_xyzw)
    normal = transform_local_direction(feature.normal, pose.quaternion_xyzw)
    normal = normal / (np.linalg.norm(normal) + 1e-15)
    return WorldPlane(origin=origin, normal=normal)
