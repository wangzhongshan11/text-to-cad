from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Union

import numpy as np


class FeatureKind(str, Enum):
    POINT = "point"
    AXIS = "axis"
    PLANE = "plane"


@dataclass(frozen=True)
class PointFeature:
    kind: Literal[FeatureKind.POINT] = FeatureKind.POINT
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class AxisFeature:
    kind: Literal[FeatureKind.AXIS] = FeatureKind.AXIS
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class PlaneFeature:
    kind: Literal[FeatureKind.PLANE] = FeatureKind.PLANE
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)


Feature = Union[PointFeature, AxisFeature, PlaneFeature]


@dataclass(frozen=True)
class PrimitiveBody:
    primitive: str
    parameters: dict[str, float]
    features: dict[str, Feature]


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    length = (x * x + y * y + z * z) ** 0.5
    if length <= 1e-15:
        return (0.0, 0.0, 1.0)
    return (x / length, y / length, z / length)


def build_box_primitive(size: tuple[float, float, float]) -> PrimitiveBody:
    lx, ly, lz = size
    hx, hy, hz = lx / 2.0, ly / 2.0, lz / 2.0
    features: dict[str, Feature] = {
        "center": PointFeature(position=(0.0, 0.0, 0.0)),
        "+x": PointFeature(position=(hx, 0.0, 0.0)),
        "-x": PointFeature(position=(-hx, 0.0, 0.0)),
        "+y": PointFeature(position=(0.0, hy, 0.0)),
        "-y": PointFeature(position=(0.0, -hy, 0.0)),
        "+z": PointFeature(position=(0.0, 0.0, hz)),
        "-z": PointFeature(position=(0.0, 0.0, -hz)),
        "axis_x": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0)),
        "axis_y": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0)),
        "axis_z": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0)),
        "plane_px": PlaneFeature(origin=(hx, 0.0, 0.0), normal=(1.0, 0.0, 0.0)),
        "plane_nx": PlaneFeature(origin=(-hx, 0.0, 0.0), normal=(-1.0, 0.0, 0.0)),
        "plane_py": PlaneFeature(origin=(0.0, hy, 0.0), normal=(0.0, 1.0, 0.0)),
        "plane_ny": PlaneFeature(origin=(0.0, -hy, 0.0), normal=(0.0, -1.0, 0.0)),
        "plane_pz": PlaneFeature(origin=(0.0, 0.0, hz), normal=(0.0, 0.0, 1.0)),
        "plane_nz": PlaneFeature(origin=(0.0, 0.0, -hz), normal=(0.0, 0.0, -1.0)),
        # 12 edges: intersection of two faces; direction along remaining axis
        "edge_px_pz": AxisFeature(origin=(hx, 0.0, hz), direction=(0.0, 1.0, 0.0)),
        "edge_px_nz": AxisFeature(origin=(hx, 0.0, -hz), direction=(0.0, 1.0, 0.0)),
        "edge_nx_pz": AxisFeature(origin=(-hx, 0.0, hz), direction=(0.0, 1.0, 0.0)),
        "edge_nx_nz": AxisFeature(origin=(-hx, 0.0, -hz), direction=(0.0, 1.0, 0.0)),
        "edge_py_pz": AxisFeature(origin=(0.0, hy, hz), direction=(1.0, 0.0, 0.0)),
        "edge_py_nz": AxisFeature(origin=(0.0, hy, -hz), direction=(1.0, 0.0, 0.0)),
        "edge_ny_pz": AxisFeature(origin=(0.0, -hy, hz), direction=(1.0, 0.0, 0.0)),
        "edge_ny_nz": AxisFeature(origin=(0.0, -hy, -hz), direction=(1.0, 0.0, 0.0)),
        "edge_px_py": AxisFeature(origin=(hx, hy, 0.0), direction=(0.0, 0.0, 1.0)),
        "edge_px_ny": AxisFeature(origin=(hx, -hy, 0.0), direction=(0.0, 0.0, 1.0)),
        "edge_nx_py": AxisFeature(origin=(-hx, hy, 0.0), direction=(0.0, 0.0, 1.0)),
        "edge_nx_ny": AxisFeature(origin=(-hx, -hy, 0.0), direction=(0.0, 0.0, 1.0)),
    }
    # Aliases for plane/point shorthand used in JSON (+x plane vs +x point)
    features["+x_plane"] = features["plane_px"]
    features["-x_plane"] = features["plane_nx"]
    features["+y_plane"] = features["plane_py"]
    features["-y_plane"] = features["plane_ny"]
    features["+z_plane"] = features["plane_pz"]
    features["-z_plane"] = features["plane_nz"]
    return PrimitiveBody(
        primitive="box",
        parameters={"lx": lx, "ly": ly, "lz": lz},
        features=features,
    )


def build_cylinder_primitive(*, radius: float, height: float) -> PrimitiveBody:
    hz = height / 2.0
    features: dict[str, Feature] = {
        "center": PointFeature(position=(0.0, 0.0, 0.0)),
        "top": PointFeature(position=(0.0, 0.0, hz)),
        "bottom": PointFeature(position=(0.0, 0.0, -hz)),
        "axis": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0)),
        "axis_x": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0)),
        "axis_y": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0)),
        "axis_z": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0)),
        "top_plane": PlaneFeature(origin=(0.0, 0.0, hz), normal=(0.0, 0.0, 1.0)),
        "bottom_plane": PlaneFeature(origin=(0.0, 0.0, -hz), normal=(0.0, 0.0, -1.0)),
        "+z": PlaneFeature(origin=(0.0, 0.0, hz), normal=(0.0, 0.0, 1.0)),
        "-z": PlaneFeature(origin=(0.0, 0.0, -hz), normal=(0.0, 0.0, -1.0)),
    }
    return PrimitiveBody(
        primitive="cylinder",
        parameters={"radius": radius, "height": height},
        features=features,
    )


def build_sphere_primitive(*, radius: float) -> PrimitiveBody:
    features: dict[str, Feature] = {
        "center": PointFeature(position=(0.0, 0.0, 0.0)),
        "equator": PlaneFeature(origin=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0)),
        "axis_x": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0)),
        "axis_y": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0)),
        "axis_z": AxisFeature(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0)),
    }
    return PrimitiveBody(
        primitive="sphere",
        parameters={"radius": radius},
        features=features,
    )


def build_primitive_body(primitive: str, spec: dict[str, object]) -> PrimitiveBody:
    if primitive == "box":
        size = spec.get("size")
        if not isinstance(size, (list, tuple)) or len(size) != 3:
            raise ValueError("box requires size: [lx, ly, lz]")
        return build_box_primitive((float(size[0]), float(size[1]), float(size[2])))
    if primitive == "cylinder":
        radius = float(spec.get("radius", spec.get("r", 0.0)))
        height = float(spec.get("height", spec.get("h", 0.0)))
        if radius <= 0 or height <= 0:
            raise ValueError("cylinder requires positive radius and height")
        return build_cylinder_primitive(radius=radius, height=height)
    if primitive == "sphere":
        radius = float(spec.get("radius", spec.get("r", 0.0)))
        if radius <= 0:
            raise ValueError("sphere requires positive radius")
        return build_sphere_primitive(radius=radius)
    raise ValueError(f"unsupported primitive: {primitive!r}")


def list_feature_ids(primitive: PrimitiveBody) -> tuple[str, ...]:
    return tuple(sorted(primitive.features))


def resolve_feature_alias(feature_id: str, primitive: PrimitiveBody) -> str:
    """Map shorthand like +z on box to plane or point."""
    if feature_id in primitive.features:
        return feature_id
    if primitive.primitive == "box":
        plane_alias = {
            "+x": "plane_px",
            "-x": "plane_nx",
            "+y": "plane_py",
            "-y": "plane_ny",
            "+z": "plane_pz",
            "-z": "plane_nz",
        }
        if feature_id in plane_alias and plane_alias[feature_id] in primitive.features:
            return plane_alias[feature_id]
    return feature_id


def plane_tangent_axes(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return in-plane e1 (world +X projected) and e2 = normal x e1."""
    normal = np.asarray(normal, dtype=float)
    normal = normal / (np.linalg.norm(normal) + 1e-15)
    reference = np.array([1.0, 0.0, 0.0], dtype=float)
    if abs(float(np.dot(normal, reference))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0], dtype=float)
    u = reference - normal * float(np.dot(reference, normal))
    u = u / (np.linalg.norm(u) + 1e-15)
    v = np.cross(normal, u)
    v = v / (np.linalg.norm(v) + 1e-15)
    return u, v
