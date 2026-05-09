from _typeshed import Incomplete
from build123d.build_common import LocationList as LocationList, flatten_sequence as flatten_sequence, validate_inputs as validate_inputs
from build123d.build_enums import Align as Align, FontStyle as FontStyle, Mode as Mode, TextAlign as TextAlign
from build123d.build_sketch import BuildSketch as BuildSketch
from build123d.geometry import Axis as Axis, Location as Location, Rotation as Rotation, TOLERANCE as TOLERANCE, Vector as Vector, VectorLike as VectorLike, to_align_offset as to_align_offset
from build123d.topology import Compound as Compound, Edge as Edge, Face as Face, ShapeList as ShapeList, Sketch as Sketch, Vertex as Vertex, Wire as Wire, topo_explore_common_vertex as topo_explore_common_vertex, tuplify as tuplify
from collections.abc import Iterable

class BaseSketchObject(Sketch):
    rotation: Incomplete
    mode: Incomplete
    def __init__(self, obj: Compound | Face, rotation: float = 0, align: Align | tuple[Align, Align] | None = None, mode: Mode = ...) -> None: ...

class Circle(BaseSketchObject):
    radius: Incomplete
    align: Incomplete
    def __init__(self, radius: float, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class Ellipse(BaseSketchObject):
    x_radius: Incomplete
    y_radius: Incomplete
    align: Incomplete
    def __init__(self, x_radius: float, y_radius: float, rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class Polygon(BaseSketchObject):
    pts: Incomplete
    align: Incomplete
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class Rectangle(BaseSketchObject):
    width: Incomplete
    rectangle_height: Incomplete
    align: Incomplete
    def __init__(self, width: float, height: float, rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class RectangleRounded(BaseSketchObject):
    width: Incomplete
    rectangle_height: Incomplete
    radius: Incomplete
    align: Incomplete
    def __init__(self, width: float, height: float, radius: float, rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class RegularPolygon(BaseSketchObject):
    radius: float
    apothem: float
    side_count: Incomplete
    align: Incomplete
    def __init__(self, radius: float, side_count: int, major_radius: bool = True, rotation: float = 0, align: tuple[Align, Align] = ..., mode: Mode = ...) -> None: ...

class SlotArc(BaseSketchObject):
    arc: Incomplete
    slot_height: Incomplete
    def __init__(self, arc: Edge | Wire, height: float, rotation: float = 0, mode: Mode = ...) -> None: ...

class SlotCenterPoint(BaseSketchObject):
    slot_center: Incomplete
    point: Incomplete
    slot_height: Incomplete
    def __init__(self, center: VectorLike, point: VectorLike, height: float, rotation: float = 0, mode: Mode = ...) -> None: ...

class SlotCenterToCenter(BaseSketchObject):
    center_separation: Incomplete
    slot_height: Incomplete
    def __init__(self, center_separation: float, height: float, rotation: float = 0, mode: Mode = ...) -> None: ...

class SlotOverall(BaseSketchObject):
    width: Incomplete
    slot_height: Incomplete
    def __init__(self, width: float, height: float, rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class Text(BaseSketchObject):
    txt: Incomplete
    font_size: Incomplete
    font: Incomplete
    font_path: Incomplete
    font_style: Incomplete
    text_align: Incomplete
    align: Incomplete
    text_path: Incomplete
    position_on_path: Incomplete
    rotation: Incomplete
    mode: Incomplete
    def __init__(self, txt: str, font_size: float, font: str = 'Arial', font_path: str | None = None, font_style: FontStyle = ..., text_align: tuple[TextAlign, TextAlign] = ..., align: Align | tuple[Align, Align] | None = None, path: Edge | Wire | None = None, position_on_path: float = 0.0, rotation: float = 0.0, mode: Mode = ...) -> None: ...

class Trapezoid(BaseSketchObject):
    width: Incomplete
    trapezoid_height: Incomplete
    left_side_angle: Incomplete
    right_side_angle: Incomplete
    align: Incomplete
    def __init__(self, width: float, height: float, left_side_angle: float, right_side_angle: float | None = None, rotation: float = 0, align: Align | tuple[Align, Align] | None = ..., mode: Mode = ...) -> None: ...

class Triangle(BaseSketchObject):
    a: Incomplete
    b: Incomplete
    c: Incomplete
    A: Incomplete
    B: Incomplete
    C: Incomplete
    edge_a: Incomplete
    edge_b: Incomplete
    edge_c: Incomplete
    vertex_A: Incomplete
    vertex_B: Incomplete
    vertex_C: Incomplete
    def __init__(self, *, a: float | None = None, b: float | None = None, c: float | None = None, A: float | None = None, B: float | None = None, C: float | None = None, align: Align | tuple[Align, Align] | None = None, rotation: float = 0, mode: Mode = ...) -> None: ...
