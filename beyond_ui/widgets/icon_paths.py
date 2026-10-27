"""Retained outline paths in a unit square; sizes describe visible silhouettes."""

from functools import lru_cache
from math import cos, sin, tau, pi


def ring(x=0, y=0, r=0.5):
    return tuple(
        (x + r * cos(i * tau / 64), y + r * sin(i * tau / 64)) for i in range(65)
    )


@lru_cache(maxsize=32)
def paths(name):
    if name == "+":
        return (((-0.5, 0), (0.5, 0)), ((0, -0.5), (0, 0.5)))
    if name == "−":
        return (((-0.5, 0), (0.5, 0)),)
    if name in {"○", "material"}:
        return (ring(),)
    if name == "search":
        return (ring(-0.08, -0.08, 0.37), ((0.20, 0.20), (0.5, 0.5)))
    if name == "object":
        return (
            (
                (0, -0.5),
                (0.45, -0.24),
                (0.45, 0.25),
                (0, 0.5),
                (-0.45, 0.25),
                (-0.45, -0.24),
                (0, -0.5),
            ),
            ((-0.45, -0.24), (0, 0.02), (0.45, -0.24)),
            ((0, 0.02), (0, 0.5)),
        )
    if name == "camera":
        return (
            (
                (-0.5, 0.4),
                (0.5, 0.4),
                (0.5, -0.28),
                (0.23, -0.28),
                (0.14, -0.47),
                (-0.14, -0.47),
                (-0.23, -0.28),
                (-0.5, -0.28),
                (-0.5, 0.4),
            ),
            ring(0, 0.04, 0.22),
        )
    if name == "duplicate":
        return (
            (
                (-0.14, 0.12),
                (-0.44, 0.12),
                (-0.44, -0.46),
                (0.14, -0.46),
                (0.14, -0.24),
            ),
            (
                (-0.16, -0.20),
                (0.45, -0.20),
                (0.45, 0.44),
                (-0.16, 0.44),
                (-0.16, -0.20),
            ),
        )
    if name == "unlink":
        result = []
        d = (0.707, -0.707)
        n = (0.707, 0.707)
        c = (0.22, -0.22)
        r = 0.18
        arc = [
            (
                c[0] + r * (n[0] * cos(t) + d[0] * sin(t)),
                c[1] + r * (n[1] * cos(t) + d[1] * sin(t)),
            )
            for t in (i * pi / 24 for i in range(25))
        ]
        path = [
            (arc[0][0] - 0.32 * d[0], arc[0][1] - 0.32 * d[1]),
            *arc,
            (arc[-1][0] - 0.32 * d[0], arc[-1][1] - 0.32 * d[1]),
        ]
        result.append(tuple(path))
        result.append(tuple((-x, -y) for x, y in path))
        result.append(((-0.14, 0.14), (0.14, -0.14)))
        return tuple(result)
    if name == "eyedropper":
        return (
            (
                (-0.43, 0.46),
                (-0.35, 0.23),
                (0.17, -0.29),
                (0.31, -0.15),
                (-0.21, 0.37),
                (-0.43, 0.46),
            ),
            ((0.04, -0.39), (0.40, -0.03)),
            ((0.19, -0.26), (0.42, -0.49), (0.51, -0.40), (0.28, -0.17)),
        )
    return ()


@lru_cache(maxsize=256)
def transformed(name, rect, size):
    """Cache authored icon geometry independently of host position and DPI."""
    x, y, w, h = rect
    return tuple(
        value
        for path in paths(name)
        for value in (
            *((x + w / 2 + px * size, y + h / 2 + py * size) for px, py in path),
            None,
        )
    )
