"""Ordered, instanced lens and rim draws for Windows Vulkan panel surfaces."""

from . import glass, skin

CAPACITY = 64


class CardSurfaces:
    """Window/canvas-owned GPU objects. Keep each lens immediately before its rim."""

    def __init__(self):
        import gpu
        import numpy as np
        from gpu_extras.batch import batch_for_shader

        info = gpu.types.GPUShaderCreateInfo()
        vary = gpu.types.GPUStageInterfaceInfo("bui_ordered_cards")
        for type_name, name in (("VEC2", "uv"), ("VEC2", "pixel"), ("FLOAT", "blurMix")):
            vary.smooth(type_name, name)
        vary.flat("INT", "drawID")
        info.vertex_in(0, "VEC2", "corner")
        info.vertex_out(vary)
        info.fragment_out(0, "VEC4", "fragColor")
        info.push_constant("MAT4", "mvp")
        info.push_constant("VEC4", "crop")
        info.sampler(0, "FLOAT_2D", "source")
        info.sampler(1, "FLOAT_2D", "softSource")
        info.typedef_source("struct BuiCard { vec4 bounds; vec4 fill; vec4 edge; vec4 shape; };"
                            f"struct BuiCards {{ BuiCard cards[{CAPACITY}]; }};")
        info.uniform_buf(0, "BuiCards", "packet")
        lens = glass.lens_sources()
        rim = skin.skin_sources()
        shared = """
#define card packet.cards[drawID / 2]
#define rect card.bounds
#define tint card.fill
#define motion vec4(card.shape.x, 1., 0., 0.)
#define params card.shape
#define lower card.edge
#define upper card.edge
"""
        for stage, (lens_source, rim_source) in enumerate(zip(lens, rim)):
            code = (shared + "\n#define pos vec3(corner, 0.175)\n" +
                    lens_source.replace("void main()", "void drawLens()") +
                    "\n#undef pos\n#define pos corner\n" +
                    rim_source.replace("void main()", "void drawEdge()") +
                    "\n#undef pos\nvoid main(){\n")
            if stage == 0:
                code += "drawID=gl_InstanceID; pixel=vec2(0.); blurMix=0.;\n"
            code += "if ((drawID & 1)==0) drawLens(); else drawEdge(); }"
            (info.fragment_source if stage else info.vertex_source)(code)
        self.shader = gpu.shader.create_from_info(info)
        self.batch = batch_for_shader(self.shader, "TRIS",
                                      {"corner": ((0, 0), (1, 0), (0, 1), (1, 1))},
                                      indices=((0, 1, 2), (2, 1, 3)))
        self.storage = np.zeros((CAPACITY, 4, 4), dtype=np.float32)
        self.buffers = {}
        self.frame = 0

    def draw(self, rows, owner):
        import gpu
        count = len(rows)
        ring = self.frame % 3
        self.frame += 1
        # Provision every buffer before the first draw. A partial pass must
        # never be blended over by the compatibility painter.
        for start in range(0, count, CAPACITY):
            if (ring, start) not in self.buffers:
                self.buffers[ring, start] = gpu.types.GPUUniformBuf(self.storage)
        textures = owner["ring"][owner["slot"]]
        gpu.state.blend_set("ALPHA")
        shader = self.shader
        shader.bind()
        shader.uniform_float("mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix())
        shader.uniform_float("crop", owner["sample_rect"])
        shader.uniform_sampler("source", textures.base[0])
        shader.uniform_sampler("softSource", textures.strong[0])
        for start in range(0, count, CAPACITY):
            chunk = rows[start:start + CAPACITY]
            self.storage[:len(chunk)] = chunk
            buf = self.buffers[ring, start]
            buf.update(self.storage)
            shader.uniform_block("packet", buf)
            self.batch.draw_instanced(shader, instance_count=2 * len(chunk))


def draw_card_surfaces(canvas, key, palette, clip, x, top, sx, sy, scale, shift):
    owner = glass._owners.get(key)
    if not owner or owner["slot"] < 0 or "sample_rect" not in owner or glass._lens_error:
        return False
    if not glass._strong_blur(owner):
        return False
    painter = getattr(canvas, "_vulkan_card_surfaces", None)
    if painter is False:
        return False
    rows = []
    edge = palette["edge"]
    clip_top, clip_bottom = clip[1], clip[1] + clip[3]

    def append(rect, tint, radius):
        a, b, c, d = rect
        box = (x + (a + shift) * sx, top - (b + d) * sy, c * sx, d * sy)
        rows.append((box, tint, edge, (radius * scale, 0.65 * scale, 5.0, 0.0)))

    for rect in getattr(canvas, "_style_cards", ()):
        if rect[1] + rect[3] > clip_top and rect[1] < clip_bottom:
            append(rect, palette["card"], canvas.theme.radius)
    for rect, options in getattr(canvas, "_style_surfaces", ()):
        if rect[1] + rect[3] > clip_top and rect[1] < clip_bottom:
            color = options.get("surface_color", palette[options["surface"]])
            opacity = options.get("_style_defaults", {}).get("opacity", 1)
            append(rect, (*color[:3], color[3] * opacity), options.get("surface_radius", canvas.theme.radius))
    if len(rows) < 4:
        return False
    if painter is None:
        try:
            painter = CardSurfaces()
        except (ValueError, RuntimeError, MemoryError) as exc:
            canvas._vulkan_card_surfaces = False
            canvas._vulkan_card_error = str(exc)
            return False
        canvas._vulkan_card_surfaces = painter
    painter.draw(rows, owner)
    return True
