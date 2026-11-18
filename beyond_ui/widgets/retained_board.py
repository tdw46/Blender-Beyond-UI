"""A host-owned, fixed-coordinate board for densely arranged retained controls.

The consumer supplies its existing display list and stable data actions. The
panel supplies clipping, the glass underlay, pointer capture and the popup host.
Nothing is registered per board, and a settled board has no animation clock.
"""

from .base import Widget


def expanding_rows(
    width,
    top,
    entries,
    selected,
    *,
    inset=8.0,
    cell=40.0,
    gap=4.0,
    row_height=34.0,
    label_gap=14.0,
):
    """Measure row membership before revealing the selected item's caption."""
    columns = max(1, int((width - 2 * inset + gap) // (cell + gap)))
    x, y = inset, top
    positions = []
    for index, (key, text_width) in enumerate(entries):
        if index and index % columns == 0:
            x, y = inset, y + row_height + gap
        w = (
            min(width - 2 * inset, cell + text_width + label_gap)
            if key == selected
            else cell
        )
        positions.append((x, y, w, row_height))
        x += w + gap
    return positions, y + row_height + gap + inset if positions else top


def insertion_target(cards, y):
    """Return the stable key and 'before' bit using displayed card centers."""
    closest_distance = float("inf")
    target = None
    for key, (_, top, _, height) in cards:
        center = top + height * 0.5
        distance = abs(y - center)
        if distance < closest_distance:
            target = key, y < center
            closest_distance = distance
    return target


def horizontal_scroll_delta(event, scale, step=40.0):
    if event.type == "TRACKPADPAN":
        dx = event.mouse_x - event.mouse_prev_x
        dy = event.mouse_y - event.mouse_prev_y
        # Blender already applies the OS scroll mapping. Move content with
        # its horizontal pan delta; do not invert the preference again.
        return -dx / scale if abs(dx) >= abs(dy) and dx else None
    if event.type in {"WHEELLEFTMOUSE", "WHEELRIGHTMOUSE"}:
        return -step if event.type == "WHEELLEFTMOUSE" else step
    if getattr(event, "shift", False) and event.type in {
        "WHEELUPMOUSE",
        "WHEELDOWNMOUSE",
    }:
        return -step if event.type == "WHEELUPMOUSE" else step
    return None


def row_viewports(width, positions, inset=8.0):
    """Give each fixed row a viewport and a bounded horizontal scroll range."""
    ends = {}
    for x, y, w, h in positions:
        ends[y] = max(ends.get(y, 0), x + w)
    indices = {y: index for index, y in enumerate(ends)}
    return [
        (
            indices[y],
            (inset, y, width - 2 * inset, h),
            max(0.0, ends[y] - width + inset),
        )
        for _, y, _, h in positions
    ]


class ReorderGesture:
    """Preview insertion during a drag. The consumer commits its IDs on release."""

    def __init__(self, start, cards, threshold=4):
        self.start = start
        self.cards = tuple(cards)
        self.threshold = threshold
        self.moved = False
        self.drop = None

    def update(self, mouse, y, inside):
        if not self.moved:
            self.moved = (
                sum(abs(a - b) for a, b in zip(self.start, mouse)) > self.threshold
            )
        drop = insertion_target(self.cards, y) if self.moved and inside else None
        changed = self.drop != drop
        self.drop = drop
        return changed


class RetainedBoard(Widget):
    def __init__(self, canvas, width, height, paint, route, *, on_park=None):
        super().__init__()
        self.canvas_owner = canvas
        self.width, self.height = width, height
        self._paint, self._route = paint, route
        self.on_park = on_park
        self.control = None

    def dimensions(self, font_size, available_width, available_height=None):
        width = min(self.width, max(1.0, available_width))
        return width, self.height * width / self.width

    def paint(self, rect, font, palette, *, backdrop=None):
        self._paint(self, rect, font, backdrop)

    def route(self, event, x, y, clip, *, context, clipboard=None, menu_measure=None):
        return self._route(self, context, event, x, y, clip)

    def cancel(self):
        super().cancel()
        if self.on_park and not self.canvas_owner.visible:
            self.on_park(self)

    def all_children(self):
        return ()

    def advance(self, clip=None):
        return False

    def menu(self, target, rows, context):
        canvas = self.canvas_owner
        x, y = canvas._event_point
        return canvas.open_context(
            self.control,
            x,
            y,
            canvas._event_clip,
            context=context,
            target=target,
            entries=rows,
        )
