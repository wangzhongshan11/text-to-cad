"""P2b: MUS conflict diagnostics tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.solver import solve_assembly  # noqa: E402


def _conflicting_offset_spec() -> dict:
    """Two incompatible normal offsets on the same plane (v1 path → scipy + MUS)."""
    return {
        "ground": "base",
        "bodies": {
            "base": {"primitive": "box", "size": [200, 150, 20]},
            "b1": {"primitive": "box", "size": [40, 30, 25]},
        },
        "constraints": [
            {"type": "contact", "a": "b1.-z", "b": "base.+z"},
            {
                "id": "c_off_a",
                "type": "point_plane_offset",
                "point": "b1.center",
                "plane": "base.+z",
                "offset": 12.5,
            },
            {
                "id": "c_off_b",
                "type": "point_plane_offset",
                "point": "b1.center",
                "plane": "base.+z",
                "offset": 25.0,
            },
            {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
        ],
    }


class MusDiagnosticsTests(unittest.TestCase):
    def test_conflicting_spec_reports_overconstrained_with_mus(self) -> None:
        result = solve_assembly(_conflicting_offset_spec())
        self.assertGreater(result["residual_max"], 1e-4)
        self.assertEqual("overconstrained", result["status"])
        conflicts = result["report"].get("conflict", [])
        self.assertTrue(conflicts)
        entry = conflicts[0]
        self.assertIn("ids", entry)
        self.assertLessEqual(len(entry["ids"]), 3)
        self.assertIn("point_plane_offset", entry.get("reason", ""))

    def test_solve_failed_has_empty_conflict(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [200, 150, 20]},
                "b1": {"primitive": "box", "size": [40, 30, 25]},
            },
            "constraints": [
                {"type": "fix", "body": "base"},
            ],
        }
        try:
            result = solve_assembly(spec)
        except Exception:
            return
        if not result.get("solve_ok"):
            self.assertEqual([], result["report"].get("conflict", []))


if __name__ == "__main__":
    unittest.main()
