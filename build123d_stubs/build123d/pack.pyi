from build123d import Location as Location, Pos as Pos, Shape as Shape
from collections.abc import Callable as Callable, Collection

def pack(objects: Collection[Shape], padding: float, align_z: bool = False) -> Collection[Shape]: ...
