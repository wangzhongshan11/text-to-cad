from _typeshed import Incomplete
from build123d.build_common import LocationList as LocationList, validate_inputs as validate_inputs
from build123d.build_enums import Align as Align, Mode as Mode
from build123d.build_part import BuildPart as BuildPart
from build123d.geometry import Location as Location, Plane as Plane, Rotation as Rotation, RotationLike as RotationLike
from build123d.topology import Compound as Compound, Part as Part, ShapeList as ShapeList, Solid as Solid, tuplify as tuplify

class BasePartObject(Part):
    rotation: Incomplete
    mode: Incomplete
    def __init__(self, part: Part | Solid, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] | None = None, mode: Mode = ...) -> None: ...

class Box(BasePartObject):
    length: Incomplete
    width: Incomplete
    box_height: Incomplete
    def __init__(self, length: float, width: float, height: float, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...

class Cone(BasePartObject):
    bottom_radius: Incomplete
    top_radius: Incomplete
    cone_height: Incomplete
    arc_size: Incomplete
    align: Incomplete
    def __init__(self, bottom_radius: float, top_radius: float, height: float, arc_size: float = 360, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...

class CounterBoreHole(BasePartObject):
    radius: Incomplete
    counter_bore_radius: Incomplete
    counter_bore_depth: Incomplete
    hole_depth: Incomplete
    mode: Incomplete
    def __init__(self, radius: float, counter_bore_radius: float, counter_bore_depth: float, depth: float | None = None, mode: Mode = ...) -> None: ...

class CounterSinkHole(BasePartObject):
    radius: Incomplete
    counter_sink_radius: Incomplete
    hole_depth: Incomplete
    counter_sink_angle: Incomplete
    mode: Incomplete
    def __init__(self, radius: float, counter_sink_radius: float, depth: float | None = None, counter_sink_angle: float = 82, mode: Mode = ...) -> None: ...

class Cylinder(BasePartObject):
    radius: Incomplete
    cylinder_height: Incomplete
    arc_size: Incomplete
    align: Incomplete
    def __init__(self, radius: float, height: float, arc_size: float = 360, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...

class Hole(BasePartObject):
    radius: Incomplete
    hole_depth: Incomplete
    mode: Incomplete
    def __init__(self, radius: float, depth: float | None = None, mode: Mode = ...) -> None: ...

class Sphere(BasePartObject):
    radius: Incomplete
    arc_size1: Incomplete
    arc_size2: Incomplete
    arc_size3: Incomplete
    align: Incomplete
    def __init__(self, radius: float, arc_size1: float = -90, arc_size2: float = 90, arc_size3: float = 360, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...

class Torus(BasePartObject):
    major_radius: Incomplete
    minor_radius: Incomplete
    minor_start_angle: Incomplete
    minor_end_angle: Incomplete
    major_angle: Incomplete
    align: Incomplete
    def __init__(self, major_radius: float, minor_radius: float, minor_start_angle: float = 0, minor_end_angle: float = 360, major_angle: float = 360, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...

class Wedge(BasePartObject):
    xsize: Incomplete
    ysize: Incomplete
    zsize: Incomplete
    xmin: Incomplete
    zmin: Incomplete
    xmax: Incomplete
    zmax: Incomplete
    align: Incomplete
    def __init__(self, xsize: float, ysize: float, zsize: float, xmin: float, zmin: float, xmax: float, zmax: float, rotation: RotationLike = (0, 0, 0), align: Align | tuple[Align, Align, Align] = ..., mode: Mode = ...) -> None: ...
