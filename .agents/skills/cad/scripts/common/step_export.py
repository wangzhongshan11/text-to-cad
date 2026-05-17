from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from common.step_scene import LoadedStepScene, load_step_scene_from_xcaf_doc, step_file_hash


def create_bin_xcaf_doc() -> Any:
    from OCP.BinXCAFDrivers import BinXCAFDrivers
    from build123d.exporters3d import (
        TCollection_ExtendedString,
        TDocStd_Document,
        UNITS_PER_METER,
        Unit,
        XCAFApp_Application,
        XCAFDoc_DocumentTool,
    )

    doc = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    application = XCAFApp_Application.GetApplication_s()
    BinXCAFDrivers.DefineFormat_s(application)
    application.NewDocument(TCollection_ExtendedString("BinXCAF"), doc)
    application.InitDocument(doc)
    XCAFDoc_DocumentTool.SetLengthUnit_s(doc, 1 / UNITS_PER_METER[Unit.MM])
    return doc


def _create_bin_xcaf_doc(to_export: Any) -> Any:
    import warnings

    from build123d.exporters3d import (
        Compound,
        Curve,
        Part,
        PreOrderIter,
        Sketch,
        TCollection_ExtendedString,
        TDataStd_Name,
        TopExp_Explorer,
        XCAFDoc_ColorType,
        XCAFDoc_DocumentTool,
        ta,
    )

    doc = create_bin_xcaf_doc()
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    is_assembly = isinstance(to_export, Compound) and len(to_export.children) > 0
    shape_tool.AddShape(to_export.wrapped, is_assembly)

    for node in PreOrderIter(to_export):
        if not node.label and node.color is None:
            continue

        node_label = shape_tool.FindShape(node.wrapped, findInstance=False)
        sub_node_labels = []
        if isinstance(node, Compound) and not node.children:
            sub_nodes = []
            if isinstance(node, Part):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_SOLID)
            elif isinstance(node, Sketch):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_FACE)
            elif isinstance(node, Curve):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_EDGE)
            else:
                warnings.warn("Unknown Compound type, color not set", stacklevel=2)
                explorer = TopExp_Explorer()

            while explorer.More():
                sub_nodes.append(explorer.Current())
                explorer.Next()

            sub_node_labels = [
                shape_tool.FindShape(sub_node, findInstance=False)
                for sub_node in sub_nodes
            ]
        if node.label and not node_label.IsNull():
            TDataStd_Name.Set_s(node_label, TCollection_ExtendedString(node.label))

        if node.color is not None:
            for label in [node_label] + sub_node_labels:
                if label.IsNull():
                    continue
                color_tool.SetColor(
                    label,
                    node.color.wrapped,
                    XCAFDoc_ColorType.XCAFDoc_ColorSurf,
                )

    shape_tool.UpdateAssemblies()
    return doc


def export_xcaf_doc_step_scene(
    doc: Any,
    output_path: Path,
    *,
    label: str | None = None,
    originating_system: str = "build123d",
) -> LoadedStepScene:
    from OCP.IFSelect import IFSelect_ReturnStatus
    from OCP.IGESControl import IGESControl_Controller
    from OCP.Interface import Interface_Static
    from OCP.Message import Message, Message_Gravity
    from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_Controller, STEPControl_StepModelType
    from OCP.XSControl import XSControl_WorkSession
    from build123d.build_enums import PrecisionMode

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    messenger = Message.DefaultMessenger_s()
    for printer in messenger.Printers():
        printer.SetTraceLevel(Message_Gravity(Message_Gravity.Message_Fail))

    session = XSControl_WorkSession()
    writer = STEPCAFControl_Writer(session, False)
    writer.SetColorMode(True)
    writer.SetLayerMode(True)
    writer.SetNameMode(True)

    # STEP file header metadata is optional; newer build123d/OCP wheels omit APIHeaderSection.
    _ = (label, originating_system)

    STEPCAFControl_Controller.Init_s()
    STEPControl_Controller.Init_s()
    IGESControl_Controller.Init_s()
    Interface_Static.SetIVal_s("write.surfacecurve.mode", 1)
    Interface_Static.SetIVal_s("write.precision.mode", PrecisionMode.AVERAGE.value)
    writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)

    if writer.Write(os.fspath(output_path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {output_path}")
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"STEP export did not create {output_path}")
    return load_step_scene_from_xcaf_doc(
        output_path,
        doc,
        step_hash=step_file_hash(output_path),
    )


def export_build123d_step_scene(to_export: Any, output_path: Path) -> LoadedStepScene:
    doc = _create_bin_xcaf_doc(to_export)
    return export_xcaf_doc_step_scene(
        doc,
        output_path,
        label=getattr(to_export, "label", None),
    )
