"""Group-composite late sidebar pixels only during Blender's native slide.

No clock, redraw source, scene render or readback. Fully open panels keep their
direct draw. Retained three-slot targets protect asynchronous GPU submissions.
"""

_owners = {}
_shader = _batch = None


def placement(alpha, width, height, alignment):
    """Match wm_draw_region_blend at each of the three audited native builds."""
    alpha = min(1.0, max(0.0, alpha))
    ease = alpha * (2.0 - alpha)
    # Native rect_geo uses integer rcti truncation, not a scaled UI layout.
    dx = (
        int((width - 1) * (1.0 - ease))
        if alignment == "RIGHT"
        else (-int((width - 1) * (1.0 - ease)) if alignment == "LEFT" else 0)
    )
    dy = (
        int((height - 1) * (1.0 - ease))
        if alignment == "TOP"
        else (-int((height - 1) * (1.0 - ease)) if alignment == "BOTTOM" else 0)
    )
    return ease, dx, dy


def draw(key, region, alpha, paint):
    """Fade the completed UI as one premultiplied group, not each primitive."""
    global _shader, _batch
    import gpu
    from gpu_extras.batch import batch_for_shader

    width, height = region.width, region.height
    ease, dx, dy = placement(alpha, width, height, region.alignment)
    if ease <= 0.0:
        return
    if ease >= 1.0:
        paint()
        return
    viewport = gpu.state.viewport_get()
    scissor = gpu.state.scissor_get()
    blend = gpu.state.blend_get()
    depth = gpu.state.depth_test_get()
    mask = gpu.state.depth_mask_get()
    if _shader is None:
        _shader = gpu.shader.from_builtin("IMAGE_COLOR")
        _batch = batch_for_shader(
            _shader,
            "TRIS",
            {
                "pos": ((0, 0), (1, 0), (0, 1), (1, 1)),
                "texCoord": ((0, 0), (1, 0), (0, 1), (1, 1)),
            },
            indices=((0, 1, 2), (2, 1, 3)),
        )
    owner = _owners.get(key)
    if owner is None:
        if len(_owners) >= 8:
            _owners.pop(next(iter(_owners)))
        owner = _owners[key] = dict(ring=[None] * 3, slot=-1, allocations=0, draws=0)
    slot = (owner["slot"] + 1) % 3
    target = owner["ring"][slot]
    if target is None or target[:2] != (width, height):
        texture = gpu.types.GPUTexture((width, height), format="RGBA8")
        target = (width, height, texture, gpu.types.GPUFrameBuffer(color_slots=texture))
        owner["ring"][slot] = target
        owner["allocations"] += 1
    try:
        with target[3].bind():
            gpu.state.viewport_set(0, 0, width, height)
            gpu.state.scissor_set(0, 0, width, height)
            target[3].clear(color=(0, 0, 0, 0))
            paint()
        # Leave the private framebuffer before returning to the native window.
        gpu.state.viewport_set(*viewport)
        gpu.state.scissor_set(*scissor)
        gpu.state.depth_test_set("NONE")
        gpu.state.depth_mask_set(False)
        gpu.state.blend_set("ALPHA_PREMULT")
        with gpu.matrix.push_pop():
            gpu.matrix.translate((dx, dy, 0))
            gpu.matrix.scale((width, height, 1))
            _shader.bind()
            _shader.uniform_sampler("image", target[2])
            _shader.uniform_float("color", (ease, ease, ease, ease))
            _batch.draw(_shader)
        owner["slot"] = slot
        owner["draws"] += 1
    finally:
        gpu.state.viewport_set(*viewport)
        gpu.state.scissor_set(*scissor)
        gpu.state.blend_set(blend)
        gpu.state.depth_test_set(depth)
        gpu.state.depth_mask_set(mask)


def clear():
    global _shader, _batch
    _owners.clear()
    _shader = _batch = None
