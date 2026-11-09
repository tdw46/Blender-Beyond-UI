"""Present an embedded canvas's transient UI above composited Blender regions."""

from contextlib import contextmanager


_active = {}  # interactive popup hosts in window stacking order


def bounds(window):
    # RNA Window dimensions can be logical points on Retina. Screen areas,
    # region origins, input coordinates and the WM framebuffer share pixels.
    areas = window.screen.areas
    l = min(a.x for a in areas)
    b = min(a.y for a in areas)
    return (
        l,
        b,
        max(a.x + a.width for a in areas) - l,
        max(a.y + a.height for a in areas) - b,
    )


def intersects(a, b):
    x, y, w, h = a
    l, d, c, r = b
    return x < l + c and l < x + w and y < d + r and d < y + h


class Sources:
    """Track native region paints only while a transient sheet is visible."""

    def __init__(self, window, changed, skip):
        self.window = window
        self.changed = changed
        self.skip = skip
        self.handlers = []
        self.crops = []
        self.unsupported = []
        try:
            kinds = {}
            for area in window.screen.areas:
                space = type(area.spaces.active)
                for region in area.regions:
                    if (
                        region.width > 1
                        and region.height > 1
                        and not skip(area, region)
                    ):
                        kinds.setdefault((space, region.type), []).append(region)
            for (space, kind), regions in kinds.items():
                try:
                    handle = space.draw_handler_add(self.touch, (), kind, "POST_PIXEL")
                except (ValueError, TypeError, RuntimeError):
                    self.unsupported.extend(regions)
                else:
                    self.handlers.append((space, handle, kind))
        except Exception:
            self.close()
            raise

    def touch(self):
        import bpy

        ctx = bpy.context
        region = ctx.region
        if ctx.window != self.window or region is None or self.skip(ctx.area, region):
            return
        bounds = (region.x, region.y, region.width, region.height)
        if any(intersects(crop, bounds) for crop in self.crops):
            self.changed()

    def sample(self, rect, pad, revision):
        x, y, w, h = rect
        crop = (x - pad, y - pad, w + 2 * pad, h + 2 * pad)
        self.crops.append(crop)
        try:
            if any(
                intersects(crop, (r.x, r.y, r.width, r.height))
                for r in self.unsupported
            ):
                return None
        except ReferenceError:
            return None
        return revision

    def close(self):
        for space, handle, kind in self.handlers:
            space.draw_handler_remove(handle, kind)
        self.handlers.clear()
        self.crops.clear()


def logical(rect, pixels, canvas):
    x, y, w, h = rect
    l, b, cw, ch = pixels
    sx, sy = w / max(1.0, canvas._width), h / max(1.0, canvas.height)
    return (l - x) / sx, (y + h - b - ch) / sy, cw / sx, ch / sy


def visible(canvas):
    if (
        canvas.overlay
        or canvas.context_menu
        or getattr(getattr(canvas, "_control_tip", None), "tooltip", None)
    ):
        return True
    return any(
        visible(child)
        for c in canvas._composites.values()
        if (child := getattr(c.options["widget"], "active_child", None)) is not None
    )


@contextmanager
def pixels():
    import gpu
    from mathutils import Matrix
    from .window_overlay import scissor_scope
    from ..gpu.paint import gpu_state

    with (
        gpu_state(),
        scissor_scope(),
        gpu.matrix.push_pop(),
        gpu.matrix.push_pop_projection(),
    ):
        _, _, w, h = gpu.state.viewport_get()
        gpu.state.viewport_set(0, 0, w, h)
        gpu.state.scissor_set(0, 0, w, h)
        gpu.matrix.load_matrix(Matrix.Identity(4))
        gpu.matrix.load_projection_matrix(
            Matrix(((2 / w, 0, 0, -1), (0, 2 / h, 0, -1), (0, 0, 1, 0), (0, 0, 0, 1)))
        )
        yield (0, 0, w, h)


def detach(host, key, record):
    entry = record.pop("popup_window", None)
    if entry:
        record.pop("popup_sources").close()
        active = _active.get(key[0], {})
        active.pop((id(host), key), None)
        if not active:
            _active.pop(key[0], None)
        from . import window_overlay

        window_overlay.detach(host.bridge, entry, (id(host), key))


def sync(host, context, key, record):
    from . import window_overlay
    from .bridge import BridgeUnavailable

    canvas = record["canvas"]
    window, area, region = context.window, context.area, context.region
    if not visible(canvas):
        detach(host, key, record)
        return False
    if record.get("popup_window"):
        return True

    def draw():
        import bpy
        from contextlib import nullcontext
        from ..gpu import glass
        from ..gpu.paint import paint

        if (
            host.closed
            or not record["valid"]
            or not canvas.visible
            or not visible(canvas)
        ):
            return
        x, y, w, h = record["rect"]
        rect = (region.x + x, region.y + y, w, h)
        # Source includes any editor below this sheet. Untracked native regions
        # may repaint independently of the invoking panel's revision.
        sources = record["popup_sources"]
        sources.crops.clear()

        def revision(sheet):
            owners = host.bridge.window_overlays[key[0]]["owners"]
            stamp = (
                record.get("popup_native_revision", 0)
                if next(iter(owners)) == (id(host), key)
                else None
            )
            return sources.sample(sheet, 20 * w / max(1, canvas._width), stamp)

        with (
            pixels() as clip,
            bpy.context.temp_override(window=window, area=area, region=region),
        ):
            with (
                glass.popup_pass(host, key, record, revision)
                if host.glass_enabled
                else nullcontext()
            ):
                paint(
                    canvas,
                    rect,
                    clip,
                    preferences=bpy.context.preferences,
                    font=host.font,
                    background=False,
                    controls=False,
                    composite_overlays=True,
                )

    try:
        window_overlay.attach(host.bridge, window, (id(host), key), draw)
    except BridgeUnavailable as error:
        record["popup_window_error"] = str(error)
        canvas._popup_clip = None
        return False

    def changed():
        record["popup_native_revision"] = record.get("popup_native_revision", 0) + 1

    try:
        record["popup_sources"] = Sources(
            window, changed, lambda a, r: a == area and r == region
        )
    except Exception:
        window_overlay.detach(host.bridge, window, (id(host), key))
        raise
    record["popup_window"] = window
    _active.setdefault(key[0], {})[(id(host), key)] = host
    return True
