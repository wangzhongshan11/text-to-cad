"""Manual test runner (no pytest required)."""
import sys
import math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent))

from transpile.core import (
    TranspileError,
    parse_frac, parse_frame,
    _box_joint_geom, _box_joint_geom_inward,
    _cylinder_joint_geom, _cylinder_joint_geom_inward,
    JointGeom,
    parse_joint_ref, SurfaceJointRef, CustomJointRef,
    joint_kind, transpile,
)

pass_count = 0
fail_count = 0

def check(name, cond, msg=""):
    global pass_count, fail_count
    if cond:
        print(f"  PASS  {name}")
        pass_count += 1
    else:
        print(f"  FAIL  {name}" + (f": {msg}" if msg else ""))
        fail_count += 1

def approx(a, b, tol=1e-9):
    if hasattr(a, '__iter__'):
        return all(abs(x - y) < tol for x, y in zip(a, b))
    return abs(a - b) < tol

# ─── parse_frac ───────────────────────────────────────────────────────────────

print("=== parse_frac ===")
check("int 1",    parse_frac(1) == 1.0)
check("int -1",   parse_frac(-1) == -1.0)
check("str 1/2",  approx(parse_frac("1/2"), 0.5))
check("str -1/3", approx(parse_frac("-1/3"), -1/3))
check("str 3/4",  approx(parse_frac("3/4"), 0.75))

# ─── parse_frame ──────────────────────────────────────────────────────────────

print("\n=== parse_frame ===")
x, y, z = parse_frame("+X:+Y:+Z")
check("identity x", x == (1, 0, 0))
check("identity y", y == (0, 1, 0))
check("identity z", z == (0, 0, 1))
x, y, z = parse_frame("+Y:+Z:+X")
check("+Y:+Z:+X x", x == (0, 1, 0))
check("+Y:+Z:+X z", z == (1, 0, 0))
try:
    parse_frame("+W:+Y:+Z")
    check("bad token raises", False)
except TranspileError:
    check("bad token raises", True)

# ─── _box_joint_geom ──────────────────────────────────────────────────────────

print("\n=== _box_joint_geom ===")
g = _box_joint_geom(["0", "0", "1"], [100, 60, 20])
check("top face pos z",  approx(g.pos[2], 10.0))
check("top face x_dir",  g.x_dir == (1.0, 0.0, 0.0))
check("top face z_dir",  g.z_dir == (0.0, 0.0, 1.0))

g2 = _box_joint_geom(["0", "0", "-1"], [100, 60, 20])
check("bottom pos z",              approx(g2.pos[2], -10.0))
check("bottom x_dir +X",          g2.x_dir == (1.0, 0.0, 0.0))
check("bottom z_dir -Z (outward)", g2.z_dir == (0.0, 0.0, -1.0))  # outward normal: -Z

gr = _box_joint_geom(["1",  "0", "0"], [100, 60, 20])
gl = _box_joint_geom(["-1", "0", "0"], [100, 60, 20])
check("right face pos x",       approx(gr.pos[0], 50.0))
check("left face pos x",        approx(gl.pos[0], -50.0))
check("right z_dir +X (outward)", gr.z_dir == (1.0, 0.0, 0.0))
check("left  z_dir -X (outward)", gl.z_dir == (-1.0, 0.0, 0.0))   # outward normal: -X

g_off = _box_joint_geom(["1/2", "1/2", "1"], [200, 120, 10])
check("off-center top pos",   approx(g_off.pos, (50.0, 30.0, 5.0)))
check("off-center top frame", g_off.z_dir == (0.0, 0.0, 1.0))

# ─── _cylinder_joint_geom ────────────────────────────────────────────────────

print("\n=== _cylinder_joint_geom ===")

# End faces
g = _cylinder_joint_geom(["0", "0", "1"], 10, 40)
check("cyl top pos z",  approx(g.pos[2], 20.0))
check("cyl top z_dir",  g.z_dir == (0.0, 0.0, 1.0))

g2 = _cylinder_joint_geom(["0", "0", "-1"], 10, 40)
check("cyl bot pos z",          approx(g2.pos[2], -20.0))
check("cyl bot z_dir -Z (outward)", approx(g2.z_dir, (0.0, 0.0, -1.0)))  # outward normal

# Side face t=0 (+X direction)
gs = _cylinder_joint_geom(["1", "0", "0"], 8, 50)
check("cyl side t=0 pos",    approx(gs.pos, (8.0, 0.0, 0.0)))
check("cyl side t=0 z_dir",  approx(gs.z_dir, (1.0, 0.0, 0.0)))
check("cyl side t=0 y_dir",  approx(gs.y_dir, (0.0, 0.0, 1.0)))
check("cyl side t=0 x_dir",  approx(gs.x_dir, (0.0, 1.0, 0.0)))

# Side face t=1/2 (+Y direction)
gs2 = _cylinder_joint_geom(["1", "1/2", "0"], 8, 50)
check("cyl side t=1/2 pos",   approx(gs2.pos, (0.0, 8.0, 0.0), tol=1e-7))
check("cyl side t=1/2 z_dir", approx(gs2.z_dir, (0.0, 1.0, 0.0), tol=1e-7))
check("cyl side t=1/2 x_dir", approx(gs2.x_dir, (-1.0, 0.0, 0.0), tol=1e-7))

# Side face t=1 (−X direction): outward normal = -X
gs3 = _cylinder_joint_geom(["1", "1", "0"], 8, 50)
check("cyl side t=1 pos",              approx(gs3.pos, (-8.0, 0.0, 0.0), tol=1e-7))
check("cyl side t=1 z_dir -X (outward)", approx(gs3.z_dir, (-1.0, 0.0, 0.0), tol=1e-7))

# Side face t=-1/2 (−Y direction): outward normal = -Y
gs4 = _cylinder_joint_geom(["1", "-1/2", "0"], 8, 50)
check("cyl side t=-1/2 pos",               approx(gs4.pos, (0.0, -8.0, 0.0), tol=1e-7))
check("cyl side t=-1/2 z_dir -Y (outward)", approx(gs4.z_dir, (0.0, -1.0, 0.0), tol=1e-7))

# ─── _box_joint_geom_inward ───────────────────────────────────────────────────

print("\n=== _box_joint_geom_inward ===")

def rh_cross(g):
    """Return (x×y) for frame check."""
    return (
        g.x_dir[1]*g.y_dir[2] - g.x_dir[2]*g.y_dir[1],
        g.x_dir[2]*g.y_dir[0] - g.x_dir[0]*g.y_dir[2],
        g.x_dir[0]*g.y_dir[1] - g.x_dir[1]*g.y_dir[0],
    )

# si:-Z (bottom inward) → same frame as s:+Z (top outward)
si_bot = _box_joint_geom_inward(["0", "0", "-1"], [100, 60, 20])
s_top  = _box_joint_geom(        ["0", "0",  "1"], [100, 60, 20])
check("box si:0:0:-1 z_dir == s:0:0:1 z_dir",  approx(si_bot.z_dir, s_top.z_dir))
check("box si:0:0:-1 x_dir == s:0:0:1 x_dir",  approx(si_bot.x_dir, s_top.x_dir))
check("box si:0:0:-1 y_dir == s:0:0:1 y_dir",  approx(si_bot.y_dir, s_top.y_dir))
check("box si:0:0:-1 pos at bottom",            approx(si_bot.pos, (0.0, 0.0, -10.0)))
check("box si:0:0:-1 right-handed",             approx(rh_cross(si_bot), si_bot.z_dir))

# si:+Z (top inward) → same frame as s:-Z (bottom outward)
si_top = _box_joint_geom_inward(["0", "0",  "1"], [100, 60, 20])
s_bot  = _box_joint_geom(        ["0", "0", "-1"], [100, 60, 20])
check("box si:0:0:1  z_dir == s:0:0:-1 z_dir", approx(si_top.z_dir, s_bot.z_dir))
check("box si:0:0:1  pos at top",               approx(si_top.pos, (0.0, 0.0, 10.0)))
check("box si:0:0:1  right-handed",             approx(rh_cross(si_top), si_top.z_dir))

# si:+X (right inward) → same frame as s:-X (left outward)
si_right = _box_joint_geom_inward(["1",  "0", "0"], [100, 60, 20])
s_left   = _box_joint_geom(       ["-1", "0", "0"], [100, 60, 20])
check("box si:1:0:0  z_dir == s:-1:0:0 z_dir", approx(si_right.z_dir, s_left.z_dir))
check("box si:1:0:0  pos at right",             approx(si_right.pos, (50.0, 0.0, 0.0)))
check("box si:1:0:0  right-handed",             approx(rh_cross(si_right), si_right.z_dir))

# si:-X (left inward) → same frame as s:+X (right outward)
si_left  = _box_joint_geom_inward(["-1", "0", "0"], [100, 60, 20])
s_right  = _box_joint_geom(       ["1",  "0", "0"], [100, 60, 20])
check("box si:-1:0:0 z_dir == s:1:0:0  z_dir", approx(si_left.z_dir, s_right.z_dir))
check("box si:-1:0:0 right-handed",             approx(rh_cross(si_left), si_left.z_dir))

# position of si == position of s for same coords
for coords in [["0","0","1"], ["0","0","-1"], ["1","0","0"], ["-1","0","0"], ["0","1","0"], ["0","-1","0"]]:
    s  = _box_joint_geom(coords, [100, 60, 20])
    si = _box_joint_geom_inward(coords, [100, 60, 20])
    check(f"box si:{':'.join(coords)} pos == s pos", approx(si.pos, s.pos))

# ─── _cylinder_joint_geom_inward ─────────────────────────────────────────────

print("\n=== _cylinder_joint_geom_inward ===")

# cyl si:0:0:-1 (bottom inward) → same frame as cyl s:0:0:1 (top outward)
csi_bot = _cylinder_joint_geom_inward(["0", "0", "-1"], 10, 40)
cs_top  = _cylinder_joint_geom(       ["0", "0",  "1"], 10, 40)
check("cyl si:0:0:-1 z_dir == s:0:0:1 z_dir", approx(csi_bot.z_dir, cs_top.z_dir))
check("cyl si:0:0:-1 pos at bottom",            approx(csi_bot.pos, (0.0, 0.0, -20.0)))
check("cyl si:0:0:-1 right-handed",             approx(rh_cross(csi_bot), csi_bot.z_dir))

# cyl si:0:0:1 (top inward) → same frame as cyl s:0:0:-1 (bottom outward)
csi_top = _cylinder_joint_geom_inward(["0", "0",  "1"], 10, 40)
cs_bot  = _cylinder_joint_geom(       ["0", "0", "-1"], 10, 40)
check("cyl si:0:0:1  z_dir == s:0:0:-1 z_dir", approx(csi_top.z_dir, cs_bot.z_dir))
check("cyl si:0:0:1  pos at top",               approx(csi_top.pos, (0.0, 0.0, 20.0)))
check("cyl si:0:0:1  right-handed",             approx(rh_cross(csi_top), csi_top.z_dir))

# cyl si side t=0 (+X side, inward) → z = -X
csi_s0 = _cylinder_joint_geom_inward(["1", "0", "0"], 8, 50)
check("cyl si:1:0:0  pos",      approx(csi_s0.pos,   (8.0, 0.0, 0.0)))
check("cyl si:1:0:0  z = -X",   approx(csi_s0.z_dir, (-1.0, 0.0, 0.0)))
check("cyl si:1:0:0  y = +Z",   approx(csi_s0.y_dir, (0.0, 0.0, 1.0)))
check("cyl si:1:0:0  right-handed", approx(rh_cross(csi_s0), csi_s0.z_dir))

# cyl si side t=1 (-X side, inward) → same frame as cyl s:1:0:0 (+X outward)
csi_s1  = _cylinder_joint_geom_inward(["1", "1", "0"], 8, 50)
cs_s0   = _cylinder_joint_geom(       ["1", "0", "0"], 8, 50)
check("cyl si:1:1:0  z_dir == s:1:0:0 z_dir", approx(csi_s1.z_dir, cs_s0.z_dir, tol=1e-7))
check("cyl si:1:1:0  pos at -X side",          approx(csi_s1.pos, (-8.0, 0.0, 0.0), tol=1e-7))
check("cyl si:1:1:0  right-handed",            approx(rh_cross(csi_s1), csi_s1.z_dir, tol=1e-7))

# ─── JointGeom.normalize_z ───────────────────────────────────────────────────

print("\n=== JointGeom.normalize_z ===")
# Top face: z=+Z already positive → unchanged
gn = _box_joint_geom(["0", "0", "1"], [100, 60, 20])
norm = gn.normalize_z()
check("normalize top unchanged z", norm.z_dir == gn.z_dir)
check("normalize top unchanged x", norm.x_dir == gn.x_dir)

# Bottom face: z=-Z → normalize to z=+Z
gn2 = _box_joint_geom(["0", "0", "-1"], [100, 60, 20])
norm2 = gn2.normalize_z()
check("normalize bottom z → +Z", approx(norm2.z_dir, (0.0, 0.0, 1.0)))
# Right-hand check after normalization
cx = norm2.x_dir[1]*norm2.y_dir[2] - norm2.x_dir[2]*norm2.y_dir[1]
cy = norm2.x_dir[2]*norm2.y_dir[0] - norm2.x_dir[0]*norm2.y_dir[2]
cz = norm2.x_dir[0]*norm2.y_dir[1] - norm2.x_dir[1]*norm2.y_dir[0]
check("normalize bottom right-handed", approx((cx,cy,cz), norm2.z_dir))

# Cylinder side t=1: z=-X → normalize to z=+X
gn3 = _cylinder_joint_geom(["1", "1", "0"], 8, 50)
norm3 = gn3.normalize_z()
check("normalize cyl t=1 z → +X", approx(norm3.z_dir, (1.0, 0.0, 0.0), tol=1e-7))

# ─── parse_joint_ref ─────────────────────────────────────────────────────────

print("\n=== parse_joint_ref ===")

# surface RigidJoint
r = parse_joint_ref({"id": "rg:s:0:0:1"})
check("surface rg kind_prefix",  isinstance(r, SurfaceJointRef) and r.kind_prefix == "rg")
check("surface rg type_prefix",  isinstance(r, SurfaceJointRef) and r.type_prefix == "s")
check("surface rg coords",       r.coords == ["0", "0", "1"])
check("surface rg raw_id",       r.raw_id == "rg:s:0:0:1")

# surface RevoluteJoint
r2 = parse_joint_ref({"id": "rv:s:0:1:0"})
check("surface rv kind_prefix",  isinstance(r2, SurfaceJointRef) and r2.kind_prefix == "rv")
check("surface rv type_prefix",  isinstance(r2, SurfaceJointRef) and r2.type_prefix == "s")

# surface inward RigidJoint
r_si = parse_joint_ref({"id": "rg:si:0:0:-1"})
check("surface si kind_prefix",  isinstance(r_si, SurfaceJointRef) and r_si.kind_prefix == "rg")
check("surface si type_prefix",  isinstance(r_si, SurfaceJointRef) and r_si.type_prefix == "si")
check("surface si coords",       r_si.coords == ["0", "0", "-1"])
check("surface si raw_id",       r_si.raw_id == "rg:si:0:0:-1")

# surface inward RevoluteJoint
r_si2 = parse_joint_ref({"id": "rv:si:1:0:0"})
check("surface rv:si kind_prefix", isinstance(r_si2, SurfaceJointRef) and r_si2.kind_prefix == "rv")
check("surface rv:si type_prefix", isinstance(r_si2, SurfaceJointRef) and r_si2.type_prefix == "si")

# custom RigidJoint
r3 = parse_joint_ref({"id": "rg:c:0:30:5", "frame": "+X:+Z:-Y"})
check("custom rg kind",   isinstance(r3, CustomJointRef) and r3.kind == "RigidJoint")
check("custom rg raw_id", r3.raw_id == "rg:c:0:30:5")
check("custom rg coords", r3.coords == ["0", "30", "5"])

# custom RevoluteJoint
r4 = parse_joint_ref({"id": "rv:c:0:0:0", "frame": "+X:+Y:+Z"})
check("custom rv kind",   isinstance(r4, CustomJointRef) and r4.kind == "RevoluteJoint")
check("custom rv raw_id", r4.raw_id == "rv:c:0:0:0")

# error: not a dict
try:
    parse_joint_ref("rg:s:0:0:1")
    check("string ref rejected", False)
except TranspileError:
    check("string ref rejected", True)

# error: bad kind prefix
try:
    parse_joint_ref({"id": "xx:s:0:0:1"})
    check("bad kind prefix raises", False)
except TranspileError:
    check("bad kind prefix raises", True)

# error: bad type prefix
try:
    parse_joint_ref({"id": "rg:x:0:0:1"})
    check("bad type prefix raises", False)
except TranspileError:
    check("bad type prefix raises", True)

# error: id too short (no third segment)
try:
    parse_joint_ref({"id": "rg:s"})
    check("short id raises", False)
except TranspileError:
    check("short id raises", True)

# ─── joint_kind ──────────────────────────────────────────────────────────────

print("\n=== joint_kind ===")
check("rg:s → RigidJoint",    joint_kind(parse_joint_ref({"id": "rg:s:0:0:1"})) == "RigidJoint")
check("rv:s → RevoluteJoint", joint_kind(parse_joint_ref({"id": "rv:s:0:0:1"})) == "RevoluteJoint")
check("rg:c → RigidJoint",    joint_kind(parse_joint_ref({"id": "rg:c:0:0:0", "frame": "+X:+Y:+Z"})) == "RigidJoint")
check("rv:c → RevoluteJoint", joint_kind(parse_joint_ref({"id": "rv:c:0:0:0", "frame": "+X:+Y:+Z"})) == "RevoluteJoint")

# ─── transpile ───────────────────────────────────────────────────────────────

print("\n=== transpile: basic pillar on base ===")
spec = {
    "meta": {"title": "pillar on base"},
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
code = transpile(spec)
check("has gen_step",    "def gen_step():" in code)
check("has Box",         "Box(100, 60, 20)" in code)
check("has Cylinder",    "Cylinder(8, 50)" in code)
check("has RigidJoint",  "RigidJoint(" in code)
check("has connect_to",  "connect_to(" in code)
check("has Compound",    "Compound(children=[" in code)

print("\n=== transpile: revolute with angle ===")
spec_rev = {
    "meta": {"title": "door"},
    "parts": [
        {"id": "frame", "primitive": {"kind": "box", "size": [50, 10, 80]}},
        {"id": "door",  "primitive": {"kind": "box", "size": [40, 5,  80]}},
    ],
    "mates": [
        {
            "partA": "frame", "jointA": {"id": "rg:s:1:0:0"},
            "partB": "door",  "jointB": {"id": "rv:s:-1:0:0"},
            "kind": "connect_to", "angle": 30,
        }
    ],
}
code_rev = transpile(spec_rev)
check("revolute angle emitted", "angle=30" in code_rev)
check("RevoluteJoint emitted",  "RevoluteJoint(" in code_rev)

print("\n=== transpile: double revolute rejected ===")
spec_bad = {
    "parts": [
        {"id": "a", "primitive": {"kind": "box", "size": [10, 10, 10]}},
        {"id": "b", "primitive": {"kind": "box", "size": [10, 10, 10]}},
    ],
    "mates": [
        {
            "partA": "a", "jointA": {"id": "rv:s:0:0:1"},
            "partB": "b", "jointB": {"id": "rv:s:0:0:-1"},
            "kind": "connect_to",
        }
    ],
}
try:
    transpile(spec_bad)
    check("double revolute rejected", False)
except TranspileError:
    check("double revolute rejected", True)

print("\n=== transpile: three-level topo order ===")
spec3 = {
    "parts": [
        {"id": "base",  "primitive": {"kind": "box",      "size": [100, 100, 10]}},
        {"id": "mid",   "primitive": {"kind": "cylinder", "radius": 10, "height": 40}},
        {"id": "top",   "primitive": {"kind": "box",      "size": [30, 30, 5]}},
    ],
    "mates": [
        # mid→top listed first in JSON, but base→mid must come first in code
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
code3 = transpile(spec3)
idx_base = code3.index("base.joints")
idx_mid  = code3.index("mid.joints")
check("topo order: base→mid before mid→top", idx_base < idx_mid)

print("\n=== transpile: custom joint ===")
spec_custom = {
    "parts": [
        {"id": "plate",   "primitive": {"kind": "box", "size": [100, 60, 10]}},
        {"id": "bracket", "primitive": {"kind": "box", "size": [20,  20, 40]}},
    ],
    "mates": [
        {
            "partA": "plate",
            # rg:c:0:0:1/2 on box [100,60,10] → pos = (0, 0, dz/4) = (0, 0, 2.5)
            "jointA": {"id": "rg:c:0:0:1/2", "frame": "+Y:+Z:+X"},
            "partB": "bracket",
            "jointB": {"id": "rg:si:0:0:-1"},
            "kind": "connect_to",
        }
    ],
}
code_custom = transpile(spec_custom)
check("custom joint emitted", "Plane(" in code_custom or "Location(" in code_custom)
check("custom RigidJoint",    "RigidJoint(" in code_custom)

print("\n=== custom joint: normalised coordinate denormalisation ===")
from transpile.core import joint_geom_for_ref as _jgfr, parse_joint_ref as _pjr

# Box: rg:c:1/2:0:-1 on [100,60,20] → pos=(25,0,-10)
_prim_box = {"kind": "box", "size": [100, 60, 20]}
_ref_box = _pjr({"id": "rg:c:1/2:0:-1", "frame": "+X:+Y:+Z"})
_g_box = _jgfr(_ref_box, _prim_box)
check("custom box c:1/2:0:-1 pos x=25",   approx(_g_box.pos[0], 25.0))
check("custom box c:1/2:0:-1 pos y=0",    approx(_g_box.pos[1], 0.0))
check("custom box c:1/2:0:-1 pos z=-10",  approx(_g_box.pos[2], -10.0))
check("custom box c:1/2:0:-1 frame z",    _g_box.z_dir == (0.0, 0.0, 1.0))

# Cylinder: rg:c:1:1/2:0 on r=10,h=40 → pos=(0,10,0)
_prim_cyl = {"kind": "cylinder", "radius": 10, "height": 40}
_ref_cyl = _pjr({"id": "rg:c:1:1/2:0", "frame": "+X:+Y:+Z"})
_g_cyl = _jgfr(_ref_cyl, _prim_cyl)
check("custom cyl c:1:1/2:0 pos x≈0",     approx(_g_cyl.pos[0], 0.0, tol=1e-7))
check("custom cyl c:1:1/2:0 pos y=10",    approx(_g_cyl.pos[1], 10.0, tol=1e-7))
check("custom cyl c:1:1/2:0 pos z=0",     approx(_g_cyl.pos[2], 0.0))
spec_si = {
    "meta": {"title": "si stacking"},
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
code_si = transpile(spec_si)
check("si: has RigidJoint",  "RigidJoint(" in code_si)
check("si: has connect_to",  "connect_to(" in code_si)
check("si: joint label s",   "rg_s_0_0_1" in code_si)
check("si: joint label si",  "rg_si_0_0__1" in code_si)

print(f"\n=== Results: {pass_count} passed, {fail_count} failed ===")
if fail_count > 0:
    print("\nGenerated code sample:")
    print(code)
    sys.exit(1)
else:
    print("\nAll tests passed!")
    print("\nSample generated code:\n")
    print(code)
