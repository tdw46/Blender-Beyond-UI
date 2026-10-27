"""Small, vectorized material swatches from host-neutral shading snapshots.

No Blender imports, scene geometry, animation or renderer resources. This is a
thumbnail approximation under fixed studio light, not a material graph renderer.
"""

import math


def sample(
    texture,
    uv,
    transform=((0.0, 0.0, 1.0, 1.0), 0.0),
    sampler=("LINEAR", "LINEAR", "REPEAT", "REPEAT"),
):
    import numpy as np

    st, angle = transform
    # Match Beyond NPR's normalized nprUv transform and rotation convention.
    q = uv.copy() * st[2:]
    if angle:
        c, s = math.cos(angle), math.sin(angle)
        q = np.stack(
            (c * q[..., 0] + s * q[..., 1], -s * q[..., 0] + c * q[..., 1]), axis=-1
        )
    q += st[:2]
    h, w = texture.shape[:2]

    def wrap(values, mode):
        if mode == "CLAMP_TO_EDGE":
            return np.clip(values, 0, 1)
        if mode == "MIRRORED_REPEAT":
            return 1 - np.abs(np.mod(values, 2) - 1)
        return np.mod(values, 1)

    u, v = wrap(q[..., 0], sampler[2]), wrap(q[..., 1], sampler[3])

    def index(values, size, mode):
        return (
            np.mod(values, size) if mode == "REPEAT" else np.clip(values, 0, size - 1)
        )

    if sampler[0] == "NEAREST":
        return texture[
            index((v * h).astype(int), h, sampler[3]),
            index((u * w).astype(int), w, sampler[2]),
        ]
    x, y = u * w - 0.5, v * h - 0.5
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    a = texture[index(y0, h, sampler[3]), index(x0, w, sampler[2])]
    b = texture[index(y0, h, sampler[3]), index(x0 + 1, w, sampler[2])]
    c = texture[index(y0 + 1, h, sampler[3]), index(x0, w, sampler[2])]
    d = texture[index(y0 + 1, h, sampler[3]), index(x0 + 1, w, sampler[2])]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def shade(parameters, textures, size=64):
    import numpy as np

    p = parameters
    axis = (np.arange(size, dtype=np.float32) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    r2 = x * x + y * y
    z = np.sqrt(np.maximum(0, 1 - r2))
    n = np.stack((x, y, z), axis=-1)
    # A complete texture spans the visible hemisphere: recognizable even for
    # atlas materials. This is a preview domain, not the character's mesh UVs.
    uv = np.stack(
        (
            np.arctan2(x, np.maximum(z, 1e-6)) / np.pi + 0.5,
            np.arcsin(np.clip(y, -1, 1)) / np.pi + 0.5,
        ),
        axis=-1,
    )

    def tex(key, coords=uv):
        source = textures.get(key)
        if source is None:
            return np.ones((*x.shape, 4), dtype=np.float32)
        return sample(
            source,
            coords,
            p.get("transforms", {}).get(key, ((0.0, 0.0, 1.0, 1.0), 0.0)),
            p.get("samplers", {}).get(key, ("LINEAR", "LINEAR", "REPEAT", "REPEAT")),
        )

    if "normal" in textures:
        normal = tex("normal")[..., :3] * 2 - 1
        normal[..., :2] *= p.get("normal_scale", 1.0)
        tangent = np.stack((z, np.zeros_like(z), -x), axis=-1)
        tangent /= np.maximum(1e-6, np.linalg.norm(tangent, axis=-1, keepdims=True))
        bitangent = np.cross(n, tangent)
        n = (
            tangent * normal[..., 0:1]
            + bitangent * normal[..., 1:2]
            + n * normal[..., 2:3]
        )
        n /= np.maximum(1e-6, np.linalg.norm(n, axis=-1, keepdims=True))
    light = np.array((-0.65, 0.50, 0.57), dtype=np.float32)
    light /= np.linalg.norm(light)
    ndl = np.sum(n * light, axis=-1)
    base = tex("base") * p.get("base_color", (1.0, 1.0, 1.0, 1.0))
    lit = base[..., :3]
    kind = p.get("kind", "PBR")
    if kind == "MTOON" or kind == "TOON":
        shift = p.get("shading_shift", 0.0)
        if "shift" in textures:
            shift = shift + tex("shift")[..., 0] * p.get("shading_shift_scale", 0.0)
        width = max(0.001, 1 - p.get("shading_toony", 0.9))
        band = np.clip((ndl + shift + width) / (2 * width), 0, 1)[..., None]
        dark = tex("shade")[..., :3] * p.get("shade_color", (0.4, 0.4, 0.4))
        if kind == "TOON":
            dark = lit * p.get("shade_color", (0.3, 0.3, 0.3))
        rgb = dark * (1 - band) + lit * band
    elif kind == "UNLIT":
        rgb = lit.copy()
    else:
        rough = np.clip(p.get("roughness", 0.5) * tex("roughness")[..., 0], 0.025, 1.0)
        metal = np.clip(p.get("metallic", 0.0) * tex("metallic")[..., 0], 0, 1)[
            ..., None
        ]
        half = light + np.array((0.0, 0.0, 1.0))
        half /= np.linalg.norm(half)
        spec = np.maximum(0, np.sum(n * half, axis=-1)) ** np.minimum(
            512.0, 2 / (rough * rough) - 1
        )
        reflection = 0.08 * p.get("specular", 0.5) * (1 - metal) + lit * metal
        rgb = (
            lit * (0.20 + 0.80 * np.maximum(0, ndl)[..., None]) * (1 - metal * 0.6)
            + reflection * spec[..., None] * 2
        )
    if kind == "MTOON":
        fresnel = np.clip(1 - n[..., 2] + p.get("rim_lift", 0.0), 0, 1) ** max(
            0.001, p.get("rim_power", 1.0)
        )
        rim = fresnel[..., None] * p.get("rim", (0.0, 0.0, 0.0)) * tex("rim")[..., :3]
        rgb += rim * (1 - 0.15 * p.get("rim_mix", 0.0))
        if "matcap" in textures:
            rgb += tex("matcap", n[..., :2] * 0.5 + 0.5)[..., :3] * p.get(
                "matcap", (1.0, 1.0, 1.0)
            )
    rgb += (
        tex("emissive")[..., :3]
        * p.get("emissive", (0.0, 0.0, 0.0))
        * p.get("emissive_strength", 1.0)
    )
    alpha = (
        base[..., 3]
        if kind == "MTOON"
        else np.full_like(z, p.get("base_color", (1, 1, 1, 1))[3])
    )
    if "alpha" in textures:
        alpha = alpha * tex("alpha")[..., p.get("alpha_channel", 3)]
    mode = p.get("alpha_mode", 0)
    if mode == 0:
        alpha = np.ones_like(alpha)
    elif mode == 1:
        alpha = (alpha >= p.get("alpha_cutoff", 0.5)).astype(np.float32)
    edge = np.clip((1 - np.sqrt(r2)) * size * 0.5, 0, 1)
    if p.get("outline_mode", 0) and p.get("outline_width", 0) > 0:
        ring = np.clip((np.sqrt(r2) - 0.94) / 0.04, 0, 1)[..., None]
        rgb = rgb * (1 - ring) + np.asarray(p.get("outline", (0, 0, 0))) * ring
    return np.dstack((np.maximum(0, rgb), alpha * edge)).astype(np.float32)
