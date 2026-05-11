#!/usr/bin/env python3
"""
Remove duplicate bare vtkmodules/*.so files when a cpython extension exists.

On macOS arm64, `pip install vtk` then `pip install cadquery-ocp` can leave both
`vtkFoo.so` and `vtkFoo.cpython-39-darwin.so`. The meta-path loader may load the
wrong one and you get:

  ImportError: Failed to load vtkCommonDataModel: No module named vtkmodules.vtkCommonTransforms
  or: Initialization failed for vtkCommonTransforms, not compatible with vtkmodules.vtkCommonCore

Run after (re)installing vtk and cadquery-ocp:

  ./.venv/bin/python .agents/skills/cad/scripts/repair_vtkmodules_duplicate_so.py
"""
from __future__ import annotations

import sys
from pathlib import Path


def _vtkmodules_dir() -> Path | None:
    try:
        import vtkmodules  # type: ignore[import-untyped]
    except ImportError:
        return None
    root = Path(vtkmodules.__file__).resolve().parent
    return root if root.is_dir() else None


def main() -> int:
    vtk_root = _vtkmodules_dir()
    if vtk_root is None:
        print("vtkmodules is not installed; nothing to do.", file=sys.stderr)
        return 1
    removed: list[Path] = []
    for path in sorted(vtk_root.glob("*.so")):
        name = path.name
        if ".cpython-" in name or name.startswith("lib"):
            continue
        stem = name[:-3]  # drop .so
        twins = list(vtk_root.glob(f"{stem}.cpython-*-darwin.so"))
        if not twins:
            continue
        path.unlink(missing_ok=True)
        removed.append(path)
    if not removed:
        print("No duplicate bare vtkmodules/*.so files found.")
        return 0
    print(f"Removed {len(removed)} duplicate bare extension(s), e.g. {removed[0].name!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
