"""Small retained painter and event contracts for compound custom controls."""

from contextlib import contextmanager, nullcontext
from ..animation import Motion
from ..editing import Text, number
from ..gpu import style
from ..gpu.paint import measure


class Painter:
    def __init__(
        self,
        rect,
        width,
        height,
        font,
        palette,
        backdrop=None,
        *,
        motion=None,
        interactive=True,
    ):
        self.motion = motion
        self.interactive = interactive
        self._clip = None
        if motion is not None:
            motion.begin_paint()
        self.rect, self.width, self.height = rect, width, height
        self.font, self.palette, self.backdrop = font, palette, backdrop
        self.sx, self.sy = rect[2] / width, rect[3] / height
        self.scale = min(self.sx, self.sy)

    def map(self, r):
        x, y, w, h = r
        rx, ry, rw, rh = self.rect
        return rx + x * self.sx, ry + rh - (y + h) * self.sy, w * self.sx, h * self.sy

    @contextmanager
    def clip(self, r):
        """Intersect the caller-owned enabled scissor; restore its exact box."""
        import gpu
        from math import ceil, floor

        previous = gpu.state.scissor_get()
        prior_clip = self._clip
        x, y, w, h = self.map(r)
        a, b, c, d = previous
        left, bottom = max(x, a), max(y, b)
        right, top = min(x + w, a + c), min(y + h, b + d)
        self._clip = (left, bottom, max(left, right), max(bottom, top))
        gpu.state.scissor_set(
            ceil(left),
            ceil(bottom),
            max(0, floor(right) - ceil(left)),
            max(0, floor(top) - ceil(bottom)),
        )
        try:
            yield
        finally:
            gpu.state.scissor_set(*previous)
            self._clip = prior_clip

    def surface(self, r, role="field", radius=8, border=0.7, *, motion_key=None):
        from ..gpu import skin

        colors = self.palette["surfaces"].get(role) if isinstance(role, str) else None
        if colors is None:
            color = self.palette.get(role, role) if isinstance(role, str) else role
            colors = (color, color)
        if (
            motion_key is None
            and isinstance(role, str)
            and role in {"field", "input", "button", "tab", "selected", "thumb"}
        ):
            motion_key = tuple(r)
        if self.motion is not None and motion_key is not None:
            if self.interactive:
                self.motion.region(motion_key, r)
            if motion_key in self.motion.tracks:
                with self.motion.deform(motion_key, self.map(r)):
                    skin.draw(
                        self.map(r),
                        *colors,
                        radius=radius * self.scale,
                        border=border * self.scale,
                    )
                return
        skin.draw(
            self.map(r), *colors, radius=radius * self.scale, border=border * self.scale
        )

    def deform(self, key, r, *, circular=False):
        if self.motion is None or key is None:
            return nullcontext()
        if self.interactive:
            self.motion.region(key, r, circular=circular)
        return self.motion.deform(key, self.map(r))

    def card(self, title, *, title_inset=67):
        from ..gpu import glass

        r = (0, 0, self.width, self.height)
        # Reuse the source host's one blurred backdrop, not one capture per control.
        if self.backdrop is None or not glass.lens(
            self.backdrop,
            self.map(r),
            14 * self.scale,
            self.palette["surfaces"]["card"][0],
        ):
            self.surface(r, "card", 14, 1)
        self.surface((1, 1, self.width - 2, 59), "header", 13, 0)
        self.line(
            ((1, 60), (self.width - 1, 60)),
            self.palette["header_divider"],
            0.8 * self.scale,
        )
        self.triangle(((23, 28), (39, 28), (31, 39)), self.palette["muted"])
        self.text(
            (title_inset, 0, self.width - title_inset - 48, 60),
            title,
            size=28,
            inset=0,
            weight="title",
        )
        for y in (22, 32, 42):
            self.circle((self.width - 29, y), 2, self.palette["muted"])

    def text(
        self, r, value, role="text", size=22, *, align="left", inset=16, weight="body"
    ):
        import blf
        from ..gpu import typography

        a, b, w, h = self.map(r)
        font = typography.face(self.font, weight)
        size *= self.scale
        blf.size(font, size)
        blf.color(
            font,
            *self.palette["title" if weight == "title" and role == "text" else role],
        )
        blf.enable(font, blf.CLIPPING)
        try:
            bounds = (a, b, a + w, b + h)
            if self._clip is not None:
                bounds = (
                    max(a, self._clip[0]),
                    max(b, self._clip[1]),
                    min(a + w, self._clip[2]),
                    min(b + h, self._clip[3]),
                )
            if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                return
            blf.clipping(font, *bounds)
            tw, _ = measure(font, size, str(value))
            x = (
                a + (w - tw) / 2
                if align == "center"
                else a + w - tw - inset * self.scale
                if align == "right"
                else a + inset * self.scale
            )
            blf.position(font, x, b + (h - measure(font, size, "H")[1]) / 2, 0)
            blf.draw(font, str(value))
        finally:
            blf.disable(font, blf.CLIPPING)

    def field(self, r, label, value, split=64, size=22):
        self.surface(r)
        x, y, w, h = r
        self.surface(
            (x + split, y + 1, w - split - 1, h - 2),
            self.palette["field_inset"],
            radius=7,
            border=0,
        )
        self.text((x, y, split, h), label, size=size)
        self.text((x + split, y, w - split, h), value, size=size, inset=22)

    def chevron(self, x, y, size=15):
        self.line(
            (
                (x - size / 2, y - size / 4),
                (x, y + size / 4),
                (x + size / 2, y - size / 4),
            ),
            self.palette["text"],
            1.8 * self.scale,
        )

    def circle(self, center, radius, color, border=0, *, motion_key=None):
        from ..gpu import skin

        x, y = center
        r = (x - radius, y - radius, radius * 2, radius * 2)
        with self.deform(motion_key, r, circular=True):
            skin.draw(
                self.map(r),
                color,
                radius=radius * self.scale,
                border=border * self.scale,
                mode=3,
            )

    def triangle(self, points, color):
        import gpu
        from gpu_extras.batch import batch_for_shader

        global _TRI_SHADER
        if _TRI_SHADER is None:
            _TRI_SHADER = gpu.shader.from_builtin("UNIFORM_COLOR")
        coords = tuple((x, self.height - y) for x, y in points)
        key = ("triangle", coords)
        item = _LINE_CACHE.get(key)
        if item is None:
            item = (_TRI_SHADER, batch_for_shader(_TRI_SHADER, "TRIS", {"pos": coords}))
            if len(_LINE_CACHE) >= 256:
                _LINE_CACHE.pop(next(iter(_LINE_CACHE)))
            _LINE_CACHE[key] = item
        shader, batch = item
        gpu.state.blend_set("ALPHA")
        with gpu.matrix.push_pop():
            gpu.matrix.translate((self.rect[0], self.rect[1], 0))
            gpu.matrix.scale((self.sx, self.sy, 1))
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)

    def icon(self, name, r, size=32, *, role="text"):
        from .icon_paths import paths, transformed

        outlines = paths(name)
        if not outlines:
            x, y, w, h = self.map(r)
            style.icon(
                name, x + w / 2, y + h / 2, size * self.scale, self.palette[role]
            )
            return
        self.line(
            transformed(name, tuple(r), size), self.palette[role], 2.2 * self.scale
        )

    def lines(self, paths, color, width=1):
        self.line(
            tuple(value for path in paths for value in (*path, None)), color, width
        )

    def line(self, points, color, width=1):
        shader, batch = line_batch(
            tuple(points),
            tuple(color),
            (0, 0, self.width, self.height),
            self.width,
            self.height,
            width / max(self.scale, 1e-9),
        )
        import gpu

        gpu.state.blend_set("ALPHA")
        with gpu.matrix.push_pop():
            gpu.matrix.translate((self.rect[0], self.rect[1], 0))
            gpu.matrix.scale((self.sx, self.sy, 1))
            shader.bind()
            shader.uniform_float(
                "mvp",
                gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix(),
            )
            shader.uniform_float("color", color)
            batch.draw(shader)


_LINE_CACHE = {}
_LINE_SHADER = None
_TRI_SHADER = None


def line_batch(points, color, rect, width, height, thickness):
    import gpu
    from gpu_extras.batch import batch_for_shader

    global _LINE_SHADER
    key = ("line", points, rect, width, height, thickness)
    item = _LINE_CACHE.get(key)
    if item is not None:
        return item
    if _LINE_SHADER is None:
        interface = gpu.types.GPUStageInterfaceInfo("beyond_ui_aa_line")
        interface.smooth("FLOAT", "edge")
        info = gpu.types.GPUShaderCreateInfo()
        info.vertex_in(0, "VEC2", "pos")
        info.vertex_in(1, "FLOAT", "distance")
        info.vertex_out(interface)
        info.fragment_out(0, "VEC4", "fragColor")
        info.push_constant("MAT4", "mvp")
        info.push_constant("VEC4", "color")
        info.vertex_source(
            "void main(){edge=distance;gl_Position=mvp*vec4(pos,0.,1.);}"
        )
        info.fragment_source(
            "void main(){float a=1.-smoothstep(.15,1.,abs(edge));fragColor=vec4(color.rgb,color.a*a);}"
        )
        _LINE_SHADER = gpu.shader.create_from_info(info)
    x, y, w, h = rect
    verts = []
    edges = []
    paths = [[]]
    for point in points:
        if point is None:
            if paths[-1]:
                paths.append([])
        else:
            px, py = point
            paths[-1].append((x + px * w / width, y + h - py * h / height))
    from math import hypot

    for coords in paths:
        if len(coords) < 2:
            continue
        normals = []
        closed = len(coords) > 2 and coords[0] == coords[-1]
        for i, (px, py) in enumerate(coords):
            prev = coords[-2] if closed and i == 0 else coords[max(0, i - 1)]
            nxt = (
                coords[1]
                if closed and i == len(coords) - 1
                else coords[min(len(coords) - 1, i + 1)]
            )
            dx, dy = nxt[0] - prev[0], nxt[1] - prev[1]
            length = max(1e-9, hypot(dx, dy))
            nx, ny = -dy / length, dx / length
            seg = coords[i + 1] if i + 1 < len(coords) else coords[i - 1]
            dx, dy = seg[0] - px, seg[1] - py
            length = max(1e-9, hypot(dx, dy))
            factor = 1 / max(0.5, abs(nx * (-dy / length) + ny * (dx / length)))
            normals.append((nx * factor, ny * factor))
        half = thickness / 2
        cuts = (-(half + 0.7), -max(0.0, half - 0.7), max(0.0, half - 0.7), half + 0.7)
        for i in range(len(coords) - 1):

            def point(index, offset):
                px, py = coords[index]
                nx, ny = normals[index]
                return (px + nx * offset, py + ny * offset)

            for left, right, le, re in zip(
                cuts, cuts[1:], (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
            ):
                verts.extend(
                    (
                        point(i, left),
                        point(i, right),
                        point(i + 1, left),
                        point(i, right),
                        point(i + 1, right),
                        point(i + 1, left),
                    )
                )
                edges.extend((le, re, le, re, re, le))
    item = (
        _LINE_SHADER,
        batch_for_shader(_LINE_SHADER, "TRIS", {"pos": verts, "distance": edges}),
    )
    if len(_LINE_CACHE) >= 256:
        _LINE_CACHE.pop(next(iter(_LINE_CACHE)))
    _LINE_CACHE[key] = item
    return item


def clear():
    global _LINE_SHADER, _TRI_SHADER
    _LINE_CACHE.clear()
    _LINE_SHADER = _TRI_SHADER = None


def contains(rect, x, y):
    a, b, w, h = rect
    return a <= x < a + w and b <= y < b + h


class Widget:
    width = 320.0
    height = 240.0

    def __init__(self):
        self.motion = Motion()
        self.capturing = False
        self.text_edit = None
        self.field = None

    def cancel(self):
        self.motion.clear()
        self.capturing = False
        self.text_edit = None
        self.field = None

    def event(self, event, x, y, *, clipboard=None):
        return False

    def edit_text(self, event, *, clipboard=None):
        """Return submitted string, None while editing, or False on cancel."""
        if event.value not in {"PRESS", "DOUBLE_CLICK"}:
            return None
        kind = event.type
        edit = self.text_edit
        if kind == "ESC":
            self.text_edit = None
            self.capturing = False
            return False
        if kind in {"RET", "NUMPAD_ENTER"}:
            value = edit.text
            self.text_edit = None
            self.capturing = False
            return value
        command = getattr(event, "ctrl", False) or getattr(event, "oskey", False)
        if command and kind == "A":
            edit.anchor = 0
            edit.cursor = len(edit.text)
        elif command and kind in {"C", "X"} and clipboard is not None:
            a, b = sorted((edit.anchor, edit.cursor))
            clipboard.clipboard = edit.text[a:b]
            if kind == "X":
                edit.erase()
        elif command and kind == "V" and clipboard is not None:
            edit.insert(clipboard.clipboard)
        elif kind in {"BACK_SPACE", "DEL"}:
            edit.erase(kind == "BACK_SPACE")
        elif kind in {"LEFT_ARROW", "RIGHT_ARROW", "HOME", "END"}:
            edit.move(
                {
                    "LEFT_ARROW": edit.cursor - 1,
                    "RIGHT_ARROW": edit.cursor + 1,
                    "HOME": 0,
                    "END": len(edit.text),
                }[kind],
                getattr(event, "shift", False),
            )
        elif getattr(event, "unicode", "") and not command:
            edit.insert(event.unicode)
        return None
