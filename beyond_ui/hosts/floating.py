"""Owned region overlay using the existing panel input, glass and motion paths."""

from .panel import PanelHost
from .bridge import load, BridgeUnavailable
from ..canvas import Canvas
from ..gpu.typography import Fonts, face
from ..gpu.paint import measure, paint


def visible_region_rect(area, region):
    """Area drawing bounds in WINDOW pixels, including overlapping sidebars.

    Window-level presentation is above UI/TOOLS, so their bounds must not push
    popups away from the clicked control. Header rows remain outside the host.
    """
    left, bottom, right, top = 0, 0, region.width, region.height
    for other in area.regions:
        if other.width <= 1 or other.height <= 1:
            continue
        x, y = other.x - region.x, other.y - region.y
        if other.type in {"UI", "TOOLS"}:
            left, right = min(left, x), max(right, x + other.width)
            bottom, top = min(bottom, y), max(top, y + other.height)
    for other in area.regions:
        if other.type not in {"HEADER", "TOOL_HEADER"} or other.height <= 1:
            continue
        y = other.y - region.y
        if y < top and y + other.height > bottom:
            if y <= bottom: bottom = min(top, y + other.height)
            else: top = max(bottom, y)
    return left, bottom, max(1, right-left), max(1, top-bottom)



class FloatingHost(PanelHost):
    def __init__(
        self, owner, context, *, animation=None, registry=None, stylesheet=None
    ):
        super().__init__(owner, animation=animation)
        self.window, self.area = context.window, context.area
        self.origin_region = context.region
        if self.window is None or self.area is None:
            raise BridgeUnavailable("Custom popups require an editor window")
        self.region = next((r for r in self.area.regions if r.type == "WINDOW"), None)
        if self.region is None or self.area.type not in {"VIEW_3D", "PROPERTIES"}:
            raise BridgeUnavailable(
                "Custom popup host supports 3D View and Properties editors"
            )
        self.bridge = load()
        from . import menu_native, menu_context

        menu_native.api()
        self.menu_adapter_reason = menu_native.reason()
        try:
            menu_context.api()
            self.menu_context_reason = ""
        except (RuntimeError, OSError, ValueError) as error:
            self.menu_context_reason = str(error)
        self.font = Fonts()
        self.canvas = Canvas(shortcut_registry=registry)
        if stylesheet is not None:
            stylesheet.apply(self.canvas)
        self.key = (
            self.window.as_pointer(),
            self.area.as_pointer(),
            self.region.as_pointer(),
        )
        self.scene = context.scene.as_pointer()
        self.reason = ""
        self.scale = max(0.5, getattr(context.preferences.system, "ui_scale", 1.0))
        self.canvas.set_text_measure(
            lambda text, role: measure(
                face(self.font, role),
                self.canvas.theme.font_size * (12 / 11 if role == "title" else 1),
                text,
            )[0],
            (id(self), int(self.font)),
        )
        self.canvas.bind_animation(
            (self.animation,), lambda: self._wake_animation(self.key)
        )
        self.canvas.bind_context_tooltips(
            lambda delay: self._schedule_tooltip(self.key, delay)
        )
        self.size()
        # All field/child animation ticks share this record and one glass revision.
        self.records[self.key] = dict(
            canvas=self.canvas,
            rect=self.rect,
            clip=self.rect,
            valid=True,
            painted=True,
            scene=self.scene,
            token=-1,
            context_region=self.origin_region,
        )
        self.space = type(self.area.spaces.active)
        from . import window_overlay
        self._source_revision = 0
        self._source_signature = None
        self._scene_changed = True
        self._scene_callback = self._changed
        try:
            window_overlay.attach(self.bridge, self.window, id(self), self._draw)
        except Exception:
            self.close()
            raise
        # Track completed viewport revisions, not popup animation frames.
        handle = self.space.draw_handler_add(self._source_draw, (), "WINDOW", "POST_PIXEL")
        self.handlers.append((self.space, handle, "WINDOW"))
        import bpy
        bpy.app.handlers.depsgraph_update_post.append(self._scene_callback)
        self.region.tag_redraw()

    def _changed(self, scene, *_args):
        if scene.as_pointer() == self.scene:
            self._scene_changed = True

    def _source_draw(self):
        import bpy
        context = bpy.context
        if self.closed or context.region is None or self._key(context) != self.key:
            return
        view = getattr(context, "region_data", None)
        signature = (
            self.region.width, self.region.height,
            tuple(v for row in view.perspective_matrix for v in row) if view else (),
        )
        if self._scene_changed or signature != self._source_signature:
            self._source_signature = signature
            self._source_revision += 1
            self._scene_changed = False
        self._source_ready = True

    def size(self):
        self.rect = visible_region_rect(self.area, self.region)
        self.canvas._width = self.rect[2] / self.scale
        self.canvas.height = self.rect[3] / self.scale
        self.clip = (0, 0, self.canvas._width, self.canvas.height)
        self.canvas._event_clip = self.clip

    def anchor(self, event):
        if event is None:
            return self.clip[2] / 2, self.clip[3] / 2
        return (
            (event.mouse_x - self.region.x - self.rect[0]) / self.scale,
            (self.region.y + self.rect[1] + self.rect[3] - event.mouse_y) / self.scale,
        )

    def _draw(self):
        import bpy
        import gpu
        from mathutils import Matrix
        from ..gpu import glass
        from ..gpu.paint import gpu_state
        from .window_overlay import scissor_scope

        context = bpy.context
        if self.closed or not self.alive(context) or not getattr(self, "_source_ready", False):
            return
        record = self.records[self.key]
        try:
            self.size()
            record.update(rect=self.rect, clip=self.rect)
            x, y, w, h = self.rect
            # Event records stay region-local; painting is window-global.
            rect = (x + self.region.x, y + self.region.y, w, h)
            backdrop = (id(self), self.key)
            source = None
            if (self.area.type == "VIEW_3D"
                    and getattr(context.preferences.system, "use_region_overlap", False)):
                source = (self.region.as_pointer(), self.region.x, self.region.y,
                          self._source_revision, self.region.width, self.region.height)
            with gpu_state(), scissor_scope(), gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                # Window RNA dimensions are logical points on Retina; the current
                # compositor viewport and ARegion bounds are framebuffer pixels.
                _, _, ww, wh = gpu.state.viewport_get()
                gpu.state.viewport_set(0, 0, ww, wh)
                gpu.state.scissor_set(0, 0, ww, wh)
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix((
                    (2 / ww, 0, 0, -1), (0, 2 / wh, 0, -1),
                    (0, 0, 1, 0), (0, 0, 0, 1))))
                ready = glass.draw(
                    backdrop, (self.scene, self.canvas.backdrop_revision, self._source_revision),
                    rect, self.canvas.theme.radius, self.bridge.library,
                    scale=self.scale, viewport_source=source,
                    framebuffer_size=(ww, wh), prepare_only=True,
                )
                record["backdrop"] = backdrop if ready else None
                record["glass_error"] = "" if ready else glass.error
                record["viewport_source"] = source
                record["window_rect"] = rect
                with context.temp_override(window=self.window, area=self.area,
                                           region=self.origin_region):
                    paint(self.canvas, rect, rect, preferences=context.preferences,
                          font=self.font, backdrop=record["backdrop"],
                          background=False, controls=False)
            record["valid"] = True
            self.reason = ""
        except Exception as error:
            self.reason = f"{type(error).__name__}: {error}"
            record["valid"] = False

    def alive(self, context):
        try:
            return (
                not self.closed
                and self.scene == context.scene.as_pointer()
                and any(a.as_pointer() == self.key[1] for a in self.window.screen.areas)
                and self.region.width > 0
                and self.region.height > 0
            )
        except (ReferenceError, AttributeError):
            return False

    def close(self):
        if self.closed:
            return
        from . import window_overlay
        import bpy
        window_overlay.detach(self.bridge, self.window, id(self))
        callback = getattr(self, "_scene_callback", None)
        if callback in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(callback)
        super().close()
        try:
            self.region.tag_redraw()
        except ReferenceError:
            pass
