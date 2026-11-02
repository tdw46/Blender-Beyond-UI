"""Owned region overlay using the existing panel input, glass and motion paths."""

from .panel import PanelHost
from .bridge import load, BridgeUnavailable
from ..canvas import Canvas
from ..gpu.typography import Fonts, face
from ..gpu.paint import measure, paint


def visible_region_rect(area, region):
    """Unoccluded drawing space, in WINDOW-region pixels (not screen pixels).

    POST_PIXEL runs before overlapping UI/TOOLS regions. Constrain floating
    surfaces to the exposed viewport rather than painting under those regions.
    """
    left, bottom, right, top = 0, 0, region.width, region.height
    for other in area.regions:
        if other is region or other.type not in {"UI", "TOOLS", "HEADER", "TOOL_HEADER"}:
            continue
        if other.width <= 1 or other.height <= 1:
            continue
        x, y = other.x - region.x, other.y - region.y
        x2, y2 = x + other.width, y + other.height
        if x2 <= left or x >= right or y2 <= bottom or y >= top:
            continue
        if other.type in {"HEADER", "TOOL_HEADER"}:
            if y <= bottom: bottom = min(top, y2)
            else: top = max(bottom, y)
        elif x <= left:
            left = min(right, x2)
        else:
            right = max(left, x)
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
        handle = self.space.draw_handler_add(self._draw, (), "WINDOW", "POST_PIXEL")
        self.handlers.append((self.space, handle, "WINDOW"))
        self.region.tag_redraw()

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
        from ..gpu import glass

        context = bpy.context
        if self.closed or context.region is None or self._key(context) != self.key:
            return
        record = self.records[self.key]
        try:
            self.size()
            record.update(rect=self.rect, clip=self.rect)
            backdrop = (id(self), self.key)
            ready = glass.draw(
                backdrop,
                (self.scene, self.canvas.backdrop_revision),
                self.rect,
                self.canvas.theme.radius,
                self.bridge.library,
                scale=self.scale,
                prepare_only=True,
            )
            record["backdrop"] = backdrop if ready else None
            record["glass_error"] = "" if ready else glass.error
            # Ownership guards use the invoking region, while pixels target the
            # viewport. Otherwise sidebar-authored popovers paint only a shell.
            with context.temp_override(window=self.window, area=self.area,
                                       region=self.origin_region):
                paint(
                    self.canvas,
                    self.rect,
                    self.rect,
                    preferences=context.preferences,
                    font=self.font,
                    backdrop=record["backdrop"],
                    background=False,
                    controls=False,
                )
            record["valid"] = True
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
        super().close()
        try:
            self.region.tag_redraw()
        except ReferenceError:
            pass
