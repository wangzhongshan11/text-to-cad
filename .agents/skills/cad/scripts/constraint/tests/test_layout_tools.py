"""P3c: layout_to_relations / relations_to_layout tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.layout_tools import layout_to_relations, relations_to_layout  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402


class LayoutToRelationsTests(unittest.TestCase):
    def test_world_positions_emit_fix_to(self) -> None:
        relations = layout_to_relations(
            {"pin_a": [10.0, 20.0, 30.0]},
            ground="plate",
        )
        self.assertEqual(1, len(relations))
        self.assertEqual("fix_to", relations[0]["type"])
        self.assertEqual("pin_a", relations[0]["child"])
        self.assertEqual("plate", relations[0]["parent"])
        self.assertEqual([10.0, 20.0, 30.0], relations[0]["local"])

    def test_in_plane_pair_emits_flat_on(self) -> None:
        relations = layout_to_relations(
            {"pin_a": [50.0, 30.0]},
            ground="base",
            mode="auto",
        )
        self.assertEqual("flat_on", relations[0]["type"])
        self.assertEqual("base.+z", relations[0]["on"])
        self.assertEqual([50.0, 30.0], relations[0]["at"])

    def test_structured_placements_passthrough(self) -> None:
        relations = layout_to_relations(
            {
                "ground": "base",
                "placements": {
                    "b1": {"type": "coax", "a": "b1.axis", "b": "base.axis_z", "offset": 5.0},
                },
            }
        )
        self.assertEqual("coax", relations[0]["type"])
        self.assertEqual(5.0, relations[0]["offset"])


class RelationsToLayoutTests(unittest.TestCase):
    def test_exports_solved_translations(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 200, 10]},
                "pin": {"primitive": "box", "size": [20, 20, 40]},
            },
            "relations": [
                {"type": "flat_on", "child": "pin", "on": "base.+z", "at": [12.0, -8.0]},
            ],
        }
        result = solve_assembly(spec)
        layout = relations_to_layout(spec, transforms=result["transforms"])
        self.assertIn("pin", layout)
        self.assertAlmostEqual(layout["pin"][0], 12.0, delta=0.5)
        self.assertAlmostEqual(layout["pin"][1], -8.0, delta=0.5)

    def test_includes_layout_only_place(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "ornament": {
                    "primitive": "box",
                    "size": [5, 5, 5],
                    "place": [80.0, 30.0, 100.0],
                    "layout_only": True,
                },
            },
            "relations": [],
            "constraints": [{"type": "fix", "body": "base"}],
        }
        layout = relations_to_layout(spec, transforms={"base": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]})
        self.assertEqual([80.0, 30.0, 100.0], layout["ornament"])


if __name__ == "__main__":
    unittest.main()
