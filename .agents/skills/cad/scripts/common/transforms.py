from __future__ import annotations

IDENTITY_TRANSFORM = (
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
)


def multiply_transforms(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    product: list[float] = []
    for row in range(4):
        for column in range(4):
            value = 0.0
            for index in range(4):
                value += left[row * 4 + index] * right[index * 4 + column]
            product.append(value)
    return tuple(product)


def invert_affine_transform(transform: tuple[float, ...]) -> tuple[float, ...]:
    a, b, c, tx, d, e, f, ty, g, h, i, tz = transform[:12]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) <= 1e-12:
        return IDENTITY_TRANSFORM
    inv_det = 1.0 / det
    r00 = (e * i - f * h) * inv_det
    r01 = (c * h - b * i) * inv_det
    r02 = (b * f - c * e) * inv_det
    r10 = (f * g - d * i) * inv_det
    r11 = (a * i - c * g) * inv_det
    r12 = (c * d - a * f) * inv_det
    r20 = (d * h - e * g) * inv_det
    r21 = (b * g - a * h) * inv_det
    r22 = (a * e - b * d) * inv_det
    return (
        r00,
        r01,
        r02,
        -((r00 * tx) + (r01 * ty) + (r02 * tz)),
        r10,
        r11,
        r12,
        -((r10 * tx) + (r11 * ty) + (r12 * tz)),
        r20,
        r21,
        r22,
        -((r20 * tx) + (r21 * ty) + (r22 * tz)),
        0.0,
        0.0,
        0.0,
        1.0,
    )


def relative_transform(parent_world_transform: tuple[float, ...], world_transform: tuple[float, ...]) -> tuple[float, ...]:
    return multiply_transforms(invert_affine_transform(parent_world_transform), world_transform)


def location_from_transform(transform: tuple[float, ...]):
    import build123d
    from OCP.gp import gp_Trsf

    trsf = gp_Trsf()
    trsf.SetValues(
        transform[0],
        transform[1],
        transform[2],
        transform[3],
        transform[4],
        transform[5],
        transform[6],
        transform[7],
        transform[8],
        transform[9],
        transform[10],
        transform[11],
    )
    return build123d.Location(trsf)
