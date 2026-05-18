"""P2c-2: analytic Jacobian vs sparse numeric."""

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
from constraint.jacobian import verify_analytic_jacobian  # noqa: E402
from constraint.jacobian_geom import (  # noqa: E402
    direction_world_jacobian,
    point_world_jacobian,
    point_world_jacobian_fd,
)
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import _residual_vector, solve_assembly  # noqa: E402
from constraint.state import BodyPose, pack_poses, unpack_poses  # noqa: E402


def _verify_spec(spec: dict, *, tol: float = 1e-4) -> dict:
    validated = validate_assembly_spec(spec)
    body_ids = tuple(sorted(validated["catalog"].keys()))
    compiled = compile_constraints(
        expand_constraints(validated["constraints"]),
        validated["catalog"],
    )
    result = solve_assembly(spec)
    poses = result["poses"]
    vector = pack_poses(body_ids, poses)

    def residual_fn(vector_in: np.ndarray) -> np.ndarray:
        return _residual_vector(
            body_ids, compiled, unpack_poses(body_ids, vector_in)
        )

    return verify_analytic_jacobian(
        body_ids,
        compiled,
        poses,
        numeric_fn=residual_fn,
        vector=vector,
        tol=tol,
    )


class GeomJacobianTests(unittest.TestCase):
    def test_point_jacobian_matches_fd(self) -> None:
        pose = BodyPose((10.0, -5.0, 3.0), (0.1, 0.2, 0.3, 0.9))
        local = (1.0, 2.0, 0.5)
        analytic = point_world_jacobian(local, pose)
        numeric = point_world_jacobian_fd(local, pose)
        self.assertLess(float(np.max(np.abs(analytic - numeric))), 1e-5)


class AnalyticJacobianTests(unittest.TestCase):
    def test_all_basic_constraint_types(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25]},
                "b2": {"primitive": "cylinder", "radius": 8, "height": 30},
            },
            "constraints": [
                {"id": "fix", "type": "fix", "body": "base"},
                {"id": "pc", "type": "point_coincident", "a": "b1.center", "b": "b2.center"},
                {"id": "ct", "type": "contact", "a": "b1.-z", "b": "base.+z"},
                {"id": "ap", "type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
                {"id": "ax", "type": "axis_coaxial", "a": "b1.axis_z", "b": "b2.axis_z"},
                {"id": "pd", "type": "plane_distance", "a": "b1.+z", "b": "base.+z", "distance": 12.5},
                {
                    "id": "ppo",
                    "type": "point_plane_offset",
                    "point": "b1.center",
                    "plane": "base.+z",
                    "offset": 25.0,
                },
                {
                    "id": "inp",
                    "type": "point_plane_offset",
                    "point": "b1.+x",
                    "plane": "base.+z",
                    "in_plane": "x",
                    "value": 5.0,
                },
            ],
        }
        report = _verify_spec(spec)
        self.assertTrue(report["ok"], msg=f"max_diff={report.get('max_diff')}")

    def test_flat_on_v2_macro_expansion(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25]},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [30, 40]},
            ],
        }
        report = _verify_spec(spec)
        self.assertTrue(report["ok"], msg=f"max_diff={report.get('max_diff')}")

    def test_solve_with_verify_jacobian_flag(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [100, 100, 10]},
                "b1": {"primitive": "box", "size": [10, 10, 10]},
            },
            "constraints": [
                {"type": "contact", "a": "b1.-z", "b": "base.+z"},
                {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
            ],
        }
        result = solve_assembly(spec, verify_jacobian=True)
        verify = result.get("jacobian_verify", {})
        self.assertTrue(verify.get("ok"), msg=str(verify))


if __name__ == "__main__":
    unittest.main()
