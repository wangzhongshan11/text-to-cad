"""P2e: yaw_only 4D joint solve tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.constraints import compile_constraints  # noqa: E402
from constraint.graph import expand_constraints  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402
from constraint.state import pack_poses  # noqa: E402
from constraint.yaw_state import YAW_STATE_DIM, pose_from_yaw_vector, yaw_vector_from_pose  # noqa: E402
from constraint.yaw_solve import cluster_yaw_bodies  # noqa: E402


def _yaw_pin_flat_on_spec() -> dict:
    return {
        "version": 2,
        "ground": "base",
        "bodies": {
            "base": {"primitive": "box", "size": [200, 200, 10], "rotation_mode": "axis_aligned"},
            "pin": {
                "primitive": "box",
                "size": [16, 16, 24],
                "rotation_mode": "yaw_only",
                "yaw_axis": "+z",
            },
        },
        "relations": [
            {"type": "flat_on", "child": "pin", "on": "base.+z", "at": [0, 0]},
        ],
    }


def _coupled_yaw_spec() -> dict:
    """flat_on + axis_parallel to base.axis_y (joint 4D satisfies; decoupled does not)."""
    return {
        "version": 2,
        "ground": "base",
        "bodies": {
            "base": {"primitive": "box", "size": [200, 200, 10], "rotation_mode": "axis_aligned"},
            "pin": {
                "primitive": "box",
                "size": [16, 16, 24],
                "rotation_mode": "yaw_only",
                "yaw_axis": "+z",
            },
        },
        "relations": [
            {"type": "flat_on", "child": "pin", "on": "base.+z", "at": [0, 0]},
        ],
        "constraints": [
            {"id": "c_align", "type": "axis_parallel", "a": "pin.axis_x", "b": "base.axis_y"},
        ],
    }


class YawStateTests(unittest.TestCase):
    def test_pack_unpack_roundtrip(self) -> None:
        pose = pose_from_yaw_vector((1.0, 2.0, 3.0), 0.25, yaw_axis="+z")
        vector = yaw_vector_from_pose(pose, yaw_axis="+z")
        self.assertEqual(YAW_STATE_DIM, vector.size)
        self.assertAlmostEqual(vector[3], 0.25, places=6)


class YawSolveTests(unittest.TestCase):
    def test_cluster_single_yaw_body(self) -> None:
        validated = validate_assembly_spec(_coupled_yaw_spec())
        compiled = compile_constraints(
            expand_constraints(validated["constraints"]),
            validated["catalog"],
        )
        clusters = cluster_yaw_bodies(("pin",), compiled)
        self.assertEqual([("pin",)], clusters)

    def test_yaw_only_flat_on_solves_with_yaw4d(self) -> None:
        result = solve_assembly(_yaw_pin_flat_on_spec())
        self.assertIn(result["status"], {"ok", "underconstrained"})
        self.assertLess(result["residual_max"], 1e-4)
        self.assertIn("yaw4d", result.get("solve_method", ""))

    def test_coupled_yaw_joint_solve(self) -> None:
        result = solve_assembly(_coupled_yaw_spec())
        self.assertIn(result["status"], {"ok", "ok_assumed", "underconstrained"})
        self.assertLess(result["residual_max"], 1e-4)
        self.assertIn("yaw4d", result.get("solve_method", ""))

    def test_yaw_bucket_uses_four_dimensional_state(self) -> None:
        validated = validate_assembly_spec(_coupled_yaw_spec())
        from constraint.yaw_state import pack_yaw_poses

        vector = pack_yaw_poses(
            ("pin",),
            {"pin": pose_from_yaw_vector((1.0, 2.0, 3.0), 0.5, yaw_axis="+z")},
            validated.get("yaw_axes", {}),
        )
        self.assertEqual(YAW_STATE_DIM, vector.size)

    def test_yaw_state_vector_length_in_pack(self) -> None:
        result = solve_assembly(_coupled_yaw_spec())
        validated = validate_assembly_spec(_coupled_yaw_spec())
        body_ids = tuple(sorted(validated["catalog"].keys()))
        vector = pack_poses(body_ids, result["poses"])
        self.assertEqual(vector.size, 7 * len(body_ids))


if __name__ == "__main__":
    unittest.main()
