import abc
import types
from _typeshed import Incomplete
from abc import ABC
from build123d.build_enums import Align as Align, Mode as Mode, Select as Select, Unit as Unit
from build123d.geometry import Axis as Axis, Location as Location, Plane as Plane, Vector as Vector, VectorLike as VectorLike, to_align_offset as to_align_offset
from build123d.topology import Compound as Compound, Curve as Curve, Edge as Edge, Face as Face, Joint as Joint, Part as Part, Shape as Shape, ShapeList as ShapeList, Sketch as Sketch, Solid as Solid, Vertex as Vertex, Wire as Wire, new_edges as new_edges, tuplify as tuplify
from collections.abc import Callable as Callable, Iterable
from typing import Any, Generic, Protocol, TypeVar, overload
from typing_extensions import Self

logger: Incomplete
MC: float
MM: int
CM: Incomplete
M: Incomplete
IN: Incomplete
FT: Incomplete
THOU: Incomplete
UNITS_PER_METER: Incomplete
G: int
KG: Incomplete
LB: Incomplete
T = TypeVar('T', Any, list[Any])

def flatten_sequence(*obj: T) -> ShapeList[Any]: ...

operations_apply_to: Incomplete
B = TypeVar('B', bound='Builder')
ShapeT = TypeVar('ShapeT', bound=Shape)

class Builder(ABC, Generic[ShapeT], metaclass=abc.ABCMeta):
    mode: Incomplete
    workplanes: Incomplete
    parent_frame: Incomplete
    builder_parent: Incomplete
    lasts: dict
    workplanes_context: Incomplete
    exit_workplanes: list[Plane]
    obj_before: Shape | None
    to_combine: list[Shape]
    def __init__(self, *workplanes: Face | Plane | Location, mode: Mode = ...) -> None: ...
    @property
    def max_dimension(self) -> float: ...
    @property
    def new_edges(self) -> ShapeList[Edge]: ...
    def __enter__(self): ...
    def __exit__(self, exception_type: type[BaseException] | None, exception_value: BaseException | None, traceback: types.TracebackType | None) -> None: ...
    def vertices(self, select: Select = ...) -> ShapeList[Vertex]: ...
    def vertex(self, select: Select = ...) -> Vertex: ...
    def edges(self, select: Select = ...) -> ShapeList[Edge]: ...
    def edge(self, select: Select = ...) -> Edge: ...
    def wires(self, select: Select = ...) -> ShapeList[Wire]: ...
    def wire(self, select: Select = ...) -> Wire: ...
    def faces(self, select: Select = ...) -> ShapeList[Face]: ...
    def face(self, select: Select = ...) -> Face: ...
    def solids(self, select: Select = ...) -> ShapeList[Solid]: ...
    def solid(self, select: Select = ...) -> Solid: ...
    def validate_inputs(self, validating_class, objects: Shape | Iterable[Shape] | None = None): ...
    def __add__(self, _other) -> Self: ...
    def __sub__(self, _other) -> Self: ...
    def __and__(self, _other) -> Self: ...
    def __getattr__(self, name) -> None: ...

def validate_inputs(context: Builder | None, validating_class, objects: Iterable[Shape] | None = None): ...

class LocationList:
    @property
    def locations(self) -> list[Location]: ...
    local_locations: Incomplete
    location_index: int
    plane_index: int
    iter_loc: Incomplete
    def __init__(self, locations: list[Location]) -> None: ...
    def __enter__(self): ...
    def __exit__(self, exception_type: type[BaseException] | None, exception_value: BaseException | None, traceback: types.TracebackType | None) -> None: ...
    def __iter__(self): ...
    def __next__(self): ...
    def __mul__(self, shape: Shape) -> list[Shape]: ...

class HexLocations(LocationList):
    radius: Incomplete
    apothem: Incomplete
    diagonal: Incomplete
    x_count: Incomplete
    y_count: Incomplete
    major_radius: Incomplete
    align: Incomplete
    local_locations: Incomplete
    def __init__(self, radius: float, x_count: int, y_count: int, major_radius: bool = False, align: Align | tuple[Align, Align] = ...) -> None: ...

class PolarLocations(LocationList):
    local_locations: Incomplete
    def __init__(self, radius: float, count: int, start_angle: float = 0.0, angular_range: float = 360.0, rotate: bool = True, endpoint: bool = False) -> None: ...

class Locations(LocationList):
    local_locations: Incomplete
    def __init__(self, *pts: VectorLike | Vertex | Location | Face | Plane | Axis | Iterable[VectorLike | Vertex | Location | Face | Plane | Axis]) -> None: ...

class GridLocations(LocationList):
    x_spacing: Incomplete
    y_spacing: Incomplete
    x_count: Incomplete
    y_count: Incomplete
    align: Incomplete
    size: Incomplete
    min: Incomplete
    max: Incomplete
    local_locations: Incomplete
    planes: list[Plane]
    def __init__(self, x_spacing: float, y_spacing: float, x_count: int, y_count: int, align: Align | tuple[Align, Align] = ...) -> None: ...

class WorkplaneList:
    workplanes: Incomplete
    locations_context: Incomplete
    plane_index: int
    def __init__(self, *workplanes: Face | Plane | Location) -> None: ...
    def __enter__(self): ...
    def __exit__(self, exception_type: type[BaseException] | None, exception_value: BaseException | None, traceback: types.TracebackType | None) -> None: ...
    def __iter__(self): ...
    def __next__(self): ...
    @overload
    @classmethod
    def localize(cls, points: VectorLike) -> Vector: ...
    @overload
    @classmethod
    def localize(cls, *points: VectorLike) -> list[Vector]: ...
T2 = TypeVar('T2')
T2_covar = TypeVar('T2_covar', covariant=True)

class ContextComponentGetter(Protocol[T2_covar]):
    def __call__(self, select: Select = ...) -> T2_covar: ...

vertices: Incomplete
edges: Incomplete
wires: Incomplete
faces: Incomplete
solids: Incomplete
vertex: Incomplete
edge: Incomplete
wire: Incomplete
face: Incomplete
solid: Incomplete
