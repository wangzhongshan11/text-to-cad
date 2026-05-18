"""P0c tests: mating/gauge classification, assumed_locks, status v2."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.solver import solve_assembly  # noqa: E402


def _spin_panel_v2(*, gauge_policy: str) -> dict:
    return {
        "version": 2,
        "ground": "base",
        "dof_policy": {
            "default_box_on_plane": "none",
            "gauge_policy": gauge_policy,
            "mating_policy": "strict",
        },
        "bodies": {
            "base": {"primitive": "box", "size": [200, 150, 20]},
            "panel": {"primitive": "box", "size": [18, 150, 400]},
        },
        "relations": [
            {
                "type": "flat_on",
                "id": "r_panel",
                "child": "panel",
                "on": "base.+z",
                "at": [-90, 0],
            }
        ],
        "constraints": [
            {"type": "axis_parallel", "a": "panel.axis_z", "b": "base.axis_z"},
        ],
    }


class DiagnosticsV2Tests(unittest.TestCase):
    def test_v2_report_has_schema_version_2(self) -> None:
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
        report = result["report"]
        self.assertEqual(2, report.get("schema_version"))
        self.assertIn("mating_free", report)
        self.assertIn("gauge_free", report)
        self.assertIn("assumed_locks", report)

    def test_fully_constrained_v2_flat_on_is_ok(self) -> None:
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
        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["report"].get("mating_free"))
        self.assertEqual([], result["report"].get("gauge_free"))

    def test_spin_panel_v2_gauge_require_is_underconstrained(self) -> None:
        result = solve_assembly(_spin_panel_v2(gauge_policy="require"))
        self.assertEqual("underconstrained", result["status"])
        gauge_free = result["report"].get("gauge_free", [])
        self.assertTrue(gauge_free)
        categories = [g.get("category", "") for g in gauge_free]
        self.assertTrue(any("spin_z" in c for c in categories))

    def test_spin_panel_v2_auto_lock_becomes_ok_assumed(self) -> None:
        result = solve_assembly(_spin_panel_v2(gauge_policy="auto_lock"))
        self.assertEqual("ok_assumed", result["status"])
        self.assertTrue(result["report"].get("assumed_locks"))
        self.assertEqual([], result["report"].get("gauge_free"))

    def test_spin_panel_v2_enumerate_writes_witness_branches(self) -> None:
        result = solve_assembly(_spin_panel_v2(gauge_policy="enumerate"))
        self.assertEqual("underconstrained", result["status"])
        gauge_free = result["report"].get("gauge_free", [])
        self.assertTrue(gauge_free)
        branches = result["report"].get("witness_branches", {})
        self.assertIn("panel", branches)
        candidates = branches["panel"]
        self.assertGreaterEqual(len(candidates), 2)
        self.assertLessEqual(len(candidates), 4)
        for candidate in candidates:
            self.assertIn("id", candidate)
            self.assertIn("rule", candidate)
            self.assertIn("description", candidate)
            self.assertIn("delta_translation", candidate)
        warnings = result.get("warnings", [])
        self.assertFalse(
            any("not yet implemented" in warning for warning in warnings),
            msg="P2d witness should be implemented",
        )

    def test_witness_candidate_ids_are_distinct(self) -> None:
        result = solve_assembly(_spin_panel_v2(gauge_policy="enumerate"))
        candidates = result["report"]["witness_branches"].get("panel", [])
        ids = [candidate["id"] for candidate in candidates]
        self.assertEqual(len(ids), len(set(ids)))

    def test_missing_in_plane_mating_v1_still_underconstrained(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "panel": {"primitive": "box", "size": [18, 150, 400]},
            },
            "constraints": [
                {"type": "contact", "a": "panel.-z", "b": "base.+z"},
                {"type": "point_plane_offset", "point": "panel.center", "plane": "base.+z", "offset": 200.0},
                {"type": "axis_parallel", "a": "panel.axis_z", "b": "base.axis_z"},
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("underconstrained", result["status"])
        self.assertNotIn("schema_version", result["report"])

    def test_v1_dual_axis_lock_still_ok(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "panel": {"primitive": "box", "size": [18, 150, 400]},
            },
            "constraints": [
                {"type": "contact", "a": "panel.-z", "b": "base.+z"},
                {"type": "point_plane_offset", "point": "panel.center", "plane": "base.+z", "offset": 200.0},
                {"type": "point_plane_offset", "point": "panel.center", "plane": "base.+z", "in_plane": "x", "value": -90},
                {"type": "axis_parallel", "a": "panel.axis_z", "b": "base.axis_z"},
                {"type": "axis_parallel", "a": "panel.axis_x", "b": "base.axis_x"},
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("ok", result["status"])


if __name__ == "__main__":
    unittest.main()
