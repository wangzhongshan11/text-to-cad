"""Unit tests for transpile.core."""
from __future__ import annotations

import pytest
from transpile.core import (
    TranspileError,
    parse_frac,
    parse_frame,
    _box_joint_geom,
    _box_joint_geom_inward,
    _cylinder_joint_geom,
    _cylinder_joint_geom_inward,
    JointGeom,
    parse_joint_ref,
    SurfaceJointRef,
    CustomJointRef,
    joint_kind,
    transpile,
)


# ─── parse_frac ──────────────────────────────────────────────────────────────

def test_parse_frac_int():
    assert parse_frac(1) == 1.0
    assert parse_frac(-1) == -1.0
    assert parse_frac(0) == 0.0


def test_parse_frac_string():
    assert parse_frac("1/2") == pytest.approx(0.5)
    assert parse_frac("-1/3") == pytest.approx(-1 / 3)
    assert parse_frac("3/4") == pytest.approx(0.75)
    assert parse_frac("1") == 1.0


def test_parse_frac_float_string():
    assert parse_frac("0.5") == pytest.approx(0.5)


# ─── parse_frame ─────────────────────────────────────────────────────────────

def test_parse_frame_identity():
    x, y, z = parse_frame("+X:+Y:+Z")
    assert x == (1, 0, 0)
    assert y == (0, 1, 0)
    assert z == (0, 0, 1)


def test_parse_frame_yx_face():
    x, y, z = parse_frame("+Y:+Z:+X")
    assert x == (0, 1, 0)
    assert y == (0, 0, 1)
    assert z == (1, 0, 0)


def test_parse_frame_bad_token():
    with pytest.raises(TranspileError):
        parse_frame("+W:+Y:+Z")


def test_parse_frame_wrong_count():
    with pytest.raises(TranspileError):
        parse_frame("+X:+Y")


# ─── _box_joint_geom ─────────────────────────────────────────────────────────

def test_box_top_face():
    geom = _box_joint_geom(["0", "0", "1"], [100.0, 60.0, 20.0])
    assert geom.pos == pytest.approx((0.0, 0.0, 10.0))
    assert geom.x_dir == (1.0, 0.0, 0.0)
    assert geom.z_dir == (0.0, 0.0, 1.0)


def test_box_bottom_face():
    geom = _box_joint_geom(["0", "0", "-1"], [100.0, 60.0, 20.0])
    assert geom.pos == pytest.approx((0.0, 0.0, -10.0))
    # Outward normal convention: -Z face has z pointing down (-Z)
    assert geom.x_dir == pytest.approx((1.0, 0.0, 0.0))
    assert geom.y_dir == pytest.approx((0.0, -1.0, 0.0))
    assert geom.z_dir == pytest.approx((0.0, 0.0, -1.0))


def test_box_right_face():
    geom = _box_joint_geom(["1", "0", "0"], [100.0, 60.0, 20.0])
    assert geom.pos == pytest.approx((50.0, 0.0, 0.0))
    assert geom.x_dir == (0.0, 1.0, 0.0)
    assert geom.z_dir == (1.0, 0.0, 0.0)


def test_box_left_face_outward_normal():
    # Outward normal: -X face z points in -X direction (NOT same as right face)
    left = _box_joint_geom(["-1", "0", "0"], [100.0, 60.0, 20.0])
    assert left.pos == pytest.approx((-50.0, 0.0, 0.0))
    assert left.z_dir == pytest.approx((-1.0, 0.0, 0.0))
    # Right-hand check: x × y = z
    import math
    cross = (
        left.x_dir[1]*left.y_dir[2] - left.x_dir[2]*left.y_dir[1],
        left.x_dir[2]*left.y_dir[0] - left.x_dir[0]*left.y_dir[2],
        left.x_dir[0]*left.y_dir[1] - left.x_dir[1]*left.y_dir[0],
    )
    assert cross == pytest.approx(left.z_dir, abs=1e-9)


def test_box_off_center_joint():
    geom = _box_joint_geom(["1/2", "1/2", "1"], [200.0, 120.0, 10.0])
    assert geom.pos == pytest.approx((50.0, 30.0, 5.0))
    assert geom.z_dir == (0.0, 0.0, 1.0)


def test_box_all_faces_right_handed():
    """All six face-center joints must form a right-handed frame (x × y == z)."""
    faces = [
        ["0", "0",  "1"], ["0",  "0", "-1"],
        ["1", "0",  "0"], ["-1", "0",  "0"],
        ["0", "1",  "0"], ["0", "-1",  "0"],
    ]
    size = [60.0, 40.0, 20.0]
    for coords in faces:
        g = _box_joint_geom(coords, size)
        cx = g.x_dir[1]*g.y_dir[2] - g.x_dir[2]*g.y_dir[1]
        cy = g.x_dir[2]*g.y_dir[0] - g.x_dir[0]*g.y_dir[2]
        cz = g.x_dir[0]*g.y_dir[1] - g.x_dir[1]*g.y_dir[0]
        assert (cx, cy, cz) == pytest.approx(g.z_dir, abs=1e-9), f"Not right-handed: coords={coords}"


# ─── _cylinder_joint_geom ────────────────────────────────────────────────────

def test_cylinder_top_face():
    geom = _cylinder_joint_geom(["0", "0", "1"], 10.0, 40.0)
    assert geom.pos == pytest.approx((0.0, 0.0, 20.0))
    assert geom.x_dir == (1.0, 0.0, 0.0)
    assert geom.z_dir == (0.0, 0.0, 1.0)


def test_cylinder_bottom_face_outward_normal():
    # Outward normal: bottom face z = -Z (points down, away from body)
    bot = _cylinder_joint_geom(["0", "0", "-1"], 10.0, 40.0)
    assert bot.pos == pytest.approx((0.0, 0.0, -20.0))
    assert bot.z_dir == pytest.approx((0.0, 0.0, -1.0))
    assert bot.x_dir == pytest.approx((1.0, 0.0, 0.0))
    assert bot.y_dir == pytest.approx((0.0, -1.0, 0.0))


def test_cylinder_side_plus_x():
    # rg:s:1:0:0 → t=0 → outward z = +X
    geom = _cylinder_joint_geom(["1", "0", "0"], 8.0, 50.0)
    assert geom.pos == pytest.approx((8.0, 0.0, 0.0))
    assert geom.z_dir == pytest.approx((1.0, 0.0, 0.0))
    assert geom.y_dir == pytest.approx((0.0, 0.0, 1.0))
    assert geom.x_dir == pytest.approx((0.0, 1.0, 0.0))


def test_cylinder_side_plus_y():
    # rg:s:1:1/2:0 → t=1/2 → theta=π/2 → outward z = +Y
    geom = _cylinder_joint_geom(["1", "1/2", "0"], 8.0, 50.0)
    assert geom.pos == pytest.approx((0.0, 8.0, 0.0))
    assert geom.z_dir == pytest.approx((0.0, 1.0, 0.0))
    assert geom.y_dir == pytest.approx((0.0, 0.0, 1.0))
    assert geom.x_dir == pytest.approx((-1.0, 0.0, 0.0))


def test_cylinder_side_minus_x_outward_normal():
    # rg:s:1:1:0 → t=1 → −X side, outward z = -X (NOT same as +X)
    minus = _cylinder_joint_geom(["1", "1", "0"], 8.0, 50.0)
    assert minus.pos == pytest.approx((-8.0, 0.0, 0.0), abs=1e-7)
    assert minus.z_dir == pytest.approx((-1.0, 0.0, 0.0), abs=1e-7)
    # Right-hand check
    cx = minus.x_dir[1]*minus.y_dir[2] - minus.x_dir[2]*minus.y_dir[1]
    cy = minus.x_dir[2]*minus.y_dir[0] - minus.x_dir[0]*minus.y_dir[2]
    cz = minus.x_dir[0]*minus.y_dir[1] - minus.x_dir[1]*minus.y_dir[0]
    assert (cx, cy, cz) == pytest.approx(minus.z_dir, abs=1e-7)


def test_cylinder_side_minus_y_outward_normal():
    # rg:s:1:-1/2:0 → t=-1/2 → −Y side, outward z = -Y (NOT same as +Y)
    minus = _cylinder_joint_geom(["1", "-1/2", "0"], 8.0, 50.0)
    assert minus.pos == pytest.approx((0.0, -8.0, 0.0), abs=1e-7)
    assert minus.z_dir == pytest.approx((0.0, -1.0, 0.0), abs=1e-7)
    cx = minus.x_dir[1]*minus.y_dir[2] - minus.x_dir[2]*minus.y_dir[1]
    cy = minus.x_dir[2]*minus.y_dir[0] - minus.x_dir[0]*minus.y_dir[2]
    cz = minus.x_dir[0]*minus.y_dir[1] - minus.x_dir[1]*minus.y_dir[0]
    assert (cx, cy, cz) == pytest.approx(minus.z_dir, abs=1e-7)


# ─── _box_joint_geom_inward ──────────────────────────────────────────────────

def _check_right_handed(g: JointGeom, label: str = ""):
    """Helper: assert x × y == z."""
    cx = g.x_dir[1]*g.y_dir[2] - g.x_dir[2]*g.y_dir[1]
    cy = g.x_dir[2]*g.y_dir[0] - g.x_dir[0]*g.y_dir[2]
    cz = g.x_dir[0]*g.y_dir[1] - g.x_dir[1]*g.y_dir[0]
    assert (cx, cy, cz) == pytest.approx(g.z_dir, abs=1e-9), f"Not right-handed{': ' + label if label else ''}"


def test_box_inward_bottom_matches_top_outward():
    """rg:si:0:0:-1 (bottom inward) must have same frame as rg:s:0:0:1 (top outward)."""
    si_bot = _box_joint_geom_inward(["0", "0", "-1"], [100.0, 60.0, 20.0])
    s_top  = _box_joint_geom(["0", "0",  "1"], [100.0, 60.0, 20.0])
    # Same frame (z=+Z), but DIFFERENT positions
    assert si_bot.x_dir == pytest.approx(s_top.x_dir)
    assert si_bot.y_dir == pytest.approx(s_top.y_dir)
    assert si_bot.z_dir == pytest.approx(s_top.z_dir)
    assert si_bot.pos == pytest.approx((0.0, 0.0, -10.0))   # at bottom face
    assert s_top.pos  == pytest.approx((0.0, 0.0,  10.0))   # at top face
    _check_right_handed(si_bot, "box si:0:0:-1")


def test_box_inward_top_matches_bottom_outward():
    si_top = _box_joint_geom_inward(["0", "0",  "1"], [100.0, 60.0, 20.0])
    s_bot  = _box_joint_geom(       ["0", "0", "-1"], [100.0, 60.0, 20.0])
    assert si_top.z_dir == pytest.approx(s_bot.z_dir)   # both z=−Z
    assert si_top.pos   == pytest.approx((0.0, 0.0, 10.0))
    _check_right_handed(si_top, "box si:0:0:1")


def test_box_inward_right_matches_left_outward():
    si_right = _box_joint_geom_inward(["1", "0", "0"], [100.0, 60.0, 20.0])
    s_left   = _box_joint_geom(["-1", "0", "0"], [100.0, 60.0, 20.0])
    assert si_right.z_dir == pytest.approx(s_left.z_dir)   # both z=−X
    assert si_right.pos   == pytest.approx((50.0, 0.0, 0.0))
    _check_right_handed(si_right, "box si:1:0:0")


def test_box_inward_left_matches_right_outward():
    si_left  = _box_joint_geom_inward(["-1", "0", "0"], [100.0, 60.0, 20.0])
    s_right  = _box_joint_geom(["1",  "0", "0"], [100.0, 60.0, 20.0])
    assert si_left.z_dir == pytest.approx(s_right.z_dir)   # both z=+X
    assert si_left.pos   == pytest.approx((-50.0, 0.0, 0.0))
    _check_right_handed(si_left, "box si:-1:0:0")


def test_box_inward_all_faces_right_handed():
    faces = [
        ["0", "0",  "1"], ["0",  "0", "-1"],
        ["1", "0",  "0"], ["-1", "0",  "0"],
        ["0", "1",  "0"], ["0", "-1",  "0"],
    ]
    size = [60.0, 40.0, 20.0]
    for coords in faces:
        g = _box_joint_geom_inward(coords, size)
        _check_right_handed(g, f"box si:{':'.join(coords)}")


def test_box_inward_position_same_as_outward():
    """si and s joints at same coords must have identical positions."""
    size = [100.0, 60.0, 20.0]
    for coords in [["0","0","1"], ["0","0","-1"], ["1","0","0"], ["-1","0","0"]]:
        s  = _box_joint_geom(coords, size)
        si = _box_joint_geom_inward(coords, size)
        assert si.pos == pytest.approx(s.pos), f"Position mismatch at {coords}"


# ─── _cylinder_joint_geom_inward ─────────────────────────────────────────────

def test_cylinder_inward_bottom_matches_top_outward():
    """cyl si:0:0:-1 (bottom inward) must have same frame as cyl s:0:0:1 (top outward)."""
    si_bot = _cylinder_joint_geom_inward(["0", "0", "-1"], 10.0, 40.0)
    s_top  = _cylinder_joint_geom(       ["0", "0",  "1"], 10.0, 40.0)
    assert si_bot.x_dir == pytest.approx(s_top.x_dir)
    assert si_bot.y_dir == pytest.approx(s_top.y_dir)
    assert si_bot.z_dir == pytest.approx(s_top.z_dir)   # both +Z
    assert si_bot.pos   == pytest.approx((0.0, 0.0, -20.0))
    _check_right_handed(si_bot, "cyl si:0:0:-1")


def test_cylinder_inward_top_matches_bottom_outward():
    si_top = _cylinder_joint_geom_inward(["0", "0",  "1"], 10.0, 40.0)
    s_bot  = _cylinder_joint_geom(       ["0", "0", "-1"], 10.0, 40.0)
    assert si_top.z_dir == pytest.approx(s_bot.z_dir)   # both −Z
    assert si_top.pos   == pytest.approx((0.0, 0.0, 20.0))
    _check_right_handed(si_top, "cyl si:0:0:1")


def test_cylinder_inward_side_plus_x_has_inward_z():
    """rg:si:1:0:0 (on +X side) → z should point radially inward (−X)."""
    si = _cylinder_joint_geom_inward(["1", "0", "0"], 8.0, 50.0)
    assert si.pos   == pytest.approx((8.0, 0.0, 0.0))
    assert si.z_dir == pytest.approx((-1.0, 0.0, 0.0))   # inward = −X
    assert si.y_dir == pytest.approx((0.0, 0.0, 1.0))    # axial +Z
    _check_right_handed(si, "cyl si:1:0:0")


def test_cylinder_inward_side_minus_x_matches_plus_x_outward():
    """cyl si:1:1:0 (−X side, inward) must have same frame as cyl s:1:0:0 (+X, outward)."""
    si_minx = _cylinder_joint_geom_inward(["1", "1", "0"], 8.0, 50.0)
    s_plusx = _cylinder_joint_geom(       ["1", "0", "0"], 8.0, 50.0)
    assert si_minx.z_dir == pytest.approx(s_plusx.z_dir, abs=1e-7)  # both +X
    assert si_minx.pos   == pytest.approx((-8.0, 0.0, 0.0), abs=1e-7)
    _check_right_handed(si_minx, "cyl si:1:1:0")


def test_cylinder_inward_all_faces_right_handed():
    faces = [
        ["0", "0", "1"], ["0", "0", "-1"],
        ["1", "0", "0"], ["1", "1/2", "0"], ["1", "1", "0"], ["1", "-1/2", "0"],
    ]
    for coords in faces:
        g = _cylinder_joint_geom_inward(coords, 10.0, 50.0)
        _check_right_handed(g, f"cyl si:{':'.join(coords)}")


# ─── JointGeom.normalize_z ───────────────────────────────────────────────────

def test_normalize_z_positive_unchanged():
    # Top face: z=+Z already positive → no change
    geom = _box_joint_geom(["0", "0", "1"], [100.0, 60.0, 20.0])
    norm = geom.normalize_z()
    assert norm.z_dir == pytest.approx(geom.z_dir)
    assert norm.x_dir == pytest.approx(geom.x_dir)


def test_normalize_z_bottom_flips_to_positive():
    # Bottom face: z=-Z (outward normal) → normalize to z=+Z (same-frame for connect_to)
    geom = _box_joint_geom(["0", "0", "-1"], [100.0, 60.0, 20.0])
    norm = geom.normalize_z()
    assert norm.z_dir == pytest.approx((0.0, 0.0, 1.0))
    # Right-hand still holds after normalization
    cx = norm.x_dir[1]*norm.y_dir[2] - norm.x_dir[2]*norm.y_dir[1]
    cy = norm.x_dir[2]*norm.y_dir[0] - norm.x_dir[0]*norm.y_dir[2]
    cz = norm.x_dir[0]*norm.y_dir[1] - norm.x_dir[1]*norm.y_dir[0]
    assert (cx, cy, cz) == pytest.approx(norm.z_dir, abs=1e-9)


def test_normalize_z_cylinder_side_minus_x():
    # t=1: outward z=-X → normalize to z=+X
    geom = _cylinder_joint_geom(["1", "1", "0"], 8.0, 50.0)
    norm = geom.normalize_z()
    assert norm.z_dir == pytest.approx((1.0, 0.0, 0.0), abs=1e-7)
    # Right-hand
    cx = norm.x_dir[1]*norm.y_dir[2] - norm.x_dir[2]*norm.y_dir[1]
    cy = norm.x_dir[2]*norm.y_dir[0] - norm.x_dir[0]*norm.y_dir[2]
    cz = norm.x_dir[0]*norm.y_dir[1] - norm.x_dir[1]*norm.y_dir[0]
    assert (cx, cy, cz) == pytest.approx(norm.z_dir, abs=1e-7)


# ─── parse_joint_ref ─────────────────────────────────────────────────────────

def test_parse_surface_rigid():
    ref = parse_joint_ref({"id": "rg:s:0:0:1"})
    assert isinstance(ref, SurfaceJointRef)
    assert ref.kind_prefix == "rg"
    assert ref.type_prefix == "s"
    assert ref.coords == ["0", "0", "1"]
    assert ref.raw_id == "rg:s:0:0:1"


def test_parse_surface_revolute():
    ref = parse_joint_ref({"id": "rv:s:0:1:0"})
    assert isinstance(ref, SurfaceJointRef)
    assert ref.kind_prefix == "rv"
    assert ref.type_prefix == "s"


def test_parse_surface_inward_rigid():
    ref = parse_joint_ref({"id": "rg:si:0:0:-1"})
    assert isinstance(ref, SurfaceJointRef)
    assert ref.kind_prefix == "rg"
    assert ref.type_prefix == "si"
    assert ref.coords == ["0", "0", "-1"]
    assert ref.raw_id == "rg:si:0:0:-1"


def test_parse_surface_inward_revolute():
    ref = parse_joint_ref({"id": "rv:si:1:0:0"})
    assert isinstance(ref, SurfaceJointRef)
    assert ref.kind_prefix == "rv"
    assert ref.type_prefix == "si"


def test_parse_custom_rigid():
    ref = parse_joint_ref({"id": "rg:c:0:30:5", "frame": "+X:+Z:-Y"})
    assert isinstance(ref, CustomJointRef)
    assert ref.kind == "RigidJoint"
    assert ref.raw_id == "rg:c:0:30:5"
    assert ref.coords == ["0", "30", "5"]


def test_parse_custom_revolute():
    ref = parse_joint_ref({"id": "rv:c:50:0:10", "origin": [0, 0, 0], "frame": "+Y:+Z:+X"})
    assert isinstance(ref, CustomJointRef)
    assert ref.kind == "RevoluteJoint"
    assert ref.raw_id == "rv:c:50:0:10"


def test_parse_string_rejected():
    with pytest.raises(TranspileError):
        parse_joint_ref("rg:s:0:0:1")


def test_parse_bad_kind_prefix():
    with pytest.raises(TranspileError):
        parse_joint_ref({"id": "xx:s:0:0:1"})


def test_parse_bad_type_prefix():
    with pytest.raises(TranspileError):
        parse_joint_ref({"id": "rg:x:0:0:1"})


def test_parse_id_too_short():
    with pytest.raises(TranspileError):
        parse_joint_ref({"id": "rg:s"})


# ─── joint_kind ──────────────────────────────────────────────────────────────

def test_joint_kind_rg_surface():
    assert joint_kind(parse_joint_ref({"id": "rg:s:0:0:1"})) == "RigidJoint"


def test_joint_kind_rv_surface():
    assert joint_kind(parse_joint_ref({"id": "rv:s:0:0:1"})) == "RevoluteJoint"


def test_joint_kind_rg_custom():
    ref = parse_joint_ref({"id": "rg:c:0:0:0", "frame": "+X:+Y:+Z"})
    assert joint_kind(ref) == "RigidJoint"


def test_joint_kind_rv_custom():
    ref = parse_joint_ref({"id": "rv:c:0:0:0", "frame": "+X:+Y:+Z"})
    assert joint_kind(ref) == "RevoluteJoint"


# ─── transpile ───────────────────────────────────────────────────────────────

_SIMPLE_SPEC = {
    "meta": {"schemaVersion": 1, "units": "mm", "title": "pillar on base"},
    "parts": [
        {"id": "base",   "primitive": {"kind": "box",      "size": [100, 60, 20]}},
        {"id": "pillar", "primitive": {"kind": "cylinder", "radius": 8, "height": 50}},
    ],
    "mates": [
        {
            "partA": "base",   "jointA": {"id": "rg:s:0:0:1"},
            "partB": "pillar", "jointB": {"id": "rg:s:0:0:-1"},
            "kind": "connect_to",
        }
    ],
}


def test_transpile_smoke():
    code = transpile(_SIMPLE_SPEC)
    assert "def gen_step():" in code
    assert "Box(100, 60, 20)" in code
    assert "Cylinder(8, 50)" in code
    assert "RigidJoint(" in code
    assert "connect_to(" in code
    assert "Compound(children=[" in code


def test_transpile_no_parts():
    with pytest.raises(TranspileError):
        transpile({"parts": [], "mates": []})


def test_transpile_double_revolute_rejected():
    spec = {
        "parts": [
            {"id": "a", "primitive": {"kind": "box", "size": [10, 10, 10]}},
            {"id": "b", "primitive": {"kind": "box", "size": [10, 10, 10]}},
        ],
        "mates": [
            {
                "partA": "a", "jointA": {"id": "rv:s:0:0:1"},
                "partB": "b", "jointB": {"id": "rv:s:0:0:-1"},
                "kind": "connect_to",
            },
        ],
    }
    with pytest.raises(TranspileError, match="RevoluteJoint"):
        transpile(spec)


def test_transpile_duplicate_partb_rejected():
    spec = {
        "parts": [
            {"id": "a", "primitive": {"kind": "box", "size": [10, 10, 10]}},
            {"id": "b", "primitive": {"kind": "box", "size": [10, 10, 10]}},
            {"id": "c", "primitive": {"kind": "box", "size": [10, 10, 10]}},
        ],
        "mates": [
            {
                "partA": "a", "jointA": {"id": "rg:s:0:0:1"},
                "partB": "b", "jointB": {"id": "rg:s:0:0:-1"},
                "kind": "connect_to",
            },
            {
                "partA": "c", "jointA": {"id": "rg:s:0:0:1"},
                "partB": "b", "jointB": {"id": "rg:s:0:0:-1"},
                "kind": "connect_to",
            },
        ],
    }
    with pytest.raises(TranspileError, match="partB in multiple mates"):
        transpile(spec)


def test_transpile_with_angle():
    spec = {
        "parts": [
            {"id": "frame", "primitive": {"kind": "box", "size": [100, 100, 10]}},
            {"id": "door",  "primitive": {"kind": "box", "size": [80, 5, 60]}},
        ],
        "mates": [
            {
                "partA": "frame", "jointA": {"id": "rg:s:0:1:0"},
                "partB": "door",  "jointB": {"id": "rv:s:0:1:0"},
                "kind": "connect_to",
                "angle": 30,
            }
        ],
    }
    code = transpile(spec)
    assert "RevoluteJoint(" in code
    assert "angle=30" in code


def test_transpile_three_level_chain():
    spec = {
        "parts": [
            {"id": "base", "primitive": {"kind": "box",      "size": [100, 100, 10]}},
            {"id": "mid",  "primitive": {"kind": "cylinder", "radius": 10, "height": 40}},
            {"id": "top",  "primitive": {"kind": "box",      "size": [30, 30, 5]}},
        ],
        "mates": [
            {
                "partA": "mid",  "jointA": {"id": "rg:s:0:0:1"},
                "partB": "top",  "jointB": {"id": "rg:s:0:0:-1"},
                "kind": "connect_to",
            },
            {
                "partA": "base", "jointA": {"id": "rg:s:0:0:1"},
                "partB": "mid",  "jointB": {"id": "rg:s:0:0:-1"},
                "kind": "connect_to",
            },
        ],
    }
    code = transpile(spec)
    idx_base_mid = code.index("base.joints")
    idx_mid_top  = code.index("mid.joints")
    assert idx_base_mid < idx_mid_top


def test_transpile_si_joint_smoke():
    """Transpile spec using si (inward) surface joint — should produce valid code."""
    spec = {
        "meta": {"schemaVersion": 1, "units": "mm", "title": "si stacking"},
        "parts": [
            {"id": "base",   "primitive": {"kind": "box",      "size": [100, 60, 20]}},
            {"id": "pillar", "primitive": {"kind": "cylinder", "radius": 8, "height": 50}},
        ],
        "mates": [
            {
                "partA": "base",   "jointA": {"id": "rg:s:0:0:1"},
                "partB": "pillar", "jointB": {"id": "rg:si:0:0:-1"},
                "kind": "connect_to",
            }
        ],
    }
    code = transpile(spec)
    assert "RigidJoint(" in code
    assert "connect_to(" in code
    # Both joints must appear; si bottom joint z=+Z same frame as top joint z=+Z
    assert "rg_s_0_0_1" in code
    assert "rg_si_0_0__1" in code


def test_transpile_custom_joint_normalised_coords():
    """Custom joint coords are normalised: rg:c:1/2:0:-1 on box[100,60,20] → (25,0,-10)."""
    from transpile.core import joint_geom_for_ref, parse_joint_ref
    prim = {"kind": "box", "size": [100, 60, 20]}
    ref = parse_joint_ref({"id": "rg:c:1/2:0:-1", "frame": "+X:+Y:+Z"})
    geom = joint_geom_for_ref(ref, prim)
    # x = 1/2 * 50 = 25, y = 0, z = -1 * 10 = -10
    import pytest
    assert geom.pos == pytest.approx((25.0, 0.0, -10.0))
    assert geom.z_dir == (0.0, 0.0, 1.0)


def test_transpile_custom_joint_cylinder_normalised_coords():
    """Custom joint on cylinder: rg:c:1:1/2:0 → side face at +Y (same as s:1:1/2:0)."""
    from transpile.core import joint_geom_for_ref, parse_joint_ref, _cylinder_joint_geom
    prim = {"kind": "cylinder", "radius": 10, "height": 40}
    ref = parse_joint_ref({"id": "rg:c:1:1/2:0", "frame": "+X:+Y:+Z"})
    geom = joint_geom_for_ref(ref, prim)
    # r=1→radius=10, t=1/2→theta=π/2→(cos=0,sin=1)→pos=(0,10,0)
    import pytest
    assert geom.pos == pytest.approx((0.0, 10.0, 0.0), abs=1e-7)
