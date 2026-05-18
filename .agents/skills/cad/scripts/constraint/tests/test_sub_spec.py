"""P2a: sub_spec subgraph tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.errors import ConstraintSchemaError, SubSpecCycleError  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import _solve_validated_core, solve_assembly  # noqa: E402
from constraint.subgraph import (  # noqa: E402
    MAX_SUB_SPEC_DEPTH,
    check_sub_spec_dag,
    compose_world_transforms,
    multiply_transform_4x4,
    prepare_spec_with_subgraphs,
)

SPECS_DIR = Path(__file__).resolve().parents[6] / "examples" / "constraint" / "specs" / "sub"


def _translation_from_transform(matrix: tuple[float, ...] | list[float]) -> tuple[float, float, float]:
    return (float(matrix[3]), float(matrix[7]), float(matrix[11]))


class SubSpecParityTests(unittest.TestCase):
    def test_compose_matches_full_sub_spec_solve(self) -> None:
        parent_path = SPECS_DIR / "parent_chassis.json"
        child_path = SPECS_DIR / "chassis.json"
        parent_spec = json.loads(parent_path.read_text(encoding="utf-8"))
        child_spec = json.loads(child_path.read_text(encoding="utf-8"))

        prepared, bundle = prepare_spec_with_subgraphs(parent_spec, parent_path)
        self.assertIsNotNone(bundle)
        assert bundle is not None

        child_validated = validate_assembly_spec(child_spec, spec_path=str(child_path))
        child_result = _solve_validated_core(child_validated)
        bundle.solve_cache[str(child_path.resolve())] = child_result

        parent_validated = validate_assembly_spec(parent_spec, spec_path=str(parent_path))
        parent_catalog = {
            body_id: parent_validated["catalog"][body_id]
            for body_id in parent_validated["bodies"]
            if body_id in parent_validated["catalog"]
        }
        parent_only = {**parent_validated, "catalog": parent_catalog}
        parent_result = _solve_validated_core(parent_only)

        composed = compose_world_transforms(parent_result["transforms"], bundle)
        full = solve_assembly(parent_spec, spec_path=str(parent_path))

        self.assertIn(full["status"], {"ok", "ok_assumed", "underconstrained"})
        sub_wheel = _translation_from_transform(full["transforms"]["wheel_fl"])
        composed_wheel = _translation_from_transform(composed["wheel_fl"])
        for index, (a, b) in enumerate(zip(sub_wheel, composed_wheel)):
            self.assertAlmostEqual(a, b, places=9)

    def test_l3_nested_compose_matches_mid_solve(self) -> None:
        l3_path = SPECS_DIR / "parent_l3.json"
        mid_path = SPECS_DIR / "mid_assembly.json"
        l3 = solve_assembly(json.loads(l3_path.read_text(encoding="utf-8")), spec_path=str(l3_path))
        mid = solve_assembly(json.loads(mid_path.read_text(encoding="utf-8")), spec_path=str(mid_path))

        self.assertIn(l3["status"], {"ok", "ok_assumed", "underconstrained"})
        self.assertIn(mid["status"], {"ok", "ok_assumed", "underconstrained"})
        self.assertIn("sub_spec", l3["solve_method"])

        chassis_matrix = l3["transforms"]["chassis"]
        mid_wheel_matrix = mid["transforms"]["wheel"]
        expected_wheel = multiply_transform_4x4(chassis_matrix, mid_wheel_matrix)
        l3_wheel = _translation_from_transform(l3["transforms"]["wheel"])
        expected = _translation_from_transform(expected_wheel)
        for index, (left, right) in enumerate(zip(l3_wheel, expected)):
            self.assertAlmostEqual(left, right, places=6, msg=f"axis {index}")


class SubSpecValidationTests(unittest.TestCase):
    def test_cross_layer_internal_ref_rejected(self) -> None:
        parent_path = SPECS_DIR / "parent_chassis.json"
        spec = json.loads(parent_path.read_text(encoding="utf-8"))
        spec["relations"] = [
            {
                "type": "flat_on",
                "child": "chassis",
                "on": "chassis.wheel_fl.+z",
                "at": [0, 0],
            }
        ]
        with self.assertRaisesRegex(ConstraintSchemaError, "cross_layer_internal_ref"):
            validate_assembly_spec(spec, spec_path=str(parent_path))

    def test_sub_spec_cycle_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a_path = root / "a.json"
            b_path = root / "b.json"
            a_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "ground": "base",
                        "bodies": {
                            "base": {"primitive": "box", "size": [10, 10, 10]},
                            "child": {"sub_spec": "b.json"},
                        },
                        "relations": [],
                        "constraints": [{"type": "fix", "body": "base"}],
                    }
                ),
                encoding="utf-8",
            )
            b_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "ground": "base",
                        "bodies": {
                            "base": {"primitive": "box", "size": [10, 10, 10]},
                            "child": {"sub_spec": "a.json"},
                        },
                        "relations": [],
                        "constraints": [{"type": "fix", "body": "base"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SubSpecCycleError):
                check_sub_spec_dag(a_path)

    def test_nested_sub_spec_depth_l3_allowed(self) -> None:
        parent_path = SPECS_DIR / "parent_l3.json"
        spec = json.loads(parent_path.read_text(encoding="utf-8"))
        validated = validate_assembly_spec(spec, spec_path=str(parent_path))
        self.assertIn("wheel", validated["catalog"])
        self.assertIn("chassis", validated["catalog"])

    def test_sub_spec_depth_l4_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [root / f"level{i}.json" for i in range(4)]
            for index, path in enumerate(paths):
                child_ref = None if index == 3 else f"level{index + 1}.json"
                bodies = {
                    f"body{index}": {"primitive": "box", "size": [10, 10, 10]},
                }
                if child_ref is not None:
                    bodies[f"sub{index}"] = {"sub_spec": child_ref}
                payload = {
                    "version": 2,
                    "ground": f"body{index}",
                    "bodies": bodies,
                    "relations": [],
                    "constraints": [{"type": "fix", "body": f"body{index}"}],
                }
                if child_ref is not None:
                    payload["interface_spec"] = {
                        "interface_body": f"body{index}",
                        "exports": [f"body{index}.+z"],
                    }
                path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ConstraintSchemaError, "error.depth"):
                check_sub_spec_dag(paths[0], max_depth=MAX_SUB_SPEC_DEPTH)

    def test_merged_catalog_includes_child_bodies(self) -> None:
        parent_path = SPECS_DIR / "parent_chassis.json"
        spec = json.loads(parent_path.read_text(encoding="utf-8"))
        validated = validate_assembly_spec(spec, spec_path=str(parent_path))
        self.assertIn("wheel_fl", validated["catalog"])
        self.assertIn("chassis", validated["catalog"])
