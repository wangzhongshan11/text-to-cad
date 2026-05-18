"""P3a: free-bucket DR sub-cluster tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.clustering import (  # noqa: E402
    cluster_coupled_bodies,
    should_decompose_free_bucket,
)
from constraint.constraints import compile_constraints  # noqa: E402
from constraint.graph import expand_constraints  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402
from constraint.state import pack_poses  # noqa: E402


def _twin_boxes_v2() -> dict:
    return {
        "version": 2,
        "ground": "plate",
        "bodies": {
            "plate": {"primitive": "box", "size": [220, 100, 10], "rotation_mode": "axis_aligned"},
            "box_a": {"primitive": "box", "size": [20, 20, 40], "rotation_mode": "free"},
            "box_b": {"primitive": "box", "size": [16, 16, 32], "rotation_mode": "free"},
        },
        "relations": [
            {"type": "flat_on", "child": "box_a", "on": "plate.+z", "at": [-50, 0]},
            {"type": "flat_on", "child": "box_b", "on": "plate.+z", "at": [55, 0]},
        ],
    }


class FreeClusteringTests(unittest.TestCase):
    def test_disconnected_free_bodies_form_two_clusters(self) -> None:
        validated = validate_assembly_spec(_twin_boxes_v2())
        compiled = compile_constraints(
            expand_constraints(validated["constraints"]),
            validated["catalog"],
        )
        clusters = cluster_coupled_bodies(("pin_a", "pin_b"), compiled)
        self.assertEqual(2, len(clusters))
        self.assertTrue(should_decompose_free_bucket(("pin_a", "pin_b"), compiled))

    def test_chain_free_bodies_single_cluster(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 200, 10], "rotation_mode": "axis_aligned"},
                "b1": {"primitive": "box", "size": [40, 30, 25], "rotation_mode": "free"},
                "b2": {"primitive": "box", "size": [40, 30, 25], "rotation_mode": "free"},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]},
                {"type": "flat_on", "child": "b2", "on": "b1.+z", "at": [0, 0]},
            ],
        }
        validated = validate_assembly_spec(spec)
        compiled = compile_constraints(
            expand_constraints(validated["constraints"]),
            validated["catalog"],
        )
        clusters = cluster_coupled_bodies(("b1", "b2"), compiled)
        self.assertEqual(1, len(clusters))
        self.assertFalse(should_decompose_free_bucket(("b1", "b2"), compiled))


class FreeSolveTests(unittest.TestCase):
    def test_twin_boxes_use_free_dr_and_match_monolithic(self) -> None:
        spec = _twin_boxes_v2()
        dr = solve_assembly(spec)
        self.assertTrue(dr["solve_ok"])
        self.assertIn("free_dr", dr["solve_method"])
        self.assertEqual(2, len(dr.get("free_clusters", [])))

        mono_spec = dict(spec)
        mono_spec["dof_policy"] = {"free_subcluster_min_bodies": 99}
        mono = solve_assembly(mono_spec)
        self.assertTrue(mono["solve_ok"])
        self.assertNotIn("free_dr", mono["solve_method"])

        dr_vec = pack_poses(("box_a", "box_b"), dr["poses"])
        mono_vec = pack_poses(("box_a", "box_b"), mono["poses"])
        self.assertLessEqual(float(abs(dr_vec - mono_vec).max()), 1e-6)

    def test_twin_cylinders_v1_fixture(self) -> None:
        path = (
            Path(__file__).resolve().parents[6]
            / "examples"
            / "constraint"
            / "specs"
            / "twin_cylinders_on_plate.json"
        )
        spec = json.loads(path.read_text(encoding="utf-8"))
        result = solve_assembly(spec)
        self.assertTrue(result["solve_ok"])
        self.assertIn("free_dr", result["solve_method"])
        self.assertEqual(2, len(result.get("free_clusters", [])))


if __name__ == "__main__":
    unittest.main()
