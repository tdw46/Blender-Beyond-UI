"""Custom canvas anchoring and input routing for a host-owned Panel.

Host registers its own modal operator and calls event(). No classes, timers,
preferences, scene properties or input modals are installed by this library.
"""

from pathlib import Path
from .bridge import load, BridgeUnavailable


class PanelHost:
    def __init__(self, owner, *, backdrop_revision=None):
        if not owner:
            raise ValueError("Use a unique extension-qualified owner")
        self.owner = owner
        self.backdrop_revision = backdrop_revision
        self.bridge = None
        self.records = {}
        self.handlers = []
        self.font = -1
        self.font_path = ""
        self.reason = "Not started"
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
        import bpy, blf

        fonts = Path(bpy.utils.resource_path("LOCAL")) / "datafiles/fonts"
        path = next(iter(fonts.glob("Inter*.woff2")), None) or next(
            iter(fonts.glob("bfont*")), None
        )
        if path is None:
            self.bridge = None
            self.reason = "Blender UI font is unavailable"
            return False
        self.font_path = str(path)
        self.font = blf.load(self.font_path)
        if self.font < 0:
            self.bridge = None
            self.reason = "Could not load a private UI font"
            return False
        for space, region in (
            (bpy.types.SpaceView3D, "UI"),
            (bpy.types.SpaceProperties, "WINDOW"),
        ):
            handle = space.draw_handler_add(self._after_draw, (), region, "POST_PIXEL")
            self.handlers.append((space, handle, region))
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
        if self.backdrop_revision is not None:
            from ..gpu import glass

            revision = self.backdrop_revision(context)
            backdrop = (id(self), key)
            if not glass.draw(
                backdrop,
                revision,
                record["rect"],
                canvas.theme.radius,
                self.bridge.library,
                capture_rect=record["clip"],
            ):
                backdrop = None
        canvas.paint(
            record["rect"],
            record["clip"],
            preferences=context.preferences,
            font=self.font,
            backdrop=backdrop,
        )

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
        for key, record in tuple(self.records.items()):
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
                canvas.edit is not None
                or canvas.overlay is not None
                or canvas.widget_capture is not None
            )
            if not captured and not (cx <= px < cx + cw and cy <= py < cy + ch):
                continue
            sx = w / max(1.0, canvas._width)
            sy = h / max(1.0, canvas.height)
            clip = ((cx - x) / sx, (y + h - cy - ch) / sy, cw / sx, ch / sy)
            old_hover = canvas.hover
            with context.temp_override(window=window, area=area, region=region):
                consumed = canvas.event(
                    event,
                    (px - x) / sx,
                    (y + h - py) / sy,
                    clip,
                    clipboard=context.window_manager,
                )
            if consumed or old_hover != canvas.hover:
                region.tag_redraw()
            if consumed:
                return True
        return False

    def invalidate(self):
        """Call from undo_pre/load_pre; never retain old RNA transactions."""
        for record in self.records.values():
            record["canvas"].park()
            if self.bridge:
                self.bridge.records.pop(record["token"], None)
        from ..gpu import glass

        for key in list(glass._owners):
            if isinstance(key, tuple) and key and key[0] == id(self):
                glass._owners.pop(key, None)
        self.records.clear()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.invalidate()
        for space, handle, region in self.handlers:
            space.draw_handler_remove(handle, region)
        self.handlers.clear()
        if self.font >= 0:
            import blf

            blf.unload(self.font_path)
            self.font = -1
        self.bridge = None
