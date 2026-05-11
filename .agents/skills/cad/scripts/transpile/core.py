"""
Declarative assembly JSON → build123d Python transpiler.

Input: model-decomposition-assembly-spec JSON (meta/parts/mates).
Output: a Python script with gen_step() that assembles the parts via build123d joints.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


# ─── Errors ──────────────────────────────────────────────────────────────────


class TranspileError(ValueError):
    pass


# ─── Direction table ─────────────────────────────────────────────────────────

_DIR: dict[str, tuple[float, float, float]] = {
    "+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0), "-Z": (0.0, 0.0, -1.0),
}

Vec3 = tuple[float, float, float]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def parse_frac(v: Any) -> float:
    """Parse a fractional value: "1/2", "-1/3", 1, -1, 0.5 → float."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if "/" in s:
        num, den = s.split("/", 1)
        return int(num) / int(den)
    return float(s)


def parse_frame(frame_str: str) -> tuple[Vec3, Vec3, Vec3]:
    """Parse "+X:+Y:+Z" → (x_vec, y_vec, z_vec)."""
    tokens = frame_str.strip().split(":")
    if len(tokens) != 3:
        raise TranspileError(f"frame must have 3 colon-separated tokens, got {frame_str!r}")
    result = []
    for t in tokens:
        t = t.strip()
        if t not in _DIR:
            raise TranspileError(f"unknown frame token {t!r} in {frame_str!r}")
        result.append(_DIR[t])
    return result[0], result[1], result[2]


def _label_safe(s: str) -> str:
    """Make a string safe as a Python identifier suffix."""
    return re.sub(r"[^A-Za-z0-9]", "_", s).strip("_") or "j"


def _fmt_f(v: float) -> str:
    """Format a float cleanly, avoiding spurious decimals."""
    if v == 0.0:
        return "0"
    rounded = round(v, 10)
    if rounded == int(rounded):
        return str(int(rounded))
    return repr(rounded)


def _fmt_vec(v: Vec3) -> str:
    return f"({_fmt_f(v[0])}, {_fmt_f(v[1])}, {_fmt_f(v[2])})"


# ─── Joint geometry ───────────────────────────────────────────────────────────


@dataclass
class JointGeom:
    pos: Vec3
    x_dir: Vec3
    y_dir: Vec3
    z_dir: Vec3

    def is_identity_rotation(self) -> bool:
        return self.x_dir == (1.0, 0.0, 0.0) and self.z_dir == (0.0, 0.0, 1.0)

    def location_code(self) -> str:
        """Generate build123d code that produces the Location for this joint."""
        if self.is_identity_rotation():
            return f"Location({_fmt_vec(self.pos)})"
        return (
            f"Plane(origin={_fmt_vec(self.pos)}, "
            f"x_dir={_fmt_vec(self.x_dir)}, "
            f"z_dir={_fmt_vec(self.z_dir)}).location"
        )

    def normalize_z(self) -> "JointGeom":
        """Normalize to same-frame convention required by build123d's connect_to.

        The spec expresses joint frames as outward normals (intuitive). build123d's
        connect_to aligns frames in the SAME direction, not face-to-face, so opposite
        faces sharing the same dominant axis must share the same z direction. This
        method flips z (and x to keep the frame right-handed) when z's dominant
        component is negative, mapping outward-normal frames to same-frame frames
        without changing the joint position.

        The flip only affects the internal build123d Joint object; it is invisible
        to the spec consumer (who works only with joint IDs).
        """
        x, y, z = self.x_dir, self.y_dir, self.z_dir
        abs_z = (abs(z[0]), abs(z[1]), abs(z[2]))
        dom = abs_z.index(max(abs_z))
        if z[dom] < -1e-9:
            return JointGeom(
                pos=self.pos,
                x_dir=(-x[0], -x[1], -x[2]),
                y_dir=y,
                z_dir=(-z[0], -z[1], -z[2]),
            )
        return self


def _box_joint_geom(coords: list[str], size: list[float]) -> JointGeom:
    """Compute joint geometry for a box surface joint (nx:ny:nz coords).

    Frame convention: outward normal — z-axis points away from the part body
    (same direction as the face's outward normal). +Z face z=+Z, -Z face z=-Z, etc.
    All frames are right-handed.
    """
    if len(coords) != 3:
        raise TranspileError(f"box surface joint needs 3 coords, got {coords}")
    nx, ny, nz = (parse_frac(c) for c in coords)
    dx, dy, dz = float(size[0]), float(size[1]), float(size[2])
    pos: Vec3 = (nx * dx / 2.0, ny * dy / 2.0, nz * dz / 2.0)

    # Dominant axis determines the face group; sign determines outward direction.
    absvals = [abs(nx), abs(ny), abs(nz)]
    face_axis = absvals.index(max(absvals))

    if face_axis == 2:          # ±Z faces — outward z = sign(nz) · Ẑ
        if nz >= 0:             # +Z face: x=+X, y=+Y, z=+Z
            x_dir, y_dir, z_dir = (1.,0.,0.), (0.,1.,0.), (0.,0.,1.)
        else:                   # -Z face: x=+X, y=-Y, z=-Z  (right-hand: x×y=z)
            x_dir, y_dir, z_dir = (1.,0.,0.), (0.,-1.,0.), (0.,0.,-1.)
    elif face_axis == 0:        # ±X faces — outward z = sign(nx) · X̂
        if nx >= 0:             # +X face: x=+Y, y=+Z, z=+X
            x_dir, y_dir, z_dir = (0.,1.,0.), (0.,0.,1.), (1.,0.,0.)
        else:                   # -X face: x=+Y, y=-Z, z=-X  (right-hand: x×y=z)
            x_dir, y_dir, z_dir = (0.,1.,0.), (0.,0.,-1.), (-1.,0.,0.)
    else:                       # ±Y faces — outward z = sign(ny) · Ŷ
        if ny >= 0:             # +Y face: x=+Z, y=+X, z=+Y
            x_dir, y_dir, z_dir = (0.,0.,1.), (1.,0.,0.), (0.,1.,0.)
        else:                   # -Y face: x=+Z, y=-X, z=-Y  (right-hand: x×y=z)
            x_dir, y_dir, z_dir = (0.,0.,1.), (-1.,0.,0.), (0.,-1.,0.)

    return JointGeom(pos=pos, x_dir=x_dir, y_dir=y_dir, z_dir=z_dir)


def _cylinder_joint_geom(coords: list[str], radius: float, height: float) -> JointGeom:
    """Compute joint geometry for a cylinder surface joint (nr:nt:nh coords).

    Frame convention: outward normal — z-axis is the actual outward normal at the
    joint location. End-face z = ±Ẑ (sign follows h). Side-face z = radial outward.
    All frames are right-handed.
    """
    if len(coords) != 3:
        raise TranspileError(f"cylinder surface joint needs 3 coords, got {coords}")
    nr, nt, nh = (parse_frac(c) for c in coords)
    theta = nt * math.pi
    cos_t = round(math.cos(theta), 12)
    sin_t = round(math.sin(theta), 12)
    pos: Vec3 = (
        nr * float(radius) * cos_t,
        nr * float(radius) * sin_t,
        nh * float(height) / 2.0,
    )

    if abs(nh) >= 1.0 - 1e-9:
        # End face: outward normal = sign(nh) · Ẑ
        if nh >= 0:             # top: x=+X, y=+Y, z=+Z
            x_dir: Vec3 = (1., 0., 0.)
            y_dir: Vec3 = (0., 1., 0.)
            z_dir: Vec3 = (0., 0., 1.)
        else:                   # bottom: x=+X, y=-Y, z=-Z  (right-hand)
            x_dir = (1., 0., 0.)
            y_dir = (0., -1., 0.)
            z_dir = (0., 0., -1.)
    else:
        # Side face: outward normal = actual radial direction at angle theta
        z_dir = (cos_t, sin_t, 0.0)          # radial outward
        y_dir = (0.0, 0.0, 1.0)              # axial +Z
        x_dir = (-sin_t, cos_t, 0.0)         # CCW tangent (right-hand: x×y=z)

    return JointGeom(pos=pos, x_dir=x_dir, y_dir=y_dir, z_dir=z_dir)


def _box_joint_geom_inward(coords: list[str], size: list[float]) -> JointGeom:
    """Compute joint geometry for a box surface joint with INWARD normal (si type).

    Position: same as the outward joint at the same coords.
    Frame: same as the outward joint on the OPPOSITE face of the same axis.
      e.g. rg:si:0:0:-1 (bottom face, inward) → z=+Z, same frame as rg:s:0:0:1 (top, outward)

    This means connect_to(outward_A, inward_B) where B's inward face is the touching
    face produces pure translation — no rotation.  Right-hand rule holds for all frames.
    """
    if len(coords) != 3:
        raise TranspileError(f"box surface joint needs 3 coords, got {coords}")
    nx, ny, nz = (parse_frac(c) for c in coords)
    dx, dy, dz = float(size[0]), float(size[1]), float(size[2])
    pos: Vec3 = (nx * dx / 2.0, ny * dy / 2.0, nz * dz / 2.0)

    absvals = [abs(nx), abs(ny), abs(nz)]
    face_axis = absvals.index(max(absvals))

    # Frame = outward frame of the OPPOSITE face on the same axis (flip dominant sign).
    if face_axis == 2:
        if nz >= 0:   # +Z face inward → use -Z face outward frame: x=+X, y=-Y, z=-Z
            x_dir, y_dir, z_dir = (1.,0.,0.), (0.,-1.,0.), (0.,0.,-1.)
        else:         # -Z face inward → use +Z face outward frame: x=+X, y=+Y, z=+Z
            x_dir, y_dir, z_dir = (1.,0.,0.), (0.,1.,0.), (0.,0.,1.)
    elif face_axis == 0:
        if nx >= 0:   # +X face inward → use -X face outward frame: x=+Y, y=-Z, z=-X
            x_dir, y_dir, z_dir = (0.,1.,0.), (0.,0.,-1.), (-1.,0.,0.)
        else:         # -X face inward → use +X face outward frame: x=+Y, y=+Z, z=+X
            x_dir, y_dir, z_dir = (0.,1.,0.), (0.,0.,1.), (1.,0.,0.)
    else:
        if ny >= 0:   # +Y face inward → use -Y face outward frame: x=+Z, y=-X, z=-Y
            x_dir, y_dir, z_dir = (0.,0.,1.), (-1.,0.,0.), (0.,-1.,0.)
        else:         # -Y face inward → use +Y face outward frame: x=+Z, y=+X, z=+Y
            x_dir, y_dir, z_dir = (0.,0.,1.), (1.,0.,0.), (0.,1.,0.)

    return JointGeom(pos=pos, x_dir=x_dir, y_dir=y_dir, z_dir=z_dir)


def _cylinder_joint_geom_inward(coords: list[str], radius: float, height: float) -> JointGeom:
    """Compute joint geometry for a cylinder surface joint with INWARD normal (si type).

    Position: same as the outward joint at the same coords.
    Frame for end faces: same as the outward joint on the OPPOSITE end.
    Frame for side faces: z points radially inward (toward cylinder axis).

    The key property: rg:si:0:0:-1 (bottom inward) has z=+Z = same frame as
    rg:s:0:0:1 (top outward), enabling no-rotation stacking via connect_to.
    """
    if len(coords) != 3:
        raise TranspileError(f"cylinder surface joint needs 3 coords, got {coords}")
    nr, nt, nh = (parse_frac(c) for c in coords)
    theta = nt * math.pi
    cos_t = round(math.cos(theta), 12)
    sin_t = round(math.sin(theta), 12)
    pos: Vec3 = (
        nr * float(radius) * cos_t,
        nr * float(radius) * sin_t,
        nh * float(height) / 2.0,
    )

    if abs(nh) >= 1.0 - 1e-9:
        # End face inward = outward frame of the opposite end.
        if nh >= 0:   # top inward → use bottom outward frame: x=+X, y=-Y, z=-Z
            x_dir: Vec3 = (1., 0., 0.)
            y_dir: Vec3 = (0., -1., 0.)
            z_dir: Vec3 = (0., 0., -1.)
        else:         # bottom inward → use top outward frame: x=+X, y=+Y, z=+Z
            x_dir = (1., 0., 0.)
            y_dir = (0., 1., 0.)
            z_dir = (0., 0., 1.)
    else:
        # Side face inward: z = radially inward (toward axis), y = axial +Z,
        # x chosen so x×y = z (right-hand).
        z_dir = (-cos_t, -sin_t, 0.0)        # radially inward
        y_dir = (0.0, 0.0, 1.0)              # axial +Z
        x_dir = (sin_t, -cos_t, 0.0)         # right-hand: x×y = (sin,-cos,0)×(0,0,1)
        #   = (-cos·1-0·0, 0·0-sin·1, sin·0-(-cos)·0) = (-cos,-sin,0) = z ✓

    return JointGeom(pos=pos, x_dir=x_dir, y_dir=y_dir, z_dir=z_dir)


# ─── Joint reference types ────────────────────────────────────────────────────


@dataclass
class SurfaceJointRef:
    kind_prefix: str   # "rg" (RigidJoint) or "rv" (RevoluteJoint)
    type_prefix: str   # "s" (outward normal) or "si" (inward normal)
    coords: list[str]
    raw_id: str        # the full id string, e.g. "rg:s:0:0:1" or "rg:si:0:0:-1"


@dataclass
class CustomJointRef:
    raw_id: str        # e.g. "rg:c:0:0:-1"
    kind: str          # "RigidJoint" or "RevoluteJoint"
    coords: list[str]  # [a, b, c] normalised strings (same scheme as surface joints)
    frame: str


JointRef = SurfaceJointRef | CustomJointRef


def parse_joint_ref(raw: Any) -> JointRef:
    """
    Parse a joint reference object from the mates section.

    Expected formats:
      { "id": "rg:s:0:0:1" }                           surface RigidJoint  (outward normal)
      { "id": "rg:si:0:0:-1" }                          surface RigidJoint  (inward normal)
      { "id": "rv:s:0:1:0" }                            surface RevoluteJoint (outward)
      { "id": "rv:si:0:1:0" }                           surface RevoluteJoint (inward)
      { "id": "rg:c:0:30:5",  "frame": "..." }          custom RigidJoint
      { "id": "rv:c:0:0:10",  "frame": "..." }          custom RevoluteJoint

    Surface joint coords are normalised fractions (e.g. 1/2, -1).
    Custom joint id encodes the origin in absolute mm as x:y:z. The 'frame' field is
    required for custom joints; 'origin' is not accepted (coords come from the id).
    """
    if not isinstance(raw, dict):
        raise TranspileError(
            f"joint ref must be an object with an 'id' field "
            f"(e.g. {{\"id\": \"rg:s:0:0:1\"}}), got {type(raw).__name__}"
        )

    id_str = str(raw.get("id", "")).strip()
    # Split into at most 3 parts: kind_prefix : type_prefix : rest
    parts = id_str.split(":", 2)
    if len(parts) < 3:
        raise TranspileError(
            f"joint id must have format '{{rg|rv}}:{{s|c}}:{{coords}}', "
            f"got {id_str!r}"
        )

    kind_prefix, type_prefix, rest = parts[0], parts[1], parts[2]

    if kind_prefix not in ("rg", "rv"):
        raise TranspileError(
            f"joint id kind prefix must be 'rg' (RigidJoint) or 'rv' (RevoluteJoint), "
            f"got {kind_prefix!r} in {id_str!r}"
        )
    if type_prefix not in ("s", "si", "c"):
        raise TranspileError(
            f"joint id type prefix must be 's' (surface outward), 'si' (surface inward), "
            f"or 'c' (custom), got {type_prefix!r} in {id_str!r}"
        )

    coords = rest.split(":")

    if type_prefix in ("s", "si"):
        return SurfaceJointRef(
            kind_prefix=kind_prefix,
            type_prefix=type_prefix,
            coords=coords,
            raw_id=id_str,
        )

    # type_prefix == "c"  →  custom joint
    if len(coords) != 3:
        raise TranspileError(
            f"custom joint id must encode origin as 'rg:c:x:y:z', "
            f"got {id_str!r} ({len(coords)} coord segment(s))"
        )
    kind = "RigidJoint" if kind_prefix == "rg" else "RevoluteJoint"
    frame_raw = raw.get("frame")
    if not frame_raw:
        raise TranspileError(
            f"custom joint {id_str!r} is missing required 'frame' field"
        )
    frame = str(frame_raw)
    return CustomJointRef(raw_id=id_str, kind=kind, coords=coords, frame=frame)


# ─── Joint geometry from ref ─────────────────────────────────────────────────


def joint_geom_for_ref(ref: JointRef, prim: dict) -> JointGeom:
    """Compute physical position and frame for a joint ref given its part's primitive."""
    if isinstance(ref, SurfaceJointRef):
        kind = prim.get("kind")
        if ref.type_prefix == "s":
            if kind == "box":
                return _box_joint_geom(ref.coords, prim["size"])
            if kind == "cylinder":
                return _cylinder_joint_geom(ref.coords, prim["radius"], prim["height"])
        elif ref.type_prefix == "si":
            if kind == "box":
                return _box_joint_geom_inward(ref.coords, prim["size"])
            if kind == "cylinder":
                return _cylinder_joint_geom_inward(ref.coords, prim["radius"], prim["height"])
        raise TranspileError(f"unsupported primitive kind {kind!r}")
    # CustomJointRef — coords are NORMALISED (same fraction scheme as surface joints).
    # For box:      x:y:z where each component is normalised to the half-dimension
    #               (same as surface joint ids).  e.g. "0:0:-1" → (0, 0, -dz/2).
    # For cylinder: r:t:h using the same (radius, angular-half-circle, half-height)
    #               convention as cylinder surface joints.
    x_dir, y_dir, z_dir = parse_frame(ref.frame)
    kind = prim.get("kind")
    if kind == "box":
        nx, ny, nz = (parse_frac(c) for c in ref.coords)
        dx, dy, dz = float(prim["size"][0]), float(prim["size"][1]), float(prim["size"][2])
        pos: Vec3 = (nx * dx / 2.0, ny * dy / 2.0, nz * dz / 2.0)
    elif kind == "cylinder":
        nr, nt, nh = (parse_frac(c) for c in ref.coords)
        theta = nt * math.pi
        cos_t = round(math.cos(theta), 12)
        sin_t = round(math.sin(theta), 12)
        pos = (
            nr * float(prim["radius"]) * cos_t,
            nr * float(prim["radius"]) * sin_t,
            nh * float(prim["height"]) / 2.0,
        )
    else:
        raise TranspileError(
            f"unsupported primitive kind {kind!r} for custom joint {ref.raw_id!r}"
        )
    return JointGeom(pos=pos, x_dir=x_dir, y_dir=y_dir, z_dir=z_dir)


# ─── Joint kind (Rigid or Revolute) ──────────────────────────────────────────


def joint_kind(ref: JointRef) -> str:
    """Return 'RigidJoint' or 'RevoluteJoint' for a joint ref."""
    if isinstance(ref, SurfaceJointRef):
        return "RigidJoint" if ref.kind_prefix == "rg" else "RevoluteJoint"
    return ref.kind


# ─── Topological sort ────────────────────────────────────────────────────────


def _topo_order(mates: list[dict]) -> list[int]:
    """
    Return mate indices in topological order (parent connect_to before child).

    Guarantees that when base.joints[...].connect_to(child.joints[...]) is called,
    `base` has already been positioned in the world by any earlier mate that moved it.
    """
    moved_by: dict[str, int] = {}     # part_id → mate index that moves it
    children_of: dict[str, list[int]] = defaultdict(list)  # part_id → [mate indices where it's partA]

    for i, mate in enumerate(mates):
        part_b = mate["partB"]
        part_a = mate["partA"]
        if part_b in moved_by:
            raise TranspileError(
                f"part {part_b!r} appears as partB in multiple mates; "
                "mates must form a tree (each part moved at most once)"
            )
        moved_by[part_b] = i
        children_of[part_a].append(i)

    all_part_ids: set[str] = set()
    for mate in mates:
        all_part_ids.add(mate["partA"])
        all_part_ids.add(mate["partB"])

    roots = sorted(pid for pid in all_part_ids if pid not in moved_by)
    result: list[int] = []
    visited: set[str] = set(roots)
    queue = list(roots)

    while queue:
        part = queue.pop(0)
        for mate_idx in children_of[part]:
            result.append(mate_idx)
            child = mates[mate_idx]["partB"]
            if child not in visited:
                visited.add(child)
                queue.append(child)

    if len(result) != len(mates):
        raise TranspileError("mates do not form a valid tree (possible cycle)")

    return result


# ─── Code generation ─────────────────────────────────────────────────────────


def _joint_creation_code(label: str, var: str, ref: JointRef, geom: JointGeom) -> list[str]:
    """Generate the build123d joint constructor call(s) for one joint."""
    lines: list[str] = []
    kind = joint_kind(ref)

    if kind == "RigidJoint":
        lines.append(f"    RigidJoint({label!r}, {var}, {geom.location_code()})")
    elif kind == "RevoluteJoint":
        axis_orig = _fmt_vec(geom.pos)
        axis_dir = _fmt_vec(geom.z_dir)
        angle_ref = _fmt_vec(geom.x_dir)
        lines.append(f"    RevoluteJoint({label!r}, {var},")
        lines.append(f"        axis=Axis({axis_orig}, {axis_dir}),")
        lines.append(f"        angle_reference={angle_ref})")
    else:
        raise TranspileError(f"unexpected joint kind {kind!r}")
    return lines


def transpile(spec: dict) -> str:
    """
    Transpile a declarative assembly spec dict to a build123d Python script string.

    The returned string defines a gen_step() function suitable for the CAD harness.
    """
    meta = spec.get("meta", {})
    raw_parts = spec.get("parts", [])
    raw_mates = spec.get("mates", [])
    title = str(meta.get("title", "assembly"))

    # ── Validate & index parts ────────────────────────────────────────────────
    part_prims: dict[str, dict] = {}   # part_id → primitive dict
    part_order: list[str] = []
    for i, p in enumerate(raw_parts):
        pid = str(p.get("id", "")).strip()
        if not pid:
            raise TranspileError(f"parts[{i}] is missing 'id'")
        if pid in part_prims:
            raise TranspileError(f"duplicate part id {pid!r}")
        prim = p.get("primitive")
        if not isinstance(prim, dict):
            raise TranspileError(f"parts[{i}] 'primitive' must be an object")
        kind = prim.get("kind")
        if kind not in ("box", "cylinder"):
            raise TranspileError(f"parts[{i}] unsupported primitive kind {kind!r}")
        part_prims[pid] = prim
        part_order.append(pid)

    if not part_order:
        raise TranspileError("spec must define at least one part")

    # ── Parse mates ───────────────────────────────────────────────────────────
    parsed_mates: list[tuple[str, JointRef, str, JointRef, float | None]] = []
    for i, m in enumerate(raw_mates):
        part_a = str(m.get("partA", "")).strip()
        part_b = str(m.get("partB", "")).strip()
        if part_a not in part_prims:
            raise TranspileError(f"mates[{i}] partA={part_a!r} not found in parts")
        if part_b not in part_prims:
            raise TranspileError(f"mates[{i}] partB={part_b!r} not found in parts")

        ref_a = parse_joint_ref(m.get("jointA"))
        ref_b = parse_joint_ref(m.get("jointB"))

        kind_a = joint_kind(ref_a)
        kind_b = joint_kind(ref_b)
        if kind_a == "RevoluteJoint" and kind_b == "RevoluteJoint":
            raise TranspileError(
                f"mates[{i}] both joints are RevoluteJoint; "
                "connect_to requires at most one Revolute per pair"
            )

        angle_raw = m.get("angle")
        angle: float | None = float(angle_raw) if angle_raw is not None else None

        parsed_mates.append((part_a, ref_a, part_b, ref_b, angle))

    # ── Topological order ─────────────────────────────────────────────────────
    topo_indices = _topo_order(raw_mates)

    # ── Collect joints needed (deduplicated) ──────────────────────────────────
    # Key: (part_id, joint_key_string) → (build123d_label, ref)
    joint_registry: dict[tuple[str, str], tuple[str, JointRef]] = {}
    used_labels: set[str] = set()

    def _joint_key(ref: JointRef) -> str:
        if isinstance(ref, SurfaceJointRef):
            return ref.raw_id
        return ref.raw_id

    def _get_or_create_label(part_id: str, ref: JointRef) -> str:
        key = (part_id, _joint_key(ref))
        if key in joint_registry:
            return joint_registry[key][0]
        base = _label_safe(_joint_key(ref))
        candidate = base
        counter = 1
        while candidate in used_labels:
            candidate = f"{base}_{counter}"
            counter += 1
        used_labels.add(candidate)
        joint_registry[key] = (candidate, ref)
        return candidate

    # Walk mates in topo order to register joints
    for part_a, ref_a, part_b, ref_b, _angle in (parsed_mates[i] for i in topo_indices):
        _get_or_create_label(part_a, ref_a)
        _get_or_create_label(part_b, ref_b)

    # ── Emit Python ───────────────────────────────────────────────────────────
    lines: list[str] = []

    # Header (harness-compatible gen_step metadata; step output is auto-derived by harness)
    safe_title = _label_safe(title)
    lines += [
        f"# Transpiled from declarative assembly spec: {title}",
        "from build123d import *",
        "from math import cos, sin, pi",
        "",
        "",
        "def gen_step():",
    ]

    # Parts
    lines.append("    # --- parts ---")
    for pid in part_order:
        var = _label_safe(pid)
        prim = part_prims[pid]
        if prim["kind"] == "box":
            dx, dy, dz = prim["size"]
            lines.append(f"    {var} = Box({_fmt_f(dx)}, {_fmt_f(dy)}, {_fmt_f(dz)})")
        elif prim["kind"] == "cylinder":
            r = prim["radius"]
            h = prim["height"]
            lines.append(f"    {var} = Cylinder({_fmt_f(r)}, {_fmt_f(h)})")
    lines.append("")

    # Joints – emit in topo order so part variables are clear
    # Collect per-part joints in order
    per_part_joints: dict[str, list[tuple[str, JointRef]]] = defaultdict(list)
    seen_keys: set[tuple[str, str]] = set()
    for part_a, ref_a, part_b, ref_b, _angle in (parsed_mates[i] for i in topo_indices):
        for pid, ref in ((part_a, ref_a), (part_b, ref_b)):
            key = (pid, _joint_key(ref))
            if key not in seen_keys:
                seen_keys.add(key)
                label = joint_registry[key][0]
                per_part_joints[pid].append((label, ref))

    lines.append("    # --- joints ---")
    for pid in part_order:
        joints = per_part_joints.get(pid, [])
        if not joints:
            continue
        var = _label_safe(pid)
        prim = part_prims[pid]
        for label, ref in joints:
            geom = joint_geom_for_ref(ref, prim)
            lines += _joint_creation_code(label, var, ref, geom)
    lines.append("")

    # Mates
    lines.append("    # --- mates ---")
    for idx in topo_indices:
        part_a, ref_a, part_b, ref_b, angle = parsed_mates[idx]
        var_a = _label_safe(part_a)
        var_b = _label_safe(part_b)
        label_a = _get_or_create_label(part_a, ref_a)
        label_b = _get_or_create_label(part_b, ref_b)
        if angle is not None:
            lines.append(
                f"    {var_a}.joints[{label_a!r}].connect_to("
                f"{var_b}.joints[{label_b!r}], angle={_fmt_f(angle)})"
            )
        else:
            lines.append(
                f"    {var_a}.joints[{label_a!r}].connect_to({var_b}.joints[{label_b!r}])"
            )
    lines.append("")

    # Assembly return
    lines.append("    # --- assembly ---")
    part_vars = ", ".join(_label_safe(pid) for pid in part_order)
    lines.append(f"    return Compound(children=[{part_vars}])")
    lines.append("")

    return "\n".join(lines)


def transpile_file(input_path: str | object, output_path: str | object | None = None) -> str:
    """
    Transpile a JSON spec file to a Python script.

    Returns the output file path as a string.
    """
    import json
    from pathlib import Path

    in_path = Path(str(input_path)).resolve()
    if not in_path.exists():
        raise FileNotFoundError(f"spec file not found: {in_path}")
    try:
        spec = json.loads(in_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise TranspileError(f"invalid JSON in {in_path}: {exc}") from exc
    if not isinstance(spec, dict):
        raise TranspileError(f"spec must be a JSON object, got {type(spec).__name__}")

    code = transpile(spec)

    if output_path is None:
        out_path = in_path.with_suffix(".py")
    else:
        out_path = Path(str(output_path)).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code, encoding="utf-8")
    return str(out_path)
