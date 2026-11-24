"""Ordered, instanced lens and rim draws for Windows panel surfaces."""

from . import glass, skin, style, icons

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
        vary.flat("INT", "paintLayer")
        info.vertex_in(0, "VEC2", "corner")
        info.vertex_out(vary)
        info.fragment_out(0, "VEC4", "fragColor")
        info.push_constant("MAT4", "mvp")
        info.push_constant("VEC4", "crop")
        info.push_constant("INT", "stageMode")
        info.push_constant("VEC2", "origin")
        info.sampler(0, "FLOAT_2D", "source")
        info.sampler(1, "FLOAT_2D", "softSource")
        info.sampler(2, "FLOAT_2D", "artTexture")
        info.sampler(3, "FLOAT_2D", "iconAtlas")
        info.typedef_source("struct BuiCard { vec4 bounds; vec4 fill; vec4 edge; vec4 shape; vec4 glyph; vec4 tile; vec4 ink; vec4 glyphFrac; };"
                            f"struct BuiCards {{ BuiCard cards[{CAPACITY}]; }};")
        info.uniform_buf(0, "BuiCards", "packet")
        lens = glass.lens_sources()
        rim = skin.skin_sources()
        art = style.preview_sources()
        shared = """
#define card packet.cards[drawID / 2]
vec4 cardRect() {
    vec4 bounds = card.bounds;
    if (origin.y != 0.) bounds.y = (origin.x - bounds.y) - card.shape.w;
    return bounds;
}
#define rect cardRect()
#define tint card.fill
#define motion vec4(card.shape.x, 1., 0., 0.)
#define params vec4(card.shape.xy, 5., 0.)
#define lower card.edge
#define upper card.edge
"""
        for stage, (lens_source, rim_source) in enumerate(zip(lens, rim)):
            code = (shared + "\n#define pos vec3(corner, 0.175)\n" +
                    lens_source.replace("void main()", "void drawLens()") +
                    "\n#undef pos\n#define pos corner\n" +
                    rim_source.replace("void main()", "void drawEdge()") +
                    "\n#undef pos\n#define pos corner\n#define image artTexture\n"
                    "#define display_space true\n#define radius card.shape.x\n" +
                    art[stage].replace("void main()", "void drawArt()") +
                    "\n#undef pos\n#undef image\n#undef radius\nvoid main(){\n")
            if stage == 0:
                code += "drawID=stageMode==3 ? 2*(gl_InstanceID/4) : gl_InstanceID; paintLayer=stageMode==3 ? gl_InstanceID%4 : 2*(drawID&1); pixel=vec2(0.); blurMix=0.;\n"
                code += "if(paintLayer==3){vec4 g=card.glyph;g.y=(origin.x-g.y)-card.glyphFrac.x; uv=card.tile.xy+corner*card.tile.zw; gl_Position=mvp*vec4(g.xy+corner*g.zw,0.,1.);return;}\n"
            else:
                code += "if(paintLayer==3){fragColor=vec4(card.ink.rgb,card.ink.a*texture(iconAtlas,uv).a);return;}\n"
            if stage:
                code += "if(paintLayer==1 && card.shape.z==0.) discard;\n"
            code += "if(paintLayer==0) drawLens(); else if(paintLayer==1) drawArt(); else drawEdge(); }"
            (info.fragment_source if stage else info.vertex_source)(code)
        self.shader = gpu.shader.create_from_info(info)
        self.batch = batch_for_shader(self.shader, "TRIS",
                                      {"corner": ((0, 0), (1, 0), (0, 1), (1, 1))},
                                      indices=((0, 1, 2), (2, 1, 3)))
        self.storage = np.zeros((CAPACITY, 8, 4), dtype=np.float32)
        self.frame = 0
        self.layout_key = self.palette = None
        self.layout_buffers = ()
        self.layout_builds = 0
        self.buttons = {}
        self.button_builds = self.button_draws = 0

    def draw_buttons(self, buttons, plans, owner, canvas, x, top, sx, sy, scale, shift):
        from math import floor
        import gpu
        if len(buttons) > CAPACITY or self.layout_key is None or self.layout_key[:7] != (canvas.layout_count, x, sx, sy, scale, shift, canvas.theme.radius):
            return False
        artwork = None
        signature = []
        for (button, _, colors, css), plan in zip(buttons, plans):
            token = css.get("button_artwork")
            if token:
                if artwork and token != artwork:
                    return False
                artwork = token
            role = "text" if "color" in css else css.get("color_role", "text")
            ink = colors.get("accent_text", colors[role]) if role == "accent" else colors[role]
            signature.append((button.key, button.rect, plan[0], tuple(ink), tuple(colors["field"]), tuple(colors["edge"]), css.get("radius", canvas.theme.radius), token))
        texture = icons.full_artwork_texture(artwork) if artwork else None
        if artwork and texture is None:
            return False
        signature = tuple(signature)
        buf = self.buttons.get(signature)
        if buf is None:
            for index, ((button, _, _, _), (_, _, (glyph, tile), ink, fill, edge, radius, token)) in enumerate(zip(buttons, signature)):
                a, b, c, d = button.rect
                bottom = (b + d) * sy
                whole = floor(bottom)
                box = (x + (a + shift) * sx, whole, c * sx, d * sy)
                glyph_bottom = bottom - glyph[1]
                glyph_whole = floor(glyph_bottom)
                self.storage[index] = (box, fill, edge, (radius * scale, .65 * scale, float(bool(token)), bottom - whole),
                                       (glyph[0], glyph_whole, glyph[2], glyph[3]), tile, ink,
                                       (glyph_bottom - glyph_whole, 0., 0., 0.))
            buf = gpu.types.GPUUniformBuf(self.storage)
            if len(self.buttons) >= 128:
                self.buttons.pop(next(iter(self.buttons)))
            self.buttons[signature] = buf
            self.button_builds += 1
        textures = owner["ring"][owner["slot"]]
        gpu.state.blend_set("ALPHA")
        shader = self.shader
        shader.bind()
        shader.uniform_float("mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix())
        shader.uniform_float("origin", (top, 1.))
        shader.uniform_float("crop", owner["sample_rect"])
        shader.uniform_sampler("source", textures.base[0])
        shader.uniform_sampler("softSource", textures.strong[0])
        shader.uniform_sampler("artTexture", texture if texture is not None else textures.base[0])
        shader.uniform_sampler("iconAtlas", icons._texture)
        shader.uniform_int("stageMode", 3)
        shader.uniform_block("packet", buf)
        self.batch.draw_instanced(shader, instance_count=4 * len(buttons))
        self.button_draws += 1
        return True

    def draw_layout(self, canvas, owner, palette, x, top, sx, sy, scale, shift):
        """Retain page geometry across native scroll translations."""
        from math import floor
        import gpu
        # Group options and host colours can be edited without replacing a
        # palette object. Keep those author-controlled inputs in the paint key.
        surfaces = getattr(canvas, "_style_surfaces", ())
        colors = tuple((opts.get("surface_color", palette[opts["surface"]]),
                        opts.get("_style_defaults", {}).get("opacity", 1),
                        opts.get("surface_radius", canvas.theme.radius)) for _, opts in surfaces)
        key = (canvas.layout_count, x, sx, sy, scale, shift, canvas.theme.radius,
               tuple(palette["edge"]), tuple(palette["card"]), colors)
        if self.layout_key != key or self.palette is not palette:
            rows = []
            edge = palette["edge"]

            def append(rect, tint, radius):
                a, b, c, d = rect
                # The host scroll origin is integral. Keeping the fractional
                # edge separately avoids cancellation when the page moves.
                bottom = (b + d) * sy
                whole = floor(bottom)
                box = (x + (a + shift) * sx, whole, c * sx, d * sy)
                rows.append((box, tint, edge, (radius * scale, .65 * scale, 5., bottom - whole)))

            for rect in getattr(canvas, "_style_cards", ()):
                append(rect, palette["card"], canvas.theme.radius)
            for rect, opts in getattr(canvas, "_style_surfaces", ()):
                color = opts.get("surface_color", palette[opts["surface"]])
                opacity = opts.get("_style_defaults", {}).get("opacity", 1)
                append(rect, (*color[:3], color[3] * opacity), opts.get("surface_radius", canvas.theme.radius))
            packets = []
            for start in range(0, len(rows), CAPACITY):
                group = rows[start:start + CAPACITY]
                self.storage[:len(group), :4] = group
                packets.append((gpu.types.GPUUniformBuf(self.storage), 2 * len(group)))
            self.layout_buffers = packets
            self.layout_key, self.palette = key, palette
            self.buttons.clear()
            self.layout_builds += 1
        gpu.state.blend_set("ALPHA")
        shader = self.shader
        textures = owner["ring"][owner["slot"]]
        shader.bind()
        shader.uniform_float("mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix())
        shader.uniform_float("origin", (top, 1.))
        shader.uniform_float("crop", owner["sample_rect"])
        shader.uniform_sampler("source", textures.base[0])
        shader.uniform_sampler("softSource", textures.strong[0])
        shader.uniform_sampler("artTexture", textures.base[0])
        shader.uniform_sampler("iconAtlas", textures.base[0])
        shader.uniform_int("stageMode", 0)
        for buf, count in self.layout_buffers:
            shader.uniform_block("packet", buf)
            self.batch.draw_instanced(shader, instance_count=count)
        self.frame += 1


def draw_card_surfaces(canvas, key, palette, x, top, sx, sy, scale, shift):
    owner = glass._owners.get(key)
    if not owner or owner["slot"] < 0 or "sample_rect" not in owner or glass._lens_error:
        return False
    painter = getattr(canvas, "_panel_card_surfaces", None)
    if painter is False:
        return False
    count = len(getattr(canvas, "_style_cards", ())) + len(getattr(canvas, "_style_surfaces", ()))
    if not 4 <= count <= 256 or not float(top).is_integer() or not glass._strong_blur(owner):
        return False
    if painter is None:
        try:
            painter = CardSurfaces()
        except (ValueError, RuntimeError, MemoryError) as exc:
            canvas._panel_card_surfaces = False
            canvas._panel_card_error = str(exc)
            return False
        canvas._panel_card_surfaces = painter
    painter.draw_layout(canvas, owner, palette, x, top, sx, sy, scale, shift)
    return True
