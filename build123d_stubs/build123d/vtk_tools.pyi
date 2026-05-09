from typing import Any
from vtkmodules.vtkCommonDataModel import vtkPolyData

HAS_VTK: bool

def to_vtk_poly_data(obj, tolerance: float | None = None, angular_tolerance: float | None = None, normals: bool = False) -> vtkPolyData: ...
def to_vtkpoly_string(shape: Any, tolerance: float = 0.001, angular_tolerance: float = 0.1) -> str: ...
