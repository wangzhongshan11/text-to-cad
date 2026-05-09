from _typeshed import Incomplete
from build123d.build_common import Builder as Builder, LocationList as LocationList, WorkplaneList as WorkplaneList, flatten_sequence as flatten_sequence, validate_inputs as validate_inputs
from build123d.build_enums import GeomType as GeomType, Keep as Keep, Kind as Kind, Mode as Mode, Side as Side, Transition as Transition
from build123d.build_line import BuildLine as BuildLine
from build123d.build_part import BuildPart as BuildPart
from build123d.build_sketch import BuildSketch as BuildSketch
from build123d.geometry import Axis as Axis, Location as Location, Matrix as Matrix, Plane as Plane, Rotation as Rotation, RotationLike as RotationLike, Vector as Vector, VectorLike as VectorLike
from build123d.objects_curve import BaseLineObject as BaseLineObject
from build123d.objects_part import BasePartObject as BasePartObject
from build123d.objects_sketch import BaseSketchObject as BaseSketchObject
from build123d.topology import Compound as Compound, Curve as Curve, Edge as Edge, Face as Face, GroupBy as GroupBy, Part as Part, Shape as Shape, ShapeList as ShapeList, Shell as Shell, Sketch as Sketch, Solid as Solid, Vertex as Vertex, Wire as Wire, isclose_b as isclose_b
from collections.abc import Iterable
from typing import TypeAlias

logger: Incomplete
AddType: TypeAlias = Edge | Wire | Face | Solid | Compound | Builder

def add(objects: AddType | Iterable[AddType], rotation: float | RotationLike | None = None, clean: bool = True, mode: Mode = ...) -> Compound: ...
def bounding_box(objects: Shape | Iterable[Shape] | None = None, mode: Mode = ...) -> Sketch | Part: ...
ChamferFilletType: TypeAlias = Edge | Vertex

def chamfer(objects: ChamferFilletType | Iterable[ChamferFilletType], length: float, length2: float | None = None, angle: float | None = None, reference: Edge | Face | None = None) -> Sketch | Part: ...
def fillet(objects: ChamferFilletType | Iterable[ChamferFilletType], radius: float) -> Sketch | Part | Curve: ...
MirrorType: TypeAlias = Edge | Wire | Face | Compound | Curve | Sketch | Part

def mirror(objects: MirrorType | Iterable[MirrorType] | None = None, about: Plane = ..., mode: Mode = ...) -> Curve | Sketch | Part | Compound: ...
OffsetType: TypeAlias = Edge | Face | Solid | Compound

def offset(objects: OffsetType | Iterable[OffsetType] | None = None, amount: float = 0, openings: Face | list[Face] | None = None, kind: Kind = ..., side: Side = ..., closed: bool = True, min_edge_length: float | None = None, mode: Mode = ...) -> Curve | Sketch | Part | Compound: ...
ProjectType: TypeAlias = Edge | Face | Wire | Vector | Vertex

def project(objects: ProjectType | Iterable[ProjectType] | None = None, workplane: Plane | None = None, target: Solid | Compound | Part | None = None, mode: Mode = ...) -> Curve | Sketch | Compound | ShapeList[Vector]: ...
def scale(objects: Shape | Iterable[Shape] | None = None, by: float | tuple[float, float, float] = 1, mode: Mode = ...) -> Curve | Sketch | Part | Compound: ...
SplitType: TypeAlias = Edge | Wire | Face | Solid

def split(objects: SplitType | Iterable[SplitType] | None = None, bisect_by: Plane | Face | Shell = ..., keep: Keep = ..., mode: Mode = ...): ...
SweepType: TypeAlias = Compound | Edge | Wire | Face | Solid

def sweep(sections: SweepType | Iterable[SweepType] | None = None, path: Curve | Edge | Wire | Iterable[Edge] | None = None, multisection: bool = False, is_frenet: bool = False, transition: Transition = ..., normal: VectorLike | None = None, binormal: Edge | Wire | None = None, clean: bool = True, mode: Mode = ...) -> Part | Sketch: ...
