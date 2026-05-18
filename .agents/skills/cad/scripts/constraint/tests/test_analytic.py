"""P0b tests: axis_aligned analytic placement + BFS topological order."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.analytic import (  # noqa: E402
    bfs_placement_order,
    extract_flat_on_placements,
    try_solve_analytic,
)
from constraint.dsl import compile_v2_to_v1, extract_rotation_modes  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402


V2_BOX_ON_BOX = {
    "version": 2,
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": [200, 150, 20]},
        "b1": {"primitive": "box", "size": [40, 30, 25], "rotation_mode": "axis_aligned"},
    },
    "relations": [
        {"type": "flat_on", "id": "r_b1", "child": "b1", "on": "base.+z", "at": [30, 40]},
    ],
}

V1_BOX_ON_BOX = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": [200, 150, 20]},
        "b1": {"primitive": "box", "size": [40, 30, 25]},
    },
    "constraints": [
        {"type": "plane_coincident", "a": "b1.-z", "b": "base.+z", "opposed": True},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "offset": 12.5},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "x", "value": 30},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "y", "value": 40},
        {"type": "axis_parallel", "a": "b1.axis_x", "b": "base.axis_x"},
        {"type": "axis_parallel", "a": "b1.axis_y", "b": "base.axis_y"},
        {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
    ],
}

V2_CHAIN = {
    "version": 2,
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": [100, 100, 10]},
        "b1": {"primitive": "box", "size": [40, 40, 20]},
        "b2": {"primitive": "box", "size": [20, 20, 15]},
    },
    "relations": [
        {"type": "flat_on", "id": "r1", "child": "b1", "on": "base.+z", "at": [0, 0]},
        {"type": "flat_on", "id": "r2", "child": "b2", "on": "b1.+z", "at": [5, -3]},
    ],
}


def _translation_delta(a: tuple, b: tuple) -> float:
    return max(abs(ax - bx) for ax, bx in zip(a, b))


class AnalyticPlacementTests(unittest.TestCase):
    def test_v2_default_rotation_mode_is_axis_aligned(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5]},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]},
            ],
        }
        modes = extract_rotation_modes(spec)
        self.assertEqual("axis_aligned", modes["b1"])

    def test_v2_solve_uses_analytic_nfev_zero(self) -> None:
        result = solve_assembly(V2_BOX_ON_BOX)
        self.assertEqual("analytic", result.get("solve_method"))
        self.assertEqual(0, result["nfev"])
        self.assertEqual("ok", result["status"])
        self.assertLess(result["residual_max"], 1e-6)

    def test_analytic_matches_scipy_v1_within_tol(self) -> None:
        analytic = solve_assembly(V2_BOX_ON_BOX)
        scipy = solve_assembly(V1_BOX_ON_BOX)
        self.assertEqual("analytic", analytic.get("solve_method"))
        self.assertEqual("scipy", scipy.get("solve_method"))
        self.assertGreater(scipy["nfev"], 0)
        self.assertLess(
            _translation_delta(
                analytic["poses"]["b1"].translation,
                scipy["poses"]["b1"].translation,
            ),
            1e-6,
        )

    def test_bfs_chain_depth_three(self) -> None:
        validated = validate_assembly_spec(V2_CHAIN)
        constraints = validated["constraints"]
        placements = extract_flat_on_placements(constraints)
        order = bfs_placement_order(
            placements,
            ground="base",
            analytic_body_ids={"b1", "b2"},
        )
        self.assertEqual(["b1", "b2"], order)

        result = solve_assembly(V2_CHAIN)
        self.assertEqual(0, result["nfev"])
        self.assertEqual("ok", result["status"])
        self.assertAlmostEqual(result["poses"]["b1"].translation[2], 15.0, places=5)
        self.assertAlmostEqual(result["poses"]["b2"].translation[2], 32.5, places=5)

    def test_v1_spec_still_uses_scipy(self) -> None:
        result = solve_assembly(V1_BOX_ON_BOX)
        self.assertEqual("scipy", result.get("solve_method"))
        self.assertGreater(result["nfev"], 0)
        self.assertEqual("ok", result["status"])

    def test_extract_flat_on_from_triggered_by(self) -> None:
        v1 = compile_v2_to_v1(V2_BOX_ON_BOX)
        placements = extract_flat_on_placements(v1["constraints"])
        self.assertEqual(1, len(placements))
        self.assertEqual("b1", placements[0].child_id)
        self.assertEqual("base", placements[0].parent_id)
        self.assertAlmostEqual(30.0, placements[0].u)
        self.assertAlmostEqual(40.0, placements[0].v)
        self.assertAlmostEqual(12.5, placements[0].normal_offset)

    def test_extract_flat_on_from_v1_pattern(self) -> None:
        placements = extract_flat_on_placements(V1_BOX_ON_BOX["constraints"])
        self.assertEqual(1, len(placements))
        self.assertAlmostEqual(12.5, placements[0].normal_offset)


class AnalyticFallbackTests(unittest.TestCase):
    def test_free_rotation_mode_falls_back_to_scipy(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25], "rotation_mode": "free"},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [30, 40]},
            ],
        }
        validated = validate_assembly_spec(spec)
        poses = try_solve_analytic(
            ground=validated["ground"],
            body_ids=tuple(sorted(validated["catalog"].keys())),
            catalog=validated["catalog"],
            constraints=validated["constraints"],
            rotation_modes=validated["rotation_modes"],
        )
        self.assertIsNone(poses)

        result = solve_assembly(spec)
        self.assertEqual("scipy", result.get("solve_method"))
        self.assertGreater(result["nfev"], 0)


if __name__ == "__main__":
    unittest.main()
