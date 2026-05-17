from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.audit import axis_lock_preflight_warnings, rotation_audit_issues  # noqa: E402
from constraint.errors import ConstraintSchemaError  # noqa: E402
from constraint.limits import DEFAULT_MAX_BODIES, WARN_BODIES  # noqa: E402
from constraint.schema import validate_assembly_spec  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402


def _minimal_spec(body_count: int) -> dict:
    bodies = {f"b{i}": {"primitive": "box", "size": [10, 10, 10]} for i in range(body_count)}
    constraints = [
        {"type": "contact", "a": "b1.-z", "b": "b0.+z"},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "b0.+z", "offset": 5.0},
    ]
    return {"ground": "b0", "bodies": bodies, "constraints": constraints}


class LimitsAuditTests(unittest.TestCase):
    def test_warn_threshold_is_at_least_30(self) -> None:
        self.assertGreaterEqual(WARN_BODIES, 30)
        self.assertGreaterEqual(DEFAULT_MAX_BODIES, 36)

    def test_rejects_body_count_over_default_max(self) -> None:
        with self.assertRaises(ConstraintSchemaError):
            validate_assembly_spec(_minimal_spec(DEFAULT_MAX_BODIES + 1))

    def test_allows_override_limits(self) -> None:
        spec = _minimal_spec(DEFAULT_MAX_BODIES + 2)
        spec["limits"] = {"max_bodies": DEFAULT_MAX_BODIES + 5}
        validated = validate_assembly_spec(spec)
        self.assertIn("large_assembly", " ".join(validated.get("scale_warnings", [])))

    def test_spinning_panel_marked_underconstrained(self) -> None:
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
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("underconstrained", result["status"])
        self.assertTrue(result.get("rotation_issues"))

    def test_dual_axis_lock_can_be_ok(self) -> None:
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
        self.assertFalse(result.get("rotation_issues"))

    def test_preflight_warns_missing_thickness_axis(self) -> None:
        warnings = axis_lock_preflight_warnings(
            ground="base",
            constraints=[
                {"type": "contact", "a": "panel.-z", "b": "base.+z"},
                {"type": "axis_parallel", "a": "panel.axis_z", "b": "base.axis_z"},
            ],
        )
        self.assertTrue(any("missing_in_plane_axis_lock" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
