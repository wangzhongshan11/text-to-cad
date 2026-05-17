from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path.cwd().resolve()
CAD_ROOT = REPO_ROOT
DEFAULT_MESH_TOLERANCE = 0.1
DEFAULT_MESH_ANGULAR_TOLERANCE = 0.1


@dataclass(frozen=True)
class MeshSettings:
    tolerance: float
    angular_tolerance: float


@dataclass(frozen=True)
class GeneratorMetadata:
    script_path: Path
    kind: str
    display_name: str | None
    generator_names: tuple[str, ...]
    has_gen_step: bool
    has_gen_dxf: bool
    has_gen_urdf: bool
    step_output: str | None
    stl: str | None
    three_mf: str | None
    dxf_output: str | None
    urdf_output: str | None
    mesh_tolerance: float | None
    mesh_angular_tolerance: float | None


DXF_ENVELOPE_FIELDS = {"document", "dxf_output"}
URDF_ENVELOPE_FIELDS = {"xml", "urdf_output", "explorer_metadata"}


DEFAULT_MESH_SETTINGS = MeshSettings(
    tolerance=DEFAULT_MESH_TOLERANCE,
    angular_tolerance=DEFAULT_MESH_ANGULAR_TOLERANCE,
)


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def normalize_mesh_numeric(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")
    if normalized <= 0.0:
        raise ValueError(f"{field_name} must be greater than 0")
    return normalized


def resolve_mesh_settings(
    *,
    cad_ref: str,
    generator_metadata: GeneratorMetadata | None,
    mesh_tolerance: float | None = None,
    mesh_angular_tolerance: float | None = None,
) -> MeshSettings:
    tolerance = DEFAULT_MESH_SETTINGS.tolerance
    angular_tolerance = DEFAULT_MESH_SETTINGS.angular_tolerance
    if mesh_tolerance is not None:
        tolerance = mesh_tolerance
    if mesh_angular_tolerance is not None:
        angular_tolerance = mesh_angular_tolerance
    return MeshSettings(
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
    )


def parse_generator_metadata(script_path: Path) -> GeneratorMetadata | None:
    try:
        tree = ast.parse(script_path.read_text(), filename=str(script_path))
    except (FileNotFoundError, SyntaxError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Failed to parse {_display_path(script_path)}") from exc

    display_name: str | None = None
    kind: str | None = None
    has_gen_step = False
    has_gen_dxf = False
    has_gen_urdf = False
    generator_names: list[str] = []
    step_output: str | None = None
    stl: str | None = None
    three_mf: str | None = None
    dxf_output: str | None = None
    urdf_output: str | None = None

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
            if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                if target.id == "DISPLAY_NAME" and isinstance(value.value, str):
                    display_name = value.value.strip()
                elif target.id == "STEP_OUTPUT" and isinstance(value.value, str):
                    step_output = _normalize_step_output_literal(
                        script_path=script_path,
                        raw_value=value.value,
                    )
            continue
        if isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
            if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                if target.id == "DISPLAY_NAME" and isinstance(value.value, str):
                    display_name = value.value.strip()
                elif target.id == "STEP_OUTPUT" and isinstance(value.value, str):
                    step_output = _normalize_step_output_literal(
                        script_path=script_path,
                        raw_value=value.value,
                    )
            continue

        if not isinstance(node, ast.FunctionDef) or node.name not in {"gen_step", "gen_dxf", "gen_urdf"}:
            continue
        generator_names.append(node.name)

        if node.args.args or node.args.posonlyargs or node.args.kwonlyargs:
            raise ValueError(
                f"{_display_path(script_path)} {node.name}() must not require arguments"
            )
        if node.args.vararg or node.args.kwarg:
            raise ValueError(
                f"{_display_path(script_path)} {node.name}() must not accept variadic arguments"
            )

        if node.decorator_list:
            raise ValueError(
                f"{_display_path(script_path)} {node.name}() must not use CAD generator decorators; "
                "return the generated content directly instead"
            )

        if node.name == "gen_step":
            kind = _parse_step_return_metadata(
                script_path=script_path,
                function=node,
            )
            has_gen_step = True
        elif node.name == "gen_dxf":
            dxf_output = _parse_dxf_envelope_metadata(
                script_path=script_path,
                function=node,
            )
            has_gen_dxf = True
        else:
            urdf_output = _parse_urdf_envelope_metadata(
                script_path=script_path,
                function=node,
            )
            has_gen_urdf = True

    if not has_gen_step and not has_gen_dxf and not has_gen_urdf:
        return None
    if not has_gen_step:
        raise ValueError(
            f"{_display_path(script_path)} gen_dxf() and gen_urdf() require gen_step()"
        )

    return GeneratorMetadata(
        script_path=script_path.resolve(),
        kind=kind,
        display_name=display_name,
        generator_names=tuple(generator_names),
        has_gen_step=has_gen_step,
        has_gen_dxf=has_gen_dxf,
        has_gen_urdf=has_gen_urdf,
        step_output=step_output,
        stl=stl,
        three_mf=three_mf,
        dxf_output=dxf_output,
        urdf_output=urdf_output,
        mesh_tolerance=None,
        mesh_angular_tolerance=None,
    )


def _parse_step_return_metadata(
    *,
    script_path: Path,
    function: ast.FunctionDef,
) -> str:
    return_node = _single_return_value(script_path=script_path, function=function)
    if isinstance(return_node, ast.Call) and _is_constraint_assembly_call(return_node):
        return "part"
    return _parse_bare_step_return(script_path=script_path, function=function, return_node=return_node)


def _is_constraint_assembly_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "constraint_assembly"
    if isinstance(func, ast.Attribute):
        return func.attr == "constraint_assembly"
    return False


def _normalize_step_output_literal(*, script_path: Path, raw_value: str) -> str | None:
    from pathlib import PurePosixPath

    value = raw_value.strip()
    if not value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    if pure.suffix.lower() != ".step":
        return None
    return value


def _parse_bare_step_return(
    *,
    script_path: Path,
    function: ast.FunctionDef,
    return_node: ast.expr,
) -> str:
    if isinstance(return_node, (ast.Dict, ast.List)):
        raise ValueError(
            f"{_display_path(script_path)} {function.name}() must return a build123d Shape or Compound"
        )
    if isinstance(return_node, ast.Constant) and return_node.value is None:
        raise ValueError(
            f"{_display_path(script_path)} {function.name}() must return a build123d Shape or Compound"
        )
    return "part"


def _parse_dxf_envelope_metadata(
    *,
    script_path: Path,
    function: ast.FunctionDef,
) -> str | None:
    return_node = _single_return_value(script_path=script_path, function=function)
    if not isinstance(return_node, ast.Dict):
        return None
    envelope = _parse_literal_return_envelope(script_path=script_path, function=function)
    _reject_unsupported_fields(
        script_path=script_path,
        function_name=function.name,
        envelope=envelope,
        allowed_fields=DXF_ENVELOPE_FIELDS,
    )
    if "document" not in envelope:
        raise ValueError(f"{_display_path(script_path)} gen_dxf() envelope must define 'document'")
    return None


def _parse_urdf_envelope_metadata(
    *,
    script_path: Path,
    function: ast.FunctionDef,
) -> str | None:
    envelope = _parse_literal_return_envelope(script_path=script_path, function=function)
    _reject_unsupported_fields(
        script_path=script_path,
        function_name=function.name,
        envelope=envelope,
        allowed_fields=URDF_ENVELOPE_FIELDS,
    )
    if "xml" not in envelope:
        raise ValueError(f"{_display_path(script_path)} gen_urdf() envelope must define 'xml'")
    return _parse_path_field(
        script_path=script_path,
        function_name=function.name,
        envelope=envelope,
        field_name="urdf_output",
    )


def _parse_literal_return_envelope(
    *,
    script_path: Path,
    function: ast.FunctionDef,
) -> dict[str, ast.expr]:
    value = _single_return_value(script_path=script_path, function=function)
    if not isinstance(value, ast.Dict):
        raise ValueError(
            f"{_display_path(script_path)} {function.name}() must return a generator envelope dict"
        )
    envelope: dict[str, ast.expr] = {}
    if len(value.keys) != len(value.values):
        raise ValueError(
            f"{_display_path(script_path)} {function.name}() envelope dict has mismatched keys/values"
        )
    for key_node, value_node in zip(value.keys, value.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            raise ValueError(
                f"{_display_path(script_path)} {function.name}() envelope keys must be string literals"
            )
        key = key_node.value
        if key in envelope:
            raise ValueError(
                f"{_display_path(script_path)} {function.name}() envelope duplicate field: {key}"
            )
        envelope[key] = value_node
    return envelope


def _single_return_value(
    *,
    script_path: Path,
    function: ast.FunctionDef,
) -> ast.expr:
    returns = [statement for statement in function.body if isinstance(statement, ast.Return)]
    if len(returns) != 1 or returns[0].value is None:
        raise ValueError(
            f"{_display_path(script_path)} {function.name}() must return one value"
        )
    return returns[0].value


def _reject_unsupported_fields(
    *,
    script_path: Path,
    function_name: str,
    envelope: dict[str, ast.expr],
    allowed_fields: set[str],
) -> None:
    extra_fields = sorted(key for key in envelope if key not in allowed_fields)
    if extra_fields:
        joined = ", ".join(extra_fields)
        raise ValueError(
            f"{_display_path(script_path)} {function_name}() envelope has unsupported field(s): {joined}"
        )


def _literal_field(
    *,
    script_path: Path,
    function_name: str,
    envelope: dict[str, ast.expr],
    field_name: str,
) -> object | None:
    if field_name not in envelope:
        return None
    try:
        return ast.literal_eval(envelope[field_name])
    except (ValueError, SyntaxError) as exc:
        raise ValueError(
            f"{_display_path(script_path)} {function_name}() envelope {field_name} must be a literal"
        ) from exc


def _parse_path_field(
    *,
    script_path: Path,
    function_name: str,
    envelope: dict[str, ast.expr],
    field_name: str,
) -> str | None:
    value = _literal_field(
        script_path=script_path,
        function_name=function_name,
        envelope=envelope,
        field_name=field_name,
    )
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{_display_path(script_path)} {function_name}() envelope {field_name} "
            "must be a non-empty string"
        )
    if "\\" in value:
        raise ValueError(
            f"{_display_path(script_path)} {function_name}() envelope {field_name} "
            "must use POSIX '/' separators"
        )
    return value.strip()
