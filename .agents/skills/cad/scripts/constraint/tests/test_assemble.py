from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from constraint.assemble import constraint_assembly  # noqa: E402

BOX_ON_BOX_CONSTRAINTS = {
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


def _box_part(size: tuple[float, float, float]):
    import build123d

    with build123d.BuildPart() as part:
        build123d.Box(*size)
    return part.part


class ConstraintAssemblyTests(unittest.TestCase):
    def test_returns_labeled_compound(self) -> None:
        assembly = constraint_assembly(
            BOX_ON_BOX_CONSTRAINTS,
            {
                "base": _box_part((200, 150, 20)),
                "b1": _box_part((40, 30, 25)),
            },
        )
        self.assertEqual(getattr(assembly, "label", None), "assembly")
        children = list(getattr(assembly, "children", []) or [])
        self.assertEqual(2, len(children))
        labels = {getattr(child, "label", "") for child in children}
        self.assertEqual({"base", "b1"}, labels)

    def test_part_keys_must_match_bodies(self) -> None:
        with self.assertRaises(ValueError):
            constraint_assembly(
                BOX_ON_BOX_CONSTRAINTS,
                {"base": _box_part((200, 150, 20))},
            )
        with self.assertRaises(ValueError):
            constraint_assembly(
                BOX_ON_BOX_CONSTRAINTS,
                {
                    "base": _box_part((200, 150, 20)),
                    "b1": _box_part((40, 30, 25)),
                    "extra": _box_part((1, 1, 1)),
                },
            )


if __name__ == "__main__":
    unittest.main()
