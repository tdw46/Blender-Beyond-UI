"""Bounded GPU-only UI backdrops, separate from scene rendering and thumbnails.

The audited canvas bridge copies a completed native UI framebuffer. Public GPU
APIs own the textures, downsample, shared Gaussian levels and presentation.
No pixel readback, scene capture, redraw timer or native framebuffer retention.
"""

import sys
import ctypes
import math

_shader = _batch = None
_lens_shader = _lens_batch = None
_lens_batches = {}
_lens_error = ""
_owners = {}
_views = {}
error = ""

# Exact rounded SDF owns coverage; smooth normals own rim light, and a
# monotone rational field owns refraction without nearest-edge reversals.
_SMOOTH_NORMAL_GLSL = """
vec2 glassNormal(vec2 p, vec2 q, float smoothing) {
    vec2 root=sqrt(q*q+vec2(smoothing*smoothing));
    vec2 corner=vec2(smoothing*smoothing)/(2.0*(root-q));
    vec2 direction=p/sqrt(p*p+vec2(smoothing*smoothing));
    return corner/max(length(corner),0.0001)*direction;
}
vec2 glassOffset(vec2 p, vec2 size, float strength, float distanceToEdge, float radius, float sweep) {
    // Monotone rational lens: straight center axes, outward bowed off-axis
    // contours all the way to the edge. No rotating bevel-normal reversal.
    // Round-boundary shoulder adds the edge-merging shape back without rotating
    // the displacement vector back inward. Bound the body shoulder derivative
    // even on long narrow fields; curved caps use the local mapping below.
    vec2 unit=p/(size*0.5);
    float bezel=max(1.0,min(size.x,size.y)*0.32);
    float shoulder=1.0-smoothstep(0.0,bezel,max(0.0,-distanceToEdge));
    float rimGain=0.30*bezel/length(size*0.5);
    float gain=1.0+strength*dot(unit,unit)+rimGain*shoulder*(1.0+0.70*sweep);
    // In the rounded corner only, unwrap the curved distance contour toward
    // its flat-edge source coordinate. This carries near-edge lines around a
    // pill's cap, instead of merely magnifying them along a radial vector.
    // The smooth corner gate is zero on center axes and straight-edge joins.
    vec2 corner=max(abs(p)-size*0.5+radius,vec2(0.0));
    float arc=smoothstep(0.0,max(1.0,radius*0.35),min(corner.x,corner.y));
    vec2 wrap=sign(p)*max(vec2(0.0),size*0.5+distanceToEdge-abs(p));
    return (p+wrap*((0.90+0.20*sweep)*arc*shoulder))/gain-p;
}
float glassWipeRadius(vec2 size) {
    // Central diagonal strip covering 40% of the rectangle, with the existing
    // 40px footprint as a minimum for small controls. Solve the rectangle's
    // projected-area distribution analytically; no texture or search loop.
    vec2 projected=size*vec2(0.894427,0.447214);
    float a=max(projected.x,projected.y),b=min(projected.x,projected.y);
    float width=0.4*a;
    if (width>a-b) width=a+b-2.0*sqrt(0.6*a*b);
    return max(20.0,width*0.5);
}
"""


def viewport_changed(context, records):
    """One revision per actual viewport draw; never request a viewport redraw."""
    if context.area.type != "VIEW_3D" or context.region.type != "WINDOW":
        return
    key = (context.window.as_pointer(), context.area.as_pointer())
    for region in context.area.regions:
        record = records.get((*key, region.as_pointer()))
        if region.type == "UI" and record and record.get("valid"):
            _views[key] = _views.get(key, 0) + 1
            if len(_views) > 8:
                _views.pop(next(iter(_views)))
            # A late window presenter consumes this revision in the same frame.
            # Fallback regions still need their next native UI paint.
            if not record.get("late"):
                region.tag_redraw()
            break


def viewport_source(context):
    """Pixel-aligned backdrop only when a real viewport overlaps this sidebar."""
    if context.area.type != "VIEW_3D" or context.region.type != "UI":
        return None
    if not getattr(context.preferences.system, "use_region_overlap", False):
        return None
    region = next((r for r in context.area.regions if r.type == "WINDOW"), None)
    if region is None:
        return None
    ui = context.region
    if region.x + region.width <= ui.x or region.y + region.height <= ui.y:
        return None
    return (
        region.as_pointer(),
        region.x - ui.x,
        region.y - ui.y,
        _views.get((context.window.as_pointer(), context.area.as_pointer()), 0),
        region.width,
        region.height,
    )


def _ensure():
    global _shader, _batch
    if _shader is not None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    interface = gpu.types.GPUStageInterfaceInfo("bvt_glass_uv")
    interface.smooth("VEC2", "uv")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.push_constant("MAT4", "mvp")
    info.push_constant("VEC4", "rect")
    info.push_constant("VEC4", "sourceRect")
    info.push_constant("VEC4", "stepMode")
    info.push_constant("VEC4", "shape")
    info.sampler(0, "FLOAT_2D", "source")
    info.vertex_source("""
void main() { uv=pos; gl_Position=mvp*vec4(rect.xy+pos*rect.zw,0.0,1.0); }
""")
    info.fragment_source(
        _SMOOTH_NORMAL_GLSL
        + """
void main() {
    vec2 coord=sourceRect.xy+uv*sourceRect.zw;
    vec4 color;
    if (stepMode.z < 0.5) {
        // Bilinear paired Gaussian taps, sigma about 3 output pixels.
        color=texture(source,coord)*0.2270270270;
        color+=(texture(source,coord+stepMode.xy*1.3846153846)
              + texture(source,coord-stepMode.xy*1.3846153846))*0.3162162162;
        color+=(texture(source,coord+stepMode.xy*3.2307692308)
              + texture(source,coord-stepMode.xy*3.2307692308))*0.0702702703;
    } else if (stepMode.z > 1.5) {
        color=(texture(source,coord+stepMode.xy)
             + texture(source,coord-stepMode.xy)
             + texture(source,coord+vec2(stepMode.x,-stepMode.y))
             + texture(source,coord+vec2(-stepMode.x,stepMode.y)))*0.25;
    } else {
        vec2 q=abs((uv-0.5)*rect.zw)-rect.zw*0.5+shape.x;
        float d=length(max(q,vec2(0.0)))+min(max(q.x,q.y),0.0)-shape.x;
        vec2 shift=glassOffset((uv-0.5)*rect.zw,rect.zw,0.16,d,shape.x,0.0)/rect.zw*sourceRect.zw;
        color=texture(source,clamp(coord+shift,sourceRect.xy,sourceRect.xy+sourceRect.zw));
        float aa=max(fwidth(d),0.7);
        color.a=(1.0-smoothstep(-aa,aa,d));
    }
    fragColor=color;
}
"""
    )
    _shader = gpu.shader.create_from_info(info)
    _batch = batch_for_shader(
        _shader,
        "TRIS",
        {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
        indices=((0, 1, 2), (2, 1, 3)),
    )


def _draw(texture, rect, source_rect, step, shape, matrix):
    _shader.bind()
    _shader.uniform_sampler("source", texture)
    for name, value in (
        ("mvp", matrix),
        ("rect", rect),
        ("sourceRect", source_rect),
        ("stepMode", step),
        ("shape", shape),
    ):
        _shader.uniform_float(name, value)
    _batch.draw(_shader)


def _target(width, height):
    import gpu

    texture = gpu.types.GPUTexture((width, height), format="RGBA8")
    # 4.2 creates filtered float textures but has no Python filter_mode setter.
    if callable(getattr(texture, "filter_mode", None)):
        texture.filter_mode(True)
    return texture, gpu.types.GPUFrameBuffer(color_slots=texture)


def source_key(key, shared_key, rect, viewport_size):
    """Only visible pixels of a spring envelope need backdrop coverage."""
    shared = _owners.get(shared_key)
    crop = shared.get("sample_rect") if shared else None
    if crop:
        a, b, w, h = crop
        x, y, rw, rh = rect
        vw, vh = viewport_size
        left, bottom = max(0.0, x), max(0.0, y)
        right, top = min(vw, x + rw), min(vh, y + rh)
        if (
            left < right
            and bottom < top
            and a <= left
            and b <= bottom
            and right <= a + w
            and top <= b + h
        ):
            return shared_key
    return key


def draw(
    key,
    revision,
    rect,
    radius,
    bridge,
    *,
    scale=1.0,
    viewport_source=None,
    framebuffer_size=None,
    shared_key=None,
    display_rect=None,
    blur=0.3,
    capture_rect=None,
    viewport_present=None,
):
    """Sample a retained blurred crop; only changed underlays run its producer."""
    global error
    # Overlays borrow the same underlying glass levels, never recursively blur
    # an already-glassy control. Only borrow when the retained crop covers it.
    import gpu
    from mathutils import Matrix

    viewport = gpu.state.viewport_get()
    vx, vy, vw, vh = viewport
    if (
        source_key(key, shared_key, rect, (vw, vh)) == shared_key
        and shared_key is not None
    ):
        if lens(
            shared_key,
            display_rect or rect,
            radius,
            (0.0, 0.0, 0.0, 0.0),
            blur=max(0.4, blur),
        ):
            return True
    if bridge is None or not hasattr(bridge, "bvt_probe_framebuffer"):
        return False
    # The audited native UI targets use a region-local full-size viewport.
    if vw < 1 or vh < 1:
        return False
    fw, fh = framebuffer_size or (vw, vh)
    x, y, w, h = capture_rect or rect
    pad = math.ceil(12 * scale)
    left = max(0, math.floor(x) - pad)
    bottom = max(0, math.floor(y) - pad)
    right = min(vw, math.ceil(x + w) + pad)
    top = min(vh, math.ceil(y + h) + pad)
    if right <= left or top <= bottom:
        return False
    cw, ch = right - left, top - bottom
    bw, bh = max(1, math.ceil(cw / (2 * scale))), max(1, math.ceil(ch / (2 * scale)))
    cropped = (
        viewport_source is None
        and hasattr(bridge, "bvt_probe_crop_framebuffer")
        and callable(getattr(gpu.platform, "backend_type_get", None))
        and (
            gpu.platform.backend_type_get() == "METAL"
            or (sys.platform == "win32" and gpu.platform.backend_type_get() == "VULKAN")
        )
    )
    signature = (
        revision,
        viewport,
        (left, bottom, cw, ch),
        scale,
        (fw, fh),
        viewport_source,
    )
    owner = _owners.get(key)
    if owner is None:
        if len(_owners) >= 8:
            _owners.pop(next(iter(_owners)))
        owner = dict(
            ring=[None] * 3, slot=-1, signature=None, productions=0, allocations=0
        )
        _owners[key] = owner
    if owner.get("failed") == signature:
        return False
    blend = gpu.state.blend_get()
    depth = gpu.state.depth_test_get()
    mask = gpu.state.depth_mask_get()
    scissor = gpu.state.scissor_get()
    try:
        _ensure()
        gpu.state.depth_test_set("NONE")
        gpu.state.depth_mask_set(False)
        if owner["signature"] != signature:
            bridge.bvt_probe_framebuffer.restype = ctypes.c_void_p
            bridge.bvt_probe_copy_framebuffer.argtypes = (ctypes.c_void_p,)
            source = bridge.bvt_probe_framebuffer() if viewport_source is None else None
            if viewport_source is None and not source:
                return False
            slot = (owner["slot"] + 1) % 3
            targets = owner["ring"][slot]
            copy_w, copy_h = (cw, ch) if cropped else (fw, fh)
            dimensions = (copy_w, copy_h, bw, bh, viewport_source is not None)
            if targets is None or targets[0] != dimensions:
                # Allocate transactionally; leave prior published slots intact.
                targets = (
                    dimensions,
                    None if viewport_source else _target(copy_w, copy_h),
                    _target(bw, bh),
                    _target(bw, bh),
                    _target(bw, bh),
                )
                owner["allocations"] += 3 if viewport_source else 4
                owner["ring"][slot] = (
                    targets  # Scratch ownership; published slot is unchanged until success.
                )
            if viewport_source:
                if not hasattr(bridge, "bvt_probe_draw_viewport"):
                    return False
                bridge.bvt_probe_draw_viewport.argtypes = (
                    ctypes.c_void_p,
                    ctypes.c_int,
                    ctypes.c_int,
                )
                with (
                    targets[2][1].bind(),
                    gpu.matrix.push_pop(),
                    gpu.matrix.push_pop_projection(),
                ):
                    gpu.state.viewport_set(0, 0, bw, bh)
                    gpu.state.scissor_set(0, 0, bw, bh)
                    targets[2][1].clear(color=(0, 0, 0, 1))
                    gpu.matrix.load_matrix(Matrix.Identity(4))
                    gpu.matrix.load_projection_matrix(
                        Matrix(
                            (
                                (2 / cw, 0, 0, -1 - 2 * left / cw),
                                (0, 2 / ch, 0, -1 - 2 * bottom / ch),
                                (0, 0, 1, 0),
                                (0, 0, 0, 1),
                            )
                        )
                    )
                    gpu.state.blend_set("NONE")
                    presented = (
                        viewport_present(*viewport_source[:3])
                        if viewport_present
                        else False
                    )
                    if not presented and not bridge.bvt_probe_draw_viewport(
                        *viewport_source[:3]
                    ):
                        return False
            else:
                with targets[1][1].bind():
                    if cropped:
                        bridge.bvt_probe_crop_framebuffer.argtypes = (
                            ctypes.c_void_p,
                            ctypes.c_int,
                            ctypes.c_int,
                            ctypes.c_int,
                            ctypes.c_int,
                        )
                        if not bridge.bvt_probe_crop_framebuffer(
                            source, left + vx, bottom + vy, cw, ch
                        ):
                            return False
                    elif not bridge.bvt_probe_copy_framebuffer(source):
                        return False
            gpu.state.blend_set("NONE")
            crop = ((left + vx) / fw, (bottom + vy) / fh, cw / fw, ch / fh)
            if cropped:
                crop = (0.0, 0.0, 1.0, 1.0)
            passes = (
                []
                if viewport_source
                else [
                    (
                        targets[2],
                        targets[1][0],
                        crop,
                        (cw / bw / copy_w * 0.25, ch / bh / copy_h * 0.25, 2.0, 0.0),
                    )
                ]
            )
            passes.extend(
                (
                    (
                        targets[3],
                        targets[2][0],
                        (0.0, 0.0, 1.0, 1.0),
                        (1 / bw, 0.0, 0.0, 0.0),
                    ),
                    (
                        targets[4],
                        targets[3][0],
                        (0.0, 0.0, 1.0, 1.0),
                        (0.0, 1 / bh, 0.0, 0.0),
                    ),
                )
            )
            for target, texture, uv, step in passes:
                with target[1].bind():
                    gpu.state.viewport_set(0, 0, bw, bh)
                    gpu.state.scissor_set(0, 0, bw, bh)
                    _draw(
                        texture,
                        (-1.0, -1.0, 2.0, 2.0),
                        uv,
                        step,
                        (0.0, 0.0, 0.0, 0.0),
                        Matrix.Identity(4),
                    )
            owner["ring"][slot] = targets
            owner["slot"] = slot
            owner["signature"] = signature
            owner["productions"] += 1
            owner["sample_rect"] = (left, bottom, cw, ch)
        gpu.state.viewport_set(*viewport)
        gpu.state.scissor_set(*scissor)
        gpu.state.blend_set("ALPHA")
        if blur > 0.3 and lens(
            key, display_rect or rect, radius, (0.0, 0.0, 0.0, 0.0), blur=blur
        ):
            return True
        texture = owner["ring"][owner["slot"]][4][0]
        display_rect = display_rect or rect
        x, y, w, h = display_rect
        _draw(
            texture,
            display_rect,
            ((x - left) / cw, (y - bottom) / ch, w / cw, h / ch),
            (0.0, 0.0, 1.0, 0.0),
            (radius, 0.0, 0.0, 0.0),
            gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix(),
        )
        return True
    except Exception as exc:
        error = str(exc)
        owner["failed"] = signature
        return False  # Existing translucent styling remains the capability fallback.
    finally:
        gpu.state.viewport_set(*viewport)
        gpu.state.scissor_set(*scissor)
        gpu.state.blend_set(blend)
        gpu.state.depth_test_set(depth)
        gpu.state.depth_mask_set(mask)


def prepare_texture(key, revision, texture, rect, *, scale=1.0):
    """Prepare the source blur levels from a host-owned, completed GPU texture.

    No framebuffer readback or extra capture. Hosts call once per underlay
    revision, then every control/menu borrows the same key through lens().
    The caller owns texture lifetime and supplies region-pixel coordinates.
    """
    global error
    import gpu
    from mathutils import Matrix
    from .paint import gpu_state

    if scale <= 0 or rect[2] <= 0 or rect[3] <= 0:
        return False
    signature = (
        "texture",
        revision,
        id(texture),
        tuple(rect),
        scale,
        texture.width,
        texture.height,
    )
    owner = _owners.get(key)
    if owner is None:
        if len(_owners) >= 8:
            _owners.pop(next(iter(_owners)))
        owner = dict(
            ring=[None] * 3, slot=-1, signature=None, productions=0, allocations=0
        )
        _owners[key] = owner
    if owner.get("signature") == signature:
        return True
    if owner.get("failed") == signature:
        return False
    try:
        with gpu_state():
            _ensure()
            bw, bh = (
                max(1, math.ceil(rect[2] / (2 * scale))),
                max(1, math.ceil(rect[3] / (2 * scale))),
            )
            slot = (owner["slot"] + 1) % 3
            targets = owner["ring"][slot]
            dimensions = ("texture", bw, bh)
            if targets is None or targets[0] != dimensions:
                targets = (
                    dimensions,
                    None,
                    _target(bw, bh),
                    _target(bw, bh),
                    _target(bw, bh),
                )
                owner["allocations"] += 3
                owner["ring"][slot] = targets
            passes = (
                (targets[2], texture, (0.25 / bw, 0.25 / bh, 2.0, 0.0)),
                (targets[3], targets[2][0], (1 / bw, 0.0, 0.0, 0.0)),
                (targets[4], targets[3][0], (0.0, 1 / bh, 0.0, 0.0)),
            )
            gpu.state.blend_set("NONE")
            for output, source, step in passes:
                with output[1].bind():
                    gpu.state.viewport_set(0, 0, bw, bh)
                    gpu.state.scissor_set(0, 0, bw, bh)
                    _draw(
                        source,
                        (-1.0, -1.0, 2.0, 2.0),
                        (0.0, 0.0, 1.0, 1.0),
                        step,
                        (0.0, 0.0, 0.0, 0.0),
                        Matrix.Identity(4),
                    )
            owner.update(slot=slot, signature=signature, sample_rect=tuple(rect))
            owner["productions"] += 1
            return True
    except Exception as exc:
        error = str(exc)
        owner["failed"] = signature
        return False


def release(key):
    """Release one host-owned backdrop and all its retained blur levels."""
    _owners.pop(key, None)


def clear():
    global _shader, _batch, _lens_shader, _lens_batch, _lens_error, error
    _owners.clear()
    _views.clear()
    _shader = _batch = None
    error = ""
    _lens_shader = _lens_batch = None
    _lens_batches.clear()
    _lens_error = ""


def _strong_blur(owner):
    """One lazy shared stronger Gaussian level per completed base revision."""
    signature = (owner.get("signature"), owner["slot"])
    if owner.get("strong_signature") == signature:
        return True
    if owner.get("strong_failed") == signature:
        return False
    import gpu
    from mathutils import Matrix

    viewport = gpu.state.viewport_get()
    scissor = gpu.state.scissor_get()
    blend = gpu.state.blend_get()
    depth = gpu.state.depth_test_get()
    mask = gpu.state.depth_mask_get()
    try:
        _ensure()
        slot = owner["slot"]
        targets = owner["ring"][slot]
        source = targets[4][0]
        w, h = source.width, source.height
        if len(targets) < 7:
            targets = (*targets, _target(w, h), _target(w, h))
            owner["ring"][slot] = targets
            owner["allocations"] += 2
        # Baseline sigma is the existing tab blur. Variances add; this extra
        # radius raises the shared level from 30 to 70 without changing 30.
        step = math.sqrt((0.7 / 0.3) ** 2 - 1.0)
        gpu.state.depth_test_set("NONE")
        gpu.state.depth_mask_set(False)
        gpu.state.blend_set("NONE")
        for target, texture, offset in (
            (targets[5], source, (step / w, 0.0, 0.0, 0.0)),
            (targets[6], targets[5][0], (0.0, step / h, 0.0, 0.0)),
        ):
            with target[1].bind():
                gpu.state.viewport_set(0, 0, w, h)
                gpu.state.scissor_set(0, 0, w, h)
                _draw(
                    texture,
                    (-1.0, -1.0, 2.0, 2.0),
                    (0.0, 0.0, 1.0, 1.0),
                    offset,
                    (0.0, 0.0, 0.0, 0.0),
                    Matrix.Identity(4),
                )
        owner["strong_signature"] = signature
        owner["strong_productions"] = owner.get("strong_productions", 0) + 1
        return True
    except Exception as exc:
        owner["strong_failed"] = signature
        owner["strong_error"] = str(exc)
        return False
    finally:
        gpu.state.viewport_set(*viewport)
        gpu.state.scissor_set(*scissor)
        gpu.state.blend_set(blend)
        gpu.state.depth_test_set(depth)
        gpu.state.depth_mask_set(mask)


def _ensure_lens():
    """One draw, at most two shared samples; no per-control targets."""
    global _lens_shader, _lens_batch
    if _lens_shader is not None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    interface = gpu.types.GPUStageInterfaceInfo("bvt_glass_lens_uv")
    interface.smooth("VEC2", "uv")
    interface.smooth("VEC2", "pixel")
    interface.smooth("FLOAT", "blurMix")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC3", "pos")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    # 128 bytes, matching the supported Metal push-constant budget.
    for kind, name in (
        ("MAT4", "mvp"),
        ("VEC4", "rect"),
        ("VEC4", "crop"),
        ("VEC4", "tint"),
        ("VEC4", "motion"),
    ):
        info.push_constant(kind, name)
    info.sampler(0, "FLOAT_2D", "source")
    info.sampler(1, "FLOAT_2D", "softSource")
    info.vertex_source("""
void main(){
    uv=pos.xy;blurMix=pos.z;
    vec2 axis=vec2(cos(motion.z),sin(motion.z));
    vec2 p=(pos.xy-0.5)*rect.zw;
    float stretch=max(0.5,1.0+motion.w);
    // Area preserving directional deformation, with stable logical hit bounds.
    p=p/stretch+axis*dot(p,axis)*(stretch-1.0/stretch);
    pixel=rect.xy+rect.zw*0.5+p;
    gl_Position=mvp*vec4(pixel,0.0,1.0);
}""")
    info.fragment_source(
        _SMOOTH_NORMAL_GLSL
        + """
void main(){
    float radius=min(motion.x,min(rect.z,rect.w)*0.5);
    vec2 q=abs((uv-0.5)*rect.zw)-rect.zw*0.5+radius;
    vec2 corner=max(q,vec2(0.0));
    float d=length(corner)+min(max(q.x,q.y),0.0)-radius;
    vec2 n=glassNormal((uv-0.5)*rect.zw,q,max(1.0,min(rect.z,rect.w)*0.10));
    float pulse=sin(clamp(motion.y,0.0,1.0)*3.14159265);
    vec2 sweepAxis=vec2(0.894427,0.447214);
    float along=dot(pixel-(rect.xy+rect.zw*0.5),sweepAxis);
    float bandRadius=glassWipeRadius(rect.zw);
    float extent=dot(rect.zw*0.5,sweepAxis)+bandRadius;
    float band=1.0-smoothstep(0.0,bandRadius,abs(along-mix(-extent,extent,clamp(motion.y,0.0,1.0))));
    float sweep=band*pulse;
    float strength=0.16+0.04*pulse+(motion.y!=1.0 ? 0.04 : 0.0);
    vec2 offset=glassOffset((uv-0.5)*rect.zw,rect.zw,strength,d,radius,sweep);
    vec2 coord=(pixel+offset-crop.xy)/crop.zw;
    vec2 texel=0.5/vec2(textureSize(source,0));
    coord=clamp(coord,texel,vec2(1.0)-texel);
    vec3 backdrop;
    if(blurMix>=1.0) backdrop=texture(softSource,coord).rgb;
    else {
        backdrop=texture(source,coord).rgb;
        if(blurMix>0.0) backdrop=mix(backdrop,texture(softSource,coord).rgb,blurMix);
    }
    vec3 color=mix(backdrop,tint.rgb,clamp(tint.a,0.0,0.78));
    float rim=1.0-smoothstep(0.0,1.6,max(0.0,-d));
    float light=max(0.0,dot(n,vec2(-0.447214,0.894427)));
    color=mix(color,vec3(1.0),rim*(0.12+0.35*light*light));
    // Rim-led flare, evaluated locally in this draw (no bloom target/pass).
    float halo=1.0-smoothstep(0.0,5.0,max(0.0,-d));
    color+=vec3(sweep*(0.03+0.575*rim+0.09*halo*halo));
    float aa=max(fwidth(d),0.7);
    fragColor=vec4(color,1.0-smoothstep(-aa,aa,d));
}"""
    )
    _lens_shader = gpu.shader.create_from_info(info)
    # Three tiny immutable quads carry the mix without exceeding the 128-byte
    # push-constant budget or allocating/updating a buffer per widget.
    for level, mix in ((0.3, 0.0), (0.4, 0.175), (0.7, 1.0)):
        _lens_batches[level] = batch_for_shader(
            _lens_shader,
            "TRIS",
            {"pos": ((0, 0, mix), (1, 0, mix), (0, 1, mix), (1, 1, mix))},
            indices=((0, 1, 2), (2, 1, 3)),
        )
    _lens_batch = _lens_batches[0.4]


def lens(key, rect, radius, tint, *, phase=1.0, stretch=0.0, angle=0.0, blur=0.4):
    """Consume shared blur levels; lazily prepare the stronger owner level once."""
    global _lens_error
    if _lens_error:
        return False
    owner = _owners.get(key)
    if not owner or owner["slot"] < 0 or "sample_rect" not in owner:
        return False
    if rect[2] <= 0 or rect[3] <= 0:
        return False
    import gpu

    try:
        _ensure_lens()
    except Exception as exc:
        _lens_error = str(exc)
        return False
    level = 0.7 if blur >= 0.7 else 0.4 if blur > 0.3 else 0.3
    if level > 0.3 and not _strong_blur(owner):
        level = 0.3
    targets = owner["ring"][owner["slot"]]
    source = targets[4][0]
    soft = targets[6][0] if level > 0.3 else source
    gpu.state.blend_set("ALPHA")
    _lens_shader.bind()
    _lens_shader.uniform_sampler("source", source)
    _lens_shader.uniform_sampler("softSource", soft)
    for name, value in (
        (
            "mvp",
            gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix(),
        ),
        ("rect", rect),
        ("crop", owner["sample_rect"]),
        ("tint", tint),
        ("motion", (radius, phase, angle, stretch)),
    ):
        _lens_shader.uniform_float(name, value)
    _lens_batches[level].draw(_lens_shader)
    return True
