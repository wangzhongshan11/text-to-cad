/**
 * Indexed mesh data for URDF primitive visuals (box / cylinder / sphere),
 * compatible with buildUrdfMeshGeometry expectations (vertices, normals, indices).
 */

function pushTriangle(indices, a, b, c) {
  indices.push(a, b, c);
}

/**
 * Axis-aligned box centered at origin. `size` is [sx, sy, sz] full extents (URDF).
 */
export function buildBoxMeshData(size) {
  const [sx, sy, sz] = size;
  const hx = sx * 0.5;
  const hy = sy * 0.5;
  const hz = sz * 0.5;

  const vertices = new Float32Array([
    -hx, -hy, hz, hx, -hy, hz, hx, hy, hz, -hx, hy, hz,
    -hx, -hy, -hz, -hx, hy, -hz, hx, hy, -hz, hx, -hy, -hz,
    -hx, hy, -hz, -hx, hy, hz, hx, hy, hz, hx, hy, -hz,
    -hx, -hy, -hz, hx, -hy, -hz, hx, -hy, hz, -hx, -hy, hz,
    hx, -hy, -hz, hx, hy, -hz, hx, hy, hz, hx, -hy, hz,
    -hx, -hy, -hz, -hx, -hy, hz, -hx, hy, hz, -hx, hy, -hz
  ]);

  const normals = new Float32Array([
    0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1,
    0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1,
    0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0,
    0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0,
    1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0,
    -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0
  ]);

  const indices = new Uint32Array([
    0, 1, 2, 0, 2, 3,
    4, 5, 6, 4, 6, 7,
    8, 9, 10, 8, 10, 11,
    12, 13, 14, 12, 14, 15,
    16, 17, 18, 16, 18, 19,
    20, 21, 22, 20, 22, 23
  ]);

  return { vertices, normals, indices };
}

/**
 * Cylinder along +Z, centered at origin. URDF: radius and length.
 */
export function buildCylinderMeshData(radius, length, segments = 24) {
  const seg = Math.max(8, Math.floor(segments));
  const half = length * 0.5;
  const positions = [];
  const normals = [];
  const indices = [];

  const bottomCenter = positions.length / 3;
  positions.push(0, 0, -half);
  normals.push(0, 0, -1);

  const topCenter = positions.length / 3;
  positions.push(0, 0, half);
  normals.push(0, 0, 1);

  const bottomRing = [];
  const topRing = [];
  for (let i = 0; i < seg; i += 1) {
    const t = (i / seg) * Math.PI * 2;
    const c = Math.cos(t) * radius;
    const s = Math.sin(t) * radius;
    bottomRing.push(positions.length / 3);
    positions.push(c, s, -half);
    normals.push(0, 0, -1);
    topRing.push(positions.length / 3);
    positions.push(c, s, half);
    normals.push(0, 0, 1);
  }

  const sideBase = positions.length / 3;
  for (let i = 0; i < seg; i += 1) {
    const t = (i / seg) * Math.PI * 2;
    const t2 = ((i + 1) / seg) * Math.PI * 2;
    const c = Math.cos(t) * radius;
    const s = Math.sin(t) * radius;
    const c2 = Math.cos(t2) * radius;
    const s2 = Math.sin(t2) * radius;
    const nx = Math.cos(t);
    const ny = Math.sin(t);
    const nx2 = Math.cos(t2);
    const ny2 = Math.sin(t2);
    positions.push(c, s, -half, c2, s2, -half, c2, s2, half, c, s, half);
    normals.push(nx, ny, 0, nx2, ny2, 0, nx2, ny2, 0, nx, ny, 0);
    const b = sideBase + i * 4;
    pushTriangle(indices, b, b + 1, b + 2);
    pushTriangle(indices, b, b + 2, b + 3);
  }

  for (let i = 0; i < seg; i += 1) {
    const i1 = (i + 1) % seg;
    pushTriangle(indices, bottomCenter, bottomRing[i1], bottomRing[i]);
    pushTriangle(indices, topCenter, topRing[i], topRing[i1]);
  }

  return {
    vertices: new Float32Array(positions),
    normals: new Float32Array(normals),
    indices: new Uint32Array(indices)
  };
}

/**
 * Sphere centered at origin (URDF sphere uses radius only).
 */
export function buildSphereMeshData(radius, rings = 12, segments = 24) {
  const rSeg = Math.max(8, Math.floor(segments));
  const rRings = Math.max(4, Math.floor(rings));
  const positions = [];
  const normals = [];
  const indices = [];

  for (let ring = 0; ring <= rRings; ring += 1) {
    const v = ring / rRings;
    const phi = v * Math.PI;
    const sinPhi = Math.sin(phi);
    const cosPhi = Math.cos(phi);
    for (let seg = 0; seg < rSeg; seg += 1) {
      const u = seg / rSeg;
      const theta = u * Math.PI * 2;
      const sinTheta = Math.sin(theta);
      const cosTheta = Math.cos(theta);
      const nx = sinPhi * cosTheta;
      const ny = sinPhi * sinTheta;
      const nz = cosPhi;
      positions.push(nx * radius, ny * radius, nz * radius);
      normals.push(nx, ny, nz);
    }
  }

  const stride = rSeg;
  for (let ring = 0; ring < rRings; ring += 1) {
    for (let seg = 0; seg < rSeg; seg += 1) {
      const i0 = ring * stride + seg;
      const i1 = ring * stride + ((seg + 1) % rSeg);
      const i2 = (ring + 1) * stride + seg;
      const i3 = (ring + 1) * stride + ((seg + 1) % rSeg);
      pushTriangle(indices, i0, i2, i1);
      pushTriangle(indices, i1, i2, i3);
    }
  }

  return {
    vertices: new Float32Array(positions),
    normals: new Float32Array(normals),
    indices: new Uint32Array(indices)
  };
}

export function buildPrimitiveMeshData(primitive) {
  if (!primitive || typeof primitive !== "object") {
    return null;
  }
  const kind = String(primitive.kind || "").toLowerCase();
  if (kind === "box") {
    const size = primitive.size;
    if (!Array.isArray(size) || size.length !== 3) {
      return null;
    }
    return buildBoxMeshData(size);
  }
  if (kind === "cylinder") {
    const { radius, length } = primitive;
    if (!Number.isFinite(radius) || !Number.isFinite(length)) {
      return null;
    }
    return buildCylinderMeshData(radius, length, primitive.segments);
  }
  if (kind === "sphere") {
    const { radius } = primitive;
    if (!Number.isFinite(radius)) {
      return null;
    }
    return buildSphereMeshData(radius, primitive.rings, primitive.segments);
  }
  return null;
}
