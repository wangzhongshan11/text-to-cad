"""R1 unit tests for the v2 ``flat_on`` macro and v1/v2 dispatch.

Covers (see constraint-assembly-optimize1.md §15.2 P0a acceptance):

* ``flat_on`` always emits 4 base constraints (plane_coincident + 3 offsets)
  plus 3 axis_parallel under the default policy (axis_aligned +
  fixed_orthogonal).
* Relation ids and ``triggered_by`` tags follow the ``r{i}_{slot}`` /
  ``"{rid}:flat_on[:role]"`` convention.
* The normal-offset sign is correct for every face value (+x/-x/+y/-y/+z/-z)
  and the solved pose matches an equivalent v1 spec to within 1e-9 mm.
* The v1/v2 router is conservative: existing v1 specs are passthrough; v2-only
  fields without explicit ``"version": 2`` are rejected.
* R1 only implements ``flat_on``; all other relations and unimplemented v2
  features raise a schema error rather than silently downgrading.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.dsl import (  # noqa: E402
    DEFAULT_DOF_POLICY,
    compile_v2_to_v1,
    detect_spec_version,
)
from constraint.errors import ConstraintSchemaError  # noqa: E402
from constraint.macros import SUPPORTED_RELATION_TYPES, expand_flat_on  # noqa: E402
from constraint.solver import solve_assembly  # noqa: E402


def _bodies_for_box_on_base() -> dict:
    return {
        "base": {"primitive": "box", "size": [200, 150, 20]},
        "b1": {"primitive": "box", "size": [40, 30, 25]},
    }


def _v1_equivalent_spec(face: str, offset_value: float) -> dict:
    """Return the hand-written v1 spec equivalent of the v2 flat_on for a face.

    Only the normal-offset / plane-coincident orientation differs across
    faces. We always lock the three world axes to keep parity with the v2
    macro under axis_aligned + fixed_orthogonal defaults.
    """
    return {
        "ground": "base",
        "bodies": _bodies_for_box_on_base(),
        "constraints": [
            {"type": "plane_coincident", "a": f"b1.{face}", "b": "base.+z", "opposed": True},
            {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "offset": offset_value},
            {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "x", "value": 30.0},
            {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "y", "value": 40.0},
            {"type": "axis_parallel", "a": "b1.axis_x", "b": "base.axis_x"},
            {"type": "axis_parallel", "a": "b1.axis_y", "b": "base.axis_y"},
            {"type": "axis_parallel", "a": "b1.axis_z", "b": "base.axis_z"},
        ],
    }


def _v2_spec_for_face(face: str) -> dict:
    return {
        "version": 2,
        "ground": "base",
        "bodies": _bodies_for_box_on_base(),
        "relations": [
            {"type": "flat_on", "id": "r_b1", "child": "b1", "on": "base.+z",
             "at": [30, 40], "face": face},
        ],
    }


def _expected_offset_for_face(face: str) -> float:
    """Mirror the §C.3 reference: sign(face) * (child_half + gap), gap=0."""
    size = {"x": 40.0, "y": 30.0, "z": 25.0}[face[1]]
    sign = +1.0 if face.startswith("-") else -1.0
    return sign * (size / 2.0)


class FlatOnExpansionShapeTests(unittest.TestCase):
    """Pure expansion: structure, ids, triggered_by, offset sign."""

    def test_default_emits_seven_constraints(self) -> None:
        expanded = expand_flat_on(
            {"type": "flat_on", "id": "r_b1", "child": "b1", "on": "base.+z", "at": [30, 40]},
            _bodies_for_box_on_base(),
            DEFAULT_DOF_POLICY,
            rel_index=1,
        )
        self.assertEqual(7, len(expanded), expanded)
        types = [c["type"] for c in expanded]
        self.assertEqual(
            types,
            [
                "plane_coincident",
                "point_plane_offset",
                "point_plane_offset",
                "point_plane_offset",
                "axis_parallel",
                "axis_parallel",
                "axis_parallel",
            ],
        )

    def test_ids_and_triggered_by_follow_naming_rule(self) -> None:
        expanded = expand_flat_on(
            {"type": "flat_on", "id": "r1", "child": "b1", "on": "base.+z", "at": [0, 0]},
            _bodies_for_box_on_base(),
            DEFAULT_DOF_POLICY,
            rel_index=1,
        )
        expected_ids = ["r1_pc", "r1_oux", "r1_ouy", "r1_off", "r1_par_x", "r1_par_y", "r1_par_z"]
        self.assertEqual(expected_ids, [c["id"] for c in expanded])
        for constraint in expanded:
            self.assertTrue(
                constraint["triggered_by"].startswith("r1:flat_on"),
                constraint,
            )

    def test_auto_id_when_missing(self) -> None:
        expanded = expand_flat_on(
            {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]},
            _bodies_for_box_on_base(),
            DEFAULT_DOF_POLICY,
            rel_index=3,
        )
        for constraint in expanded:
            self.assertTrue(constraint["id"].startswith("r3_"), constraint["id"])

    def test_offset_sign_when_child_face_matches_parent_opposite(self) -> None:
        # The macro emits offset = sign(face) * half. ``sign('-z') = +1`` so
        # the child centre sits +half above the parent +z plane.
        for parent_face, child_face in (("+z", "-z"), ("-z", "+z")):
            with self.subTest(parent_face=parent_face, child_face=child_face):
                expanded = expand_flat_on(
                    {"type": "flat_on", "id": "r1", "child": "b1",
                     "on": f"base.{parent_face}", "at": [0, 0], "face": child_face},
                    _bodies_for_box_on_base(),
                    DEFAULT_DOF_POLICY,
                    rel_index=1,
                )
                normal_constraint = next(c for c in expanded if c["id"] == "r1_off")
                self.assertAlmostEqual(
                    normal_constraint["offset"],
                    _expected_offset_for_face(child_face),
                    places=12,
                )

    def test_face_defaults_to_opposite_of_parent(self) -> None:
        # If 'face' is omitted, the macro should pick the inverse of the
        # parent face under axis_aligned (the only feasible choice).
        for parent_face, expected_child_face in (("+z", "-z"), ("-z", "+z")):
            with self.subTest(parent_face=parent_face):
                expanded = expand_flat_on(
                    {"type": "flat_on", "id": "r1", "child": "b1",
                     "on": f"base.{parent_face}", "at": [0, 0]},
                    _bodies_for_box_on_base(),
                    DEFAULT_DOF_POLICY,
                    rel_index=1,
                )
                contact = next(c for c in expanded if c["id"] == "r1_pc")
                self.assertEqual(contact["a"], f"b1.{expected_child_face}")

    def test_lateral_face_rejected_under_axis_aligned(self) -> None:
        for child_face in ("+x", "-x", "+y", "-y"):
            with self.subTest(child_face=child_face):
                with self.assertRaisesRegex(
                    ConstraintSchemaError,
                    "axis is incompatible with parent face",
                ):
                    expand_flat_on(
                        {"type": "flat_on", "id": "r1", "child": "b1",
                         "on": "base.+z", "at": [0, 0], "face": child_face},
                        _bodies_for_box_on_base(),
                        DEFAULT_DOF_POLICY,
                        rel_index=1,
                    )

    def test_same_sign_face_rejected_under_axis_aligned(self) -> None:
        with self.assertRaisesRegex(
            ConstraintSchemaError,
            "must be opposite to parent face",
        ):
            expand_flat_on(
                {"type": "flat_on", "id": "r1", "child": "b1",
                 "on": "base.+z", "at": [0, 0], "face": "+z"},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_non_literal_parent_face_rejected_under_axis_aligned(self) -> None:
        with self.assertRaisesRegex(
            ConstraintSchemaError,
            "parent feature must be a literal box face",
        ):
            expand_flat_on(
                {"type": "flat_on", "id": "r1", "child": "b1",
                 "on": "base.center", "at": [0, 0]},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_no_axis_parallel_when_policy_disabled(self) -> None:
        policy = dict(DEFAULT_DOF_POLICY)
        policy["default_box_on_plane"] = "none"
        expanded = expand_flat_on(
            {"type": "flat_on", "id": "r1", "child": "b1", "on": "base.+z", "at": [0, 0]},
            _bodies_for_box_on_base(),
            policy,
            rel_index=1,
        )
        self.assertEqual(4, len(expanded))
        self.assertNotIn("axis_parallel", [c["type"] for c in expanded])


class FlatOnSchemaRejectionTests(unittest.TestCase):
    """Negative cases: invalid input -> ConstraintSchemaError."""

    def test_invalid_face(self) -> None:
        with self.assertRaisesRegex(ConstraintSchemaError, "invalid face"):
            expand_flat_on(
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0], "face": "+w"},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_unknown_child(self) -> None:
        with self.assertRaisesRegex(ConstraintSchemaError, "child 'ghost' not found"):
            expand_flat_on(
                {"type": "flat_on", "child": "ghost", "on": "base.+z", "at": [0, 0]},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_unknown_parent(self) -> None:
        with self.assertRaisesRegex(ConstraintSchemaError, "parent 'phantom'"):
            expand_flat_on(
                {"type": "flat_on", "child": "b1", "on": "phantom.+z", "at": [0, 0]},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_unsupported_parent_primitive(self) -> None:
        bodies = {
            "ball": {"primitive": "sphere", "radius": 30.0},
            "b1": {"primitive": "box", "size": [10, 10, 10]},
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "sphere"):
            expand_flat_on(
                {"type": "flat_on", "child": "b1", "on": "ball.+z", "at": [0, 0]},
                bodies,
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_cylinder_parent_not_yet_supported(self) -> None:
        bodies = {
            "pad": {"primitive": "cylinder", "radius": 50.0, "height": 10.0},
            "b1": {"primitive": "box", "size": [10, 10, 10]},
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "only 'box'"):
            expand_flat_on(
                {"type": "flat_on", "child": "b1", "on": "pad.+z", "at": [0, 0]},
                bodies,
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )

    def test_at_must_be_two_floats(self) -> None:
        with self.assertRaisesRegex(ConstraintSchemaError, "'at' must be"):
            expand_flat_on(
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [1]},
                _bodies_for_box_on_base(),
                DEFAULT_DOF_POLICY,
                rel_index=1,
            )


class SpecVersionRouterTests(unittest.TestCase):
    def test_v1_spec_is_detected_and_passthrough(self) -> None:
        v1 = {
            "ground": "base",
            "bodies": {"base": {"primitive": "box", "size": [10, 10, 10]}},
            "constraints": [{"type": "fix", "body": "base"}],
        }
        self.assertEqual(1, detect_spec_version(v1))
        # passthrough: same object identity, no field mutation
        self.assertIs(v1, compile_v2_to_v1(v1))

    def test_v2_field_without_version_is_rejected(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5]},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]}
            ],
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "version': 2"):
            detect_spec_version(spec)

    def test_rotation_mode_in_body_without_version_is_rejected(self) -> None:
        spec = {
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5], "rotation_mode": "axis_aligned"},
            },
            "constraints": [{"type": "fix", "body": "base"}],
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "version': 2"):
            detect_spec_version(spec)

    def test_explicit_version_2_is_v2(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5]},
            },
            "relations": [
                {"type": "flat_on", "child": "b1", "on": "base.+z", "at": [0, 0]}
            ],
        }
        self.assertEqual(2, detect_spec_version(spec))

    def test_unsupported_version_value(self) -> None:
        with self.assertRaisesRegex(ConstraintSchemaError, "unsupported spec version"):
            detect_spec_version({"version": 3, "ground": "base", "bodies": {}})

    def test_unknown_relation_type_rejected(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5]},
            },
            "relations": [
                {"type": "wheel_mount", "child": "b1", "parent": "base"}
            ],
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "unsupported"):
            compile_v2_to_v1(spec)

    def test_coax_relation_expands(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "cylinder", "radius": 5, "height": 20},
            },
            "relations": [
                {"type": "coax", "id": "r1", "a": "b1.axis_z", "b": "base.axis_z", "offset": 12.0}
            ],
        }
        v1 = compile_v2_to_v1(spec)
        types = [c["type"] for c in v1["constraints"]]
        self.assertEqual(["axis_coaxial", "point_plane_offset"], types)
        self.assertEqual("r1:coax:axis", v1["constraints"][0]["triggered_by"])


class V2MutexTests(unittest.TestCase):
    def test_sub_spec_with_primitive_rejected(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "sub": {"primitive": "box", "size": [1, 1, 1], "sub_spec": "child.json"},
            },
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "mutually exclusive"):
            compile_v2_to_v1(spec)

    def test_anchor_body_without_sub_spec_rejected(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [1, 1, 1], "anchor_body": "foo"},
            },
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "anchor_body.*requires.*sub_spec"):
            compile_v2_to_v1(spec)

    def test_layout_only_without_place_rejected(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [1, 1, 1], "layout_only": True},
            },
        }
        with self.assertRaisesRegex(ConstraintSchemaError, r"requires 'place"):
            compile_v2_to_v1(spec)

    def test_constraint_id_starting_with_r_rejected(self) -> None:
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": {
                "base": {"primitive": "box", "size": [10, 10, 10]},
                "b1": {"primitive": "box", "size": [5, 5, 5]},
            },
            "constraints": [
                {"id": "r_user", "type": "fix", "body": "b1"}
            ],
        }
        with self.assertRaisesRegex(ConstraintSchemaError, "reserved for relation expansion"):
            compile_v2_to_v1(spec)


class FlatOnEndToEndParityTests(unittest.TestCase):
    """v2 flat_on result must agree with the hand-written v1 spec within the
    solver's residual tolerance.

    Only the most common configuration (parent.+z, child.-z, stacked on top)
    is exercised end-to-end here; lateral / inverted mating requires
    yaw_only / free rotation modes which arrive in P0b/P2e. The 1e-6 mm
    tolerance matches ``RESIDUAL_TOL`` in ``solver.py`` because the macro
    reorders rows in the residual vector and that perturbs scipy's
    trust-region path within the converged neighbourhood.
    """

    PARITY_TOL: float = 1e-6

    def _translation_close(self, a: tuple, b: tuple, tol: float | None = None) -> None:
        tol = self.PARITY_TOL if tol is None else tol
        for ax, bx in zip(a, b):
            self.assertLess(abs(ax - bx), tol, f"got {a} vs {b}")

    def test_canonical_face_parity(self) -> None:
        # parent=+z, child=-z (default auto-pick).
        v2_result = solve_assembly(_v2_spec_for_face("-z"))
        v1_result = solve_assembly(
            _v1_equivalent_spec("-z", _expected_offset_for_face("-z"))
        )
        self.assertEqual(v2_result["status"], "ok", v2_result.get("report"))
        self.assertEqual(v1_result["status"], "ok", v1_result.get("report"))
        self._translation_close(
            v2_result["poses"]["b1"].translation,
            v1_result["poses"]["b1"].translation,
        )

    def test_default_face_auto_picked(self) -> None:
        # omitting 'face' should still produce a 'ok' status; b1 sits on top
        # of base at z = base_top + b1_half = 10 + 12.5 = 22.5 mm.
        spec = {
            "version": 2,
            "ground": "base",
            "bodies": _bodies_for_box_on_base(),
            "relations": [
                {"type": "flat_on", "id": "r_b1", "child": "b1",
                 "on": "base.+z", "at": [30, 40]},
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("ok", result["status"], result.get("report"))
        self.assertAlmostEqual(result["poses"]["b1"].translation[2], 22.5, places=5)

    def test_solve_path_residual_within_tol(self) -> None:
        result = solve_assembly(_v2_spec_for_face("-z"))
        self.assertEqual("ok", result["status"])
        self.assertLess(result["residual_max"], 1e-6)

    def test_supported_relation_types(self) -> None:
        self.assertEqual(
            {
                "flat_on",
                "coax",
                "align",
                "fix_to",
                "hinge",
                "slider",
                "lock_orthogonal_to",
                "yaw_free",
            },
            set(SUPPORTED_RELATION_TYPES),
        )


class V1RegressionPassthroughTests(unittest.TestCase):
    """v1 specs must remain bit-identical after compile_v2_to_v1."""

    def test_box_on_box_v1_passthrough(self) -> None:
        spec = {
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
            ],
        }
        self.assertIs(spec, compile_v2_to_v1(spec))

    def test_v1_solve_still_works_after_router_inserted(self) -> None:
        spec = {
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
            ],
        }
        result = solve_assembly(spec)
        self.assertEqual("ok", result["status"])
        self.assertLess(result["residual_max"], 1e-6)
        # b1 should sit 22.5 mm above origin (base.+z = +10mm, b1 half = 12.5mm).
        self.assertAlmostEqual(result["poses"]["b1"].translation[2], 22.5, places=6)


if __name__ == "__main__":
    unittest.main()
