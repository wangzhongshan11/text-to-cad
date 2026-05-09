from _typeshed import Incomplete
from build123d.build_common import WorkplaneList as WorkplaneList, flatten_sequence as flatten_sequence, validate_inputs as validate_inputs
from build123d.build_enums import AngularDirection as AngularDirection, ContinuityLevel as ContinuityLevel, GeomType as GeomType, Keep as Keep, LengthMode as LengthMode, Mode as Mode, Side as Side
from build123d.build_line import BuildLine as BuildLine
from build123d.geometry import Axis as Axis, Plane as Plane, TOLERANCE as TOLERANCE, Vector as Vector, VectorLike as VectorLike
from build123d.topology import Curve as Curve, Edge as Edge, Face as Face, Wire as Wire
from build123d.topology.shape_core import ShapeList as ShapeList
from collections.abc import Iterable

class BaseLineObject(Wire):
    def __init__(self, curve: Wire, mode: Mode = ...) -> None: ...

class BaseEdgeObject(Edge):
    def __init__(self, curve: Edge, mode: Mode = ...) -> None: ...

class Airfoil(BaseLineObject):
    @staticmethod
    def parse_naca4(value: str | float) -> tuple[float, float, float]: ...
    code: str
    max_camber: float
    camber_pos: float
    thickness: float
    finite_te: bool
    def __init__(self, airfoil_code: str, n_points: int = 50, finite_te: bool = False, mode: Mode = ...) -> None: ...
    @property
    def camber_line(self) -> Edge: ...

class Bezier(BaseEdgeObject):
    def __init__(self, *cntl_pnts: VectorLike, weights: list[float] | None = None, mode: Mode = ...) -> None: ...

class BlendCurve(BaseEdgeObject):
    def __init__(self, curve0: Edge, curve1: Edge, continuity: ContinuityLevel = ..., end_points: tuple[VectorLike, VectorLike] | None = None, tangent_scalars: tuple[float, float] | None = None, mode: Mode = ...) -> None: ...

class CenterArc(BaseEdgeObject):
    def __init__(self, center: VectorLike, radius: float, start_angle: float, arc_size: float, mode: Mode = ...) -> None: ...

class DoubleTangentArc(BaseEdgeObject):
    def __init__(self, pnt: VectorLike, tangent: VectorLike, other: Curve | Edge | Wire, keep: Keep = ..., mode: Mode = ...) -> None: ...

class EllipticalStartArc(BaseEdgeObject):
    def __init__(self, start: VectorLike, end: VectorLike, x_radius: float, y_radius: float, rotation: float = 0.0, large_arc: bool = False, sweep_flag: bool = True, plane: Plane = ..., mode: Mode = ...) -> None: ...

class EllipticalCenterArc(BaseEdgeObject):
    def __init__(self, center: VectorLike, x_radius: float, y_radius: float, start_angle: float = 0.0, end_angle: float = 90.0, rotation: float = 0.0, angular_direction: AngularDirection = ..., mode: Mode = ...) -> None: ...

class Helix(BaseEdgeObject):
    def __init__(self, pitch: float, height: float, radius: float, center: VectorLike = (0, 0, 0), direction: VectorLike = (0, 0, 1), cone_angle: float = 0, lefthand: bool = False, mode: Mode = ...) -> None: ...

class FilletPolyline(BaseLineObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], radius: float, close: bool = False, mode: Mode = ...) -> None: ...

class JernArc(BaseEdgeObject):
    start: Incomplete
    center_point: Incomplete
    end_of_arc: Incomplete
    def __init__(self, start: VectorLike, tangent: VectorLike, radius: float, arc_size: float, mode: Mode = ...) -> None: ...

class Line(BaseEdgeObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], mode: Mode = ...) -> None: ...

class IntersectingLine(BaseEdgeObject):
    def __init__(self, start: VectorLike, direction: VectorLike, other: Curve | Edge | Wire, mode: Mode = ...) -> None: ...

class PolarLine(BaseEdgeObject):
    def __init__(self, start: VectorLike, length: float, angle: float | None = None, direction: VectorLike | None = None, length_mode: LengthMode = ..., mode: Mode = ...) -> None: ...

class Polyline(BaseLineObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], close: bool = False, mode: Mode = ...) -> None: ...

class RadiusArc(BaseEdgeObject):
    def __init__(self, start_point: VectorLike, end_point: VectorLike, radius: float, short_sagitta: bool = True, mode: Mode = ...) -> None: ...

class SagittaArc(BaseEdgeObject):
    def __init__(self, start_point: VectorLike, end_point: VectorLike, sagitta: float, mode: Mode = ...) -> None: ...

class Spline(BaseEdgeObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], tangents: Iterable[VectorLike] | None = None, tangent_scalars: Iterable[float] | None = None, periodic: bool = False, mode: Mode = ...) -> None: ...

class TangentArc(BaseEdgeObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], tangent: VectorLike, tangent_from_first: bool = True, mode: Mode = ...) -> None: ...

class ThreePointArc(BaseEdgeObject):
    def __init__(self, *pts: VectorLike | Iterable[VectorLike], mode: Mode = ...) -> None: ...

class PointArcTangentLine(BaseEdgeObject):
    def __init__(self, point: VectorLike, arc: Curve | Edge | Wire, side: Side = ..., mode: Mode = ...) -> None: ...

class PointArcTangentArc(BaseEdgeObject):
    def __init__(self, point: VectorLike, direction: VectorLike, arc: Curve | Edge | Wire, side: Side = ..., mode: Mode = ...) -> None: ...

class ArcArcTangentLine(BaseEdgeObject):
    def __init__(self, start_arc: Curve | Edge | Wire, end_arc: Curve | Edge | Wire, side: Side = ..., keep: Keep = ..., mode: Mode = ...) -> None: ...

class ArcArcTangentArc(BaseEdgeObject):
    def __init__(self, start_arc: Curve | Edge | Wire, end_arc: Curve | Edge | Wire, radius: float, side: Side = ..., keep: Keep | tuple[Keep, Keep] = ..., short_sagitta: bool = True, mode: Mode = ...) -> None: ...
