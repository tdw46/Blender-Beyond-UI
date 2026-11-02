"""Original Blender SVG glyphs in one retained, theme-tinted atlas.

Generated offline; no RNA reads, files, image datablocks or allocations in draw.
"""

from pathlib import Path
import json, zlib

_texture = _shader = _batch = None
_entries = {}
_ink_bounds = {}
_dimensions = (1, 1)
_artwork = {}


def register_artwork(owner, sources, entries):
    if owner in _artwork:
        raise ValueError('Artwork namespace already registered')
    if len(_artwork) >= 16 or len(sources) > 8 or len(entries) > 128:
        raise ValueError('Artwork registry capacity exceeded')
    _artwork[owner] = dict(sources=sources, entries=entries, textures={})
    if _texture is not None:
        try:
            _prepare_artwork()
        except Exception:
            unregister_artwork(owner)
            raise


def unregister_artwork(owner):
    _artwork.pop(owner, None)


def _prepare_artwork():
    import gpu
    for pack in _artwork.values():
        for key, (width, height, raw) in pack['sources'].items():
            if key not in pack['textures']:
                # Pack bytes are bottom-up display-space RGBA, straight alpha.
                from array import array
                values = array('f', (v / 255 for v in raw))
                pack['textures'][key] = gpu.types.GPUTexture(
                    (width, height), format='RGBA8',
                    data=gpu.types.Buffer('FLOAT', len(values), values))


def prepare():
    global _texture, _shader, _batch, _entries, _ink_bounds, _dimensions
    if _texture is not None:
        _prepare_artwork()
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    root = Path(__file__).resolve().parents[1] / "assets/icons"
    spec = json.loads((root / "atlas.json").read_text())
    width, height = spec["dimensions"]
    raw = zlib.decompress((root / "atlas.rgba.zlib").read_bytes())
    assert len(raw) == width * height * 4
    texture = gpu.types.GPUTexture(
        (width, height),
        format="RGBA8",
        data=gpu.types.Buffer("FLOAT", len(raw), [v / 255 for v in raw]),
    )
    interface = gpu.types.GPUStageInterfaceInfo("beyond_source_icon_uv")
    interface.smooth("VEC2", "uv")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.sampler(0, "FLOAT_2D", "image")
    for kind, name in [
        ("MAT4", "mvp"),
        ("VEC4", "rect"),
        ("VEC4", "tile"),
        ("VEC4", "tint"),
        ("FLOAT", "colored"),
        ("VEC2", "sample_step"),
    ]:
        info.push_constant(kind, name)
    info.vertex_source(
        "void main(){uv=tile.xy+pos*tile.zw;gl_Position=mvp*vec4(rect.xy+pos*rect.zw,0.,1.);}"
    )
    info.fragment_source(
        "void main(){vec4 c=texture(image,uv);"
        "if(sample_step.x>0.){vec4 sum=vec4(0.);"
        "for(int i=0;i<4;i++){for(int j=0;j<4;j++){"
        "vec4 s=texture(image,uv+(vec2(float(i),float(j))-1.5)*sample_step);"
        "sum+=vec4(s.rgb*s.a,s.a);}}"
        "c=vec4(sum.rgb/max(sum.a,0.000001),sum.a/16.);}"
        "fragColor=vec4(mix(tint.rgb,c.rgb,colored),tint.a*c.a);}"
    )
    shader = gpu.shader.create_from_info(info)
    batch = batch_for_shader(
        shader,
        "TRIS",
        {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
        indices=((0, 1, 2), (2, 1, 3)),
    )
    _entries = spec["entries"]
    _ink_bounds = spec.get("ink_bounds", {})
    _dimensions = (width, height)
    _texture, _shader, _batch = texture, shader, batch
    _prepare_artwork()


def draw(name, x, y, size, color):
    if isinstance(name, str) and ':' in name:
        pack = _artwork.get(name.split(':', 1)[0])
        if pack is not None and name in pack['entries']:
            key, (a,b,w,h), tint = pack['entries'][name]
            texture = pack['textures'].get(key)
            if texture is None or _shader is None:
                return False
            import gpu
            tw, th, _ = pack['sources'][key]
            ratio = size / max(w,h)
            gpu.state.blend_set('ALPHA')
            _shader.bind()
            _shader.uniform_sampler('image', texture)
            _shader.uniform_float('mvp', gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix())
            _shader.uniform_float('rect', (x-w*ratio/2,y-h*ratio/2,w*ratio,h*ratio))
            _shader.uniform_float('tile', (a/tw,1-(b+h)/th,w/tw,h/th))
            _shader.uniform_float('tint', color)
            _shader.uniform_float('colored', 0.0 if tint else 1.0)
            _shader.uniform_float('sample_step', (1/(tw*ratio*4),1/(th*ratio*4)))
            _batch.draw(_shader)
            return True
    entry = _entries.get(name)
    if entry is None or _texture is None:
        return False
    import gpu

    a, b, w, h = entry
    left, top, right, bottom = _ink_bounds.get(name, (0, 0, w, h))
    ink_w, ink_h = right - left, bottom - top
    draw_w, draw_h = size * ink_w / w, size * ink_h / h
    a, b, w, h = a + left, b + top, ink_w, ink_h
    tw, th = _dimensions
    gpu.state.blend_set("ALPHA")
    _shader.bind()
    _shader.uniform_sampler("image", _texture)
    _shader.uniform_float(
        "mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    )
    _shader.uniform_float("rect", (x - draw_w / 2, y - draw_h / 2, draw_w, draw_h))
    _shader.uniform_float("tile", (a / tw, 1 - (b + h) / th, w / tw, h / th))
    _shader.uniform_float("tint", color)
    _shader.uniform_float("colored", 0.0)
    _shader.uniform_float("sample_step", (0.0, 0.0))
    _batch.draw(_shader)
    return True


def clear():
    global _texture, _shader, _batch
    _texture = _shader = _batch = None
    _entries.clear()
    _ink_bounds.clear()
    for pack in _artwork.values():
        pack['textures'].clear()
