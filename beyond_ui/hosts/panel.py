"""Custom canvas anchoring and input routing for a host-owned Panel.

Host registers its own modal operator and calls event(). Finite animation timers
exist only while visible controls settle. Nothing is registered on import.
"""

from ..animation import AnimationSettings
from .bridge import load, BridgeUnavailable


class PanelHost:
    def __init__(
        self, owner, *, backdrop_revision=None, animation=None, glass_enabled=True
    ):
        if not owner:
            raise ValueError("Use a unique extension-qualified owner")
        self.animation = animation or AnimationSettings()
        self._animation_keys = set()
        self._animation_callback = self._animate
        self._tooltip_keys = set()
        self._tooltip_callback = self._reveal_tooltips
        self._in_tooltip_callback = False
        self.owner = owner
        self.backdrop_revision = backdrop_revision
        self.glass_enabled = bool(glass_enabled)
        self.bridge = None
        self.records = {}
        self.handlers = []
        self.font = -1
        self.reason = "Not started"
        self.menu_adapter_reason = "Not started"
        self.menu_context_reason = "Not started"
        self.closed = False

    def start(self):
        if self.bridge is not None:
            return True
        if self.closed:
            raise RuntimeError("Create a new PanelHost after close")
        try:
            self.bridge = load()
        except BridgeUnavailable as error:
            self.reason = str(error)
            return False
        import bpy
        from ..gpu.typography import Fonts
        from . import menu_native

        # Admission hashes once at host startup, never on the first menu paint.
        menu_native.api()
        self.menu_adapter_reason = menu_native.reason()
        from . import menu_context

        try:
            menu_context.api()
            self.menu_context_reason = ""
        except (RuntimeError, OSError, ValueError) as error:
            self.menu_context_reason = str(error)

        try:
            self.font = Fonts()
        except RuntimeError as error:
            self.bridge = None
            self.reason = str(error)
            return False
        for space, region in (
            (bpy.types.SpaceView3D, "UI"),
            (bpy.types.SpaceProperties, "WINDOW"),
        ):
            handle = space.draw_handler_add(self._after_draw, (), region, "POST_PIXEL")
            self.handlers.append((space, handle, region))
        handle = bpy.types.SpaceView3D.draw_handler_add(
            self._viewport_draw, (), "WINDOW", "POST_PIXEL"
        )
        self.handlers.append((bpy.types.SpaceView3D, handle, "WINDOW"))
        self.reason = ""
        return True

    @staticmethod
    def _key(context):
        return (
            context.window.as_pointer(),
            context.area.as_pointer(),
            context.region.as_pointer(),
        )

    def draw(self, layout, context, canvas):
        """Reserve ONE canvas in an exclusively host-owned Panel block.

        Returns False on unavailable hosts, so caller can draw its native path.
        Keep each canvas per window/area/region; never share interactive state.
        """
        if self.bridge is None or self.closed:
            return False
        if (context.area.type, context.region.type) not in {
            ("VIEW_3D", "UI"),
            ("PROPERTIES", "WINDOW"),
        }:
            return False
        key = self._key(context)
        scale = max(
            0.5,
            getattr(
                context.preferences.system,
                "ui_scale",
                getattr(context.preferences.view, "ui_scale", 1.0),
            ),
        )
        width = max(1.0, context.region.width / scale - 20.0)
        from ..gpu.paint import measure
        from ..gpu.typography import face

        font, size = self.font, canvas.theme.font_size
        measure_key = (id(self), int(font), getattr(font, "title", int(font)), size)
        if canvas._text_measure_key != measure_key:
            canvas.set_text_measure(
                lambda text, role: measure(
                    face(font, role), size * (12 / 11 if role == "title" else 1), text
                )[0],
                measure_key,
            )
        height = canvas.arrange(width)
        record = self.records.get(key)
        if record is None:
            token = self.bridge.next_token
            self.bridge.next_token += 1
            record = {
                "token": token,
                "canvas": canvas,
                "rect": None,
                "painted": False,
                "valid": False,
                "scene": context.scene.as_pointer(),
            }
            self.records[key] = record
            self.bridge.records[token] = lambda *rect: self._paint(key, *rect)
        elif (
            record["canvas"] is not canvas
            or record["scene"] != context.scene.as_pointer()
        ):
            record["canvas"].park()
            record["canvas"] = canvas
            record["scene"] = context.scene.as_pointer()
        # Old native blocks can outlive a layout rebuild. Revoke their tokens.
        self.bridge.records.pop(record["token"], None)
        record["token"] = self.bridge.next_token
        self.bridge.next_token += 1
        self.bridge.records[record["token"]] = lambda *rect: self._paint(key, *rect)
        record["valid"] = False
        record["painted"] = False
        canvas.visible = True
        canvas.bind_animation((self.animation,), lambda: self._wake_animation(key))
        canvas._tooltip_wake = lambda delay: self._schedule_tooltip(key, delay)
        raw = getattr(layout, "raw", layout)
        return bool(
            self.bridge.library.bvt_probe_reserve(
                raw.column().as_pointer(),
                max(1, int(width * scale)),
                max(1, int(height * scale)),
                record["token"],
            )
        )

    def _paint(self, key, x0, y0, x1, y1):
        import bpy

        context = bpy.context
        if self.closed or context.region is None or self._key(context) != key:
            return
        record = self.records.get(key)
        if record is None or record["scene"] != context.scene.as_pointer():
            return
        region = context.region
        left = max(0, x0)
        bottom = max(0, y0)
        right = min(region.width, x1)
        top = min(region.height, y1)
        canvas = record["canvas"]
        if right <= left or top <= bottom:
            record["valid"] = False
            canvas.park()
            return
        canvas.visible = True
        record["painted"] = True
        record["valid"] = True
        record["rect"] = (x0, y0, x1 - x0, y1 - y0)
        record["clip"] = (left, bottom, right - left, top - bottom)
        backdrop = None
        if self.glass_enabled:
            from ..gpu import glass

            revision = (
                self.backdrop_revision(context)
                if self.backdrop_revision
                else (record["scene"], canvas.backdrop_revision)
            )
            backdrop = (id(self), key)
            if not glass.draw(
                backdrop,
                revision,
                record["rect"],
                canvas.theme.radius,
                self.bridge.library,
                capture_rect=record["clip"],
                scale=min(
                    record["rect"][2] / max(1, canvas._width),
                    record["rect"][3] / max(1, canvas.height),
                ),
                viewport_source=glass.viewport_source(context),
            ):
                backdrop = None
        record["backdrop"] = backdrop
        record["glass_error"] = (
            ""
            if backdrop is not None
            else (glass.error if self.glass_enabled else "Glass explicitly disabled")
        )
        canvas.paint(
            record["rect"],
            record["clip"],
            preferences=context.preferences,
            font=self.font,
            backdrop=backdrop,
        )

    def _viewport_draw(self):
        import bpy
        from ..gpu import glass

        if self.glass_enabled and not self.closed:
            glass.viewport_changed(bpy.context, self.records)

    def _after_draw(self):
        import bpy

        context = bpy.context
        if context.region is None:
            return
        record = self.records.get(self._key(context))
        if record:
            record["valid"] = record["painted"]
            record["painted"] = False
            if not record["valid"]:
                record["canvas"].park()

    def event(self, context, event):
        """Window modal adapter; input outside the clipped anchor passes through."""
        if self.closed:
            return False
        window = context.window
        for key, record in sorted(
            tuple(self.records.items()),
            key=lambda item: item[1]["canvas"].active_menu() is None,
        ):
            if key[0] != window.as_pointer():
                continue
            area = next(
                (a for a in window.screen.areas if a.as_pointer() == key[1]), None
            )
            region = (
                next((r for r in area.regions if r.as_pointer() == key[2]), None)
                if area
                else None
            )
            canvas = record["canvas"]
            hidden = (
                area is not None
                and area.type == "VIEW_3D"
                and not area.spaces.active.show_region_ui
            )
            if region is None or hidden or not record["valid"] or not record["rect"]:
                canvas.park()
                continue
            px = event.mouse_x - region.x
            py = event.mouse_y - region.y
            x, y, w, h = record["rect"]
            cx, cy, cw, ch = record["clip"]
            captured = (
                canvas.context_menu is not None
                or canvas.edit is not None
                or canvas.overlay is not None
                or canvas.widget_capture is not None
                or (
                    (
                        canvas.keyboard_focus is not None
                        and event.type in canvas.navigation_keys
                    )
                    or (
                        canvas.context_focus is not None
                        and (event.type == "APP" or event.type == "F10" and event.shift)
                    )
                )
            )
            if not captured and not (cx <= px < cx + cw and cy <= py < cy + ch):
                if (
                    event.type == "LEFTMOUSE"
                    and event.value == "PRESS"
                    and (
                        canvas.keyboard_focus is not None
                        or canvas.context_focus is not None
                    )
                ):
                    canvas.blur_focus()
                    canvas.context_focus = None
                    region.tag_redraw()
                if canvas.hover is not None:
                    canvas.hover = None
                    if canvas._motion_focus:
                        canvas._motion_focus.hover = None
                        canvas._motion_focus.pointer = None
                    region.tag_redraw()
                continue
            sx = w / max(1.0, canvas._width)
            sy = h / max(1.0, canvas.height)
            clip = ((cx - x) / sx, (y + h - cy - ch) / sy, cw / sx, ch / sy)
            old_hover = canvas.hover
            from ..gpu.paint import measure
            from ..gpu.typography import face

            with context.temp_override(window=window, area=area, region=region):
                consumed = canvas.event(
                    event,
                    (px - x) / sx,
                    (y + h - py) / sy,
                    clip,
                    clipboard=context.window_manager,
                    context=context,
                    menu_measure=lambda text, size: measure(
                        face(self.font, "body"), size, text
                    )[0],
                )
            if consumed or old_hover != canvas.hover:
                region.tag_redraw()
            if consumed:
                if (
                    event.type in {"LEFTMOUSE", "RIGHTMOUSE", "APP", "F10"}
                    and event.value == "PRESS"
                ):
                    for other_key, other in self.records.items():
                        if other_key != key and other_key[0] == key[0]:
                            other["canvas"].blur_focus()
                            other["canvas"].close_context()
                            other["canvas"].context_focus = None
                return True
        return False

    def _schedule_tooltip(self, key, delay):
        import bpy

        if delay is None:
            self._wake_animation(key)  # One final redraw removes a visible description.
            self._tooltip_keys.discard(key)
            if (
                not self._tooltip_keys
                and not self._in_tooltip_callback
                and bpy.app.timers.is_registered(self._tooltip_callback)
            ):
                bpy.app.timers.unregister(self._tooltip_callback)
            return
        if self.closed or key not in self.records:
            return
        self._tooltip_keys.add(key)
        if not bpy.app.timers.is_registered(self._tooltip_callback):
            bpy.app.timers.register(self._tooltip_callback, first_interval=delay)

    def _reveal_tooltips(self):
        import bpy

        delays = []
        self._in_tooltip_callback = True
        try:
            for key in tuple(self._tooltip_keys):
                record = self.records.get(key)
                menu = record["canvas"].active_menu() if record else None
                owner = next(
                    (
                        (w, a, r)
                        for w in bpy.context.window_manager.windows
                        for a in w.screen.areas
                        for r in a.regions
                        if (w.as_pointer(), a.as_pointer(), r.as_pointer()) == key
                    ),
                    None,
                )
                visible = (
                    owner and record and record["valid"] and record["canvas"].visible
                )
                if (
                    owner
                    and owner[1].type == "VIEW_3D"
                    and not owner[1].spaces.active.show_region_ui
                ):
                    visible = False
                if not visible or menu is None:
                    if menu:
                        menu.hide_tip()
                    self._tooltip_keys.discard(key)
                    continue
                window, area, region = owner
                with bpy.context.temp_override(window=window, area=area, region=region):
                    delay = menu.reveal_tip(bpy.context)
                region.tag_redraw()
                if delay is None:
                    self._tooltip_keys.discard(key)
                else:
                    delays.append(delay)
        finally:
            self._in_tooltip_callback = False
        return max(0.01, min(delays)) if delays else None

    def _wake_animation(self, key):
        if self.closed or key not in self.records:
            return
        import bpy

        self._animation_keys.add(key)
        if not bpy.app.timers.is_registered(self._animation_callback):
            bpy.app.timers.register(self._animation_callback, first_interval=0.0)

    def _animate(self):
        import bpy

        if self.closed:
            return None
        for key in tuple(self._animation_keys):
            record = self.records.get(key)
            window = next(
                (
                    w
                    for w in bpy.context.window_manager.windows
                    if w.as_pointer() == key[0]
                ),
                None,
            )
            area = (
                next((a for a in window.screen.areas if a.as_pointer() == key[1]), None)
                if window
                else None
            )
            region = (
                next((r for r in area.regions if r.as_pointer() == key[2]), None)
                if area
                else None
            )
            visible = (
                region is not None
                and record
                and record["valid"]
                and record["canvas"].visible
            )
            if (
                area
                and area.type == "VIEW_3D"
                and not area.spaces.active.show_region_ui
            ):
                visible = False
            if not visible:
                if record:
                    record["canvas"].park()
                self._animation_keys.discard(key)
                continue
            # One last redraw publishes exact rest when the last spring expires.
            region.tag_redraw()
            canvas = record["canvas"]
            x, y, w, h = record["rect"]
            cx, cy, cw, ch = record["clip"]
            sx, sy = w / max(1.0, canvas._width), h / max(1.0, canvas.height)
            clip = ((cx - x) / sx, (y + h - cy - ch) / sy, cw / sx, ch / sy)
            if not canvas.advance_animations(clip):
                self._animation_keys.discard(key)
        return 1 / 60 if self._animation_keys else None

    def invalidate(self):
        """Call from undo_pre/load_pre; never retain old RNA transactions."""
        for record in self.records.values():
            record["canvas"].park()
            record["canvas"].set_text_measure(None, None)
            if self.bridge:
                self.bridge.records.pop(record["token"], None)
        from ..gpu import glass

        for key in list(glass._owners):
            if isinstance(key, tuple) and key and key[0] == id(self):
                glass._owners.pop(key, None)
        self.records.clear()
        self._animation_keys.clear()
        self._tooltip_keys.clear()
        import bpy

        if bpy.app.timers.is_registered(self._animation_callback):
            bpy.app.timers.unregister(self._animation_callback)
        if bpy.app.timers.is_registered(self._tooltip_callback):
            bpy.app.timers.unregister(self._tooltip_callback)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.invalidate()
        for space, handle, region in self.handlers:
            space.draw_handler_remove(handle, region)
        self.handlers.clear()
        if self.font >= 0:
            self.font.close()
            self.font = -1
        self.bridge = None
