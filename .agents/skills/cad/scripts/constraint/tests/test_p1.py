"""P1 acceptance tests: BFS init, macros, layout_only, verify_only."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.dsl import compile_v2_to_v1, extract_layout_places  # noqa: E402
from constraint.errors import ConstraintSchemaError  # noqa: E402
from constraint.macros import expand_fix_to, expand_relation  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.constraints import compile_constraints  # noqa: E402
from constraint.graph import expand_constraints  # noqa: E402
from constraint.solver import (  # noqa: E402
    _residual_max,
    _scipy_seed_poses,
    _solve_body_ids,
    solve_assembly,
)
from constraint.state import STATE_DIM, pack_poses  # noqa: E402


def _chain_spec(*, depth: int, rotation_mode: str = "free") -> dict:
    bodies: dict = {
        "base": {"primitive": "box", "size": [500, 500, 20], "rotation_mode": "axis_aligned"},
    }
    relations = []
    for index in range(1, depth):
        body_id = f"b{index}"
        parent = "base" if index == 1 else f"b{index - 1}"
        bodies[body_id] = {
            "primitive": "box",
            "size": [40, 30, 25],
            "rotation_mode": rotation_mode,
        }
        relations.append(
            {
                "type": "flat_on",
                "child": body_id,
                "on": f"{parent}.+z",
                "at": [10.0 * index, 5.0 * index],
            }
        )
    return {
        "version": 2,
        "ground": "base",
        "bodies": bodies,
        "relations": relations,
    }


class P1MacroTests(unittest.TestCase):
    def test_fix_to_expands_six_constraints(self) -> None:
        bodies = {
            "parent": {"primitive": "box", "size": [100, 100, 10]},
            "child": {"primitive": "box", "size": [20, 20, 20]},
        }
        expanded = expand_fix_to(
            {"type": "fix_to", "child": "child", "parent": "parent", "local": [1, 2, 3]},
            bodies,
            {},
            1,
        )
        self.assertEqual(6, len(expanded))
        offsets = [c for c in expanded if c["type"] == "point_plane_offset"]
        parallels = [c for c in expanded if c["type"] == "axis_parallel"]
        self.assertEqual(3, len(offsets))
        self.assertEqual(3, len(parallels))
        self.assertEqual(1.0, offsets[0]["offset"])

    def test_lock_orthogonal_to_expands_three_axis_parallel(self) -> None:
        bodies = {
            "base": {"primitive": "box", "size": [10, 10, 10]},
            "b1": {"primitive": "box", "size": [5, 5, 5]},
        }
        expanded = expand_relation(
            {"type": "lock_orthogonal_to", "child": "b1", "target": "base"},
            bodies,
            {},
            1,
        )
        self.assertEqual(3, len(expanded))
        self.assertTrue(all(c["type"] == "axis_parallel" for c in expanded))


class P1LayoutTests(unittest.TestCase):
    def test_place_conflicts_with_relations(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [100, 100, 10]},
                "b1": {
                    "primitive": "box",
                    "size": [10, 10, 10],
                    "place": [1, 2, 3],
                },
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]}
            ],
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "'place' conflicts"):
            compile_v2_to_v1(spec)

    def test_layout_only_excluded_from_scipy_vector(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "dof_policy": {"mating_policy": "strict", "gauge_policy": "require"},
            "bodies": {
                "base": {"primitive": "box", "size": [200, 200, 20]},
                "ornament": {
                    "primitive": "box",
                    "size": [20, 20, 20],
                    "place": [80, 30, 100],
                    "layout_only": True,
                },
                "b1": {"primitive": "box", "size": [40, 30, 25]},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [30, 40]}
            ],
        }
        validated = validate_assembly_spec(spec)
        layout_ids = validated["layout_only_ids"]
        self.assertIn("ornament", layout_ids)
        _, layout_poses = extract_layout_places(spec)
        self.assertAlmostEqual(80.0, layout_poses["ornament"].translation[0])

        result = solve_assembly(spec)
        self.assertEqual((80.0, 30.0, 100.0), result["poses"]["ornament"].translation)

        body_ids = tuple(sorted(validated["catalog"].keys()))
        solve_ids = _solve_body_ids(body_ids, layout_ids)
        self.assertNotIn("ornament", solve_ids)
        self.assertEqual(len(solve_ids) * STATE_DIM, len(pack_poses(solve_ids, result["poses"])))


class P1BfsInitTests(unittest.TestCase):
    def test_bfs_improves_initial_residual_on_deep_free_chain(self) -> None:
        spec = _chain_spec(depth=4, rotation_mode="free")
        validated = validate_assembly_spec(spec)
        ground = validated["ground"]
        catalog = validated["catalog"]
        body_ids = tuple(sorted(catalog.keys()))
        solve_ids = _solve_body_ids(body_ids, validated["layout_only_ids"])
        constraints = expand_constraints(validated["constraints"])
        compiled = compile_constraints(constraints, catalog)

        bfs_poses = _scipy_seed_poses(
            body_ids=body_ids,
            solve_ids=solve_ids,
            ground=ground,
            catalog=catalog,
            constraints=constraints,
            initial_guess=validated["initial_guess"],
            layout_poses=validated["layout_poses"],
            initial_poses=None,
            use_bfs=True,
        )
        z_poses = _scipy_seed_poses(
            body_ids=body_ids,
            solve_ids=solve_ids,
            ground=ground,
            catalog=catalog,
            constraints=constraints,
            initial_guess=validated["initial_guess"],
            layout_poses=validated["layout_poses"],
            initial_poses=None,
            use_bfs=False,
        )
        bfs_residual = _residual_max(body_ids, compiled, bfs_poses)
        z_residual = _residual_max(body_ids, compiled, z_poses)
        self.assertLess(
            bfs_residual,
            z_residual * 0.5,
            msg=f"BFS initial residual={bfs_residual} vs Z-stack={z_residual}",
        )

class P1VerifyOnlyTests(unittest.TestCase):
    def test_verify_only_skips_optimization(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "dof_policy": {
                "mating_policy": "permissive",
                "gauge_policy": "auto_lock",
            },
            "bodies": {
                "base": {"primitive": "box", "size": [100, 100, 10]},
                "tag": {
                    "primitive": "box",
                    "size": [5, 5, 5],
                    "place": [0, 0, 20],
                    "layout_only": True,
                },
            },
            "constraints": [
                {
                    "id": "c1",
                    "type": "point_plane_offset",
                    "point": "tag.center",
                    "plane": "base.+z",
                    "offset": 22.5,
                }
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("verify_only", result["solve_method"])
        self.assertEqual(0, result["nfev"])
        self.assertFalse(result["solve_ok"])
        self.assertEqual("solve_failed", result["status"])
