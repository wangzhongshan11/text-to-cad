from OCP.BRepGProp import BRepGProp as BRepGProp, BRepGProp_Face as BRepGProp_Face
from OCP.GProp import GProp_GProps as GProp_GProps
from _typeshed import Incomplete
from build123d.build_enums import Align as Align
from build123d.geometry import Color as Color, Location as Location, Vector as Vector, to_align_offset as to_align_offset
from build123d.topology import Compound as Compound, Edge as Edge, Face as Face, Shape as Shape, ShapeList as ShapeList, Shell as Shell, Solid as Solid, Vertex as Vertex, Wire as Wire, downcast as downcast
from os import PathLike
from pathlib import Path
from typing import Literal, TextIO

topods_lut: Incomplete

def import_brep(file_name: PathLike | str | bytes) -> Shape: ...
def import_step(filename: PathLike | str | bytes) -> Compound: ...
def import_stl(file_name: PathLike | str | bytes) -> Face: ...
def import_svg_as_buildline_code(file_name: PathLike | str | bytes) -> tuple[str, str]: ...
def import_svg(svg_file: str | Path | TextIO, *, flip_y: bool = True, align: Align | tuple[Align, Align] | None = ..., ignore_visibility: bool = False, label_by: Literal['id', 'class', 'inkscape:label'] | str = 'id', is_inkscape_label: bool | None = None) -> ShapeList[Wire | Face]: ...
