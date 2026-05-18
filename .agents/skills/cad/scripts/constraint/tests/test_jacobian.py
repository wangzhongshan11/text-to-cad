"""P2c-1: sparse numeric Jacobian tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.constraints import compile_constraints  # noqa: E402
from constraint.dof import (  # noqa: E402
    count_dense_jacobian_evaluations,
    count_sparse_jacobian_evaluations,
    dense_numeric_jacobian,
    numeric_jacobian,
    sparse_numeric_jacobian,
    structural_nnz,
)
from constraint.graph import expand_constraints  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import _residual_vector, solve_assembly  # noqa: E402
from constraint.state import pack_poses, unpack_poses  # noqa: E402


class SparseJacobianTests(unittest.TestCase):
    def test_sparse_matches_dense_small_spec(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25]},
            },
            "constraints": [
                {"type": "contact", "a": "b1.-z", "b": "base.+z"},
                {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "offset": 12.5},
                {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
            ],
        }
        validated = validate_assembly_spec(spec)
        body_ids = tuple(sorted(validated["catalog"].keys()))
        constraints = expand_constraints(validated["constraints"])
        compiled = compile_constraints(constraints, validated["catalog"])
        result = solve_assembly(spec)
        vector = pack_poses(body_ids, result["poses"])

        def residual_fn(vector_in: np.ndarray) -> np.ndarray:
            return _residual_vector(
                body_ids, compiled, unpack_poses(body_ids, vector_in)
            )

        dense = dense_numeric_jacobian(residual_fn, vector)
        sparse = sparse_numeric_jacobian(
            residual_fn, vector, body_ids=body_ids, compiled=compiled
        )
        max_diff = float(np.max(np.abs(dense - sparse)))
        self.assertLess(max_diff, 1e-5, msg=f"max|J_dense - J_sparse|={max_diff}")

    def test_sparse_fewer_evaluations_with_unconstrained_body(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25]},
                "floater": {"primitive": "box", "size": [10, 10, 10]},
            },
            "constraints": [
                {"type": "contact", "a": "b1.-z", "b": "base.+z"},
                {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
            ],
        }
        validated = validate_assembly_spec(spec)
        body_ids = tuple(sorted(validated["catalog"].keys()))
        compiled = compile_constraints(
            expand_constraints(validated["constraints"]),
            validated["catalog"],
        )
        result = solve_assembly(spec)
        vector = pack_poses(body_ids, result["poses"])

        def residual_fn(vector_in: np.ndarray) -> np.ndarray:
            return _residual_vector(
                body_ids, compiled, unpack_poses(body_ids, vector_in)
            )

        dense_evals: list[int] = [0]

        def counted_dense(v: np.ndarray) -> np.ndarray:
            dense_evals[0] += 1
            return residual_fn(v)

        sparse_evals: list[int] = [0]
        sparse_numeric_jacobian(
            residual_fn,
            vector,
            body_ids=body_ids,
            compiled=compiled,
            eval_counter=sparse_evals,
        )
        dense_numeric_jacobian(counted_dense, vector)

        self.assertEqual(count_dense_jacobian_evaluations(vector), dense_evals[0])
        self.assertEqual(
            count_sparse_jacobian_evaluations(body_ids, compiled),
            sparse_evals[0],
        )
        self.assertLess(sparse_evals[0], dense_evals[0])

    def test_numeric_jacobian_routes_to_sparse_when_pattern_given(self) -> None:
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
        validated = validate_assembly_spec(spec)
        body_ids = tuple(sorted(validated["catalog"].keys()))
        compiled = compile_constraints(
            expand_constraints(validated["constraints"]),
            validated["catalog"],
        )
        result = solve_assembly(spec)
        vector = pack_poses(body_ids, result["poses"])

        routed = numeric_jacobian(
            lambda v: _residual_vector(
                body_ids, compiled, unpack_poses(body_ids, v)
            ),
            vector,
            body_ids=body_ids,
            compiled=compiled,
        )
        explicit = sparse_numeric_jacobian(
            lambda v: _residual_vector(
                body_ids, compiled, unpack_poses(body_ids, v)
            ),
            vector,
            body_ids=body_ids,
            compiled=compiled,
        )
        self.assertLess(float(np.max(np.abs(routed - explicit))), 1e-9)

    def test_solve_parity_with_sparse_jacobian(self) -> None:
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
        result = solve_assembly(spec)
        self.assertIn(result["status"], {"ok", "ok_assumed"})
        self.assertLess(result["residual_max"], 1e-5)
        self.assertAlmostEqual(
            result["poses"]["b1"].translation[2],
            22.5,
            places=4,
        )


if __name__ == "__main__":
    unittest.main()
