"""An on-demand PanelPopover for tools with stable data keys and dynamic sheets."""

from types import SimpleNamespace

from .operator_enum import context_key
from .popover import RegisteredPanel
from .registered_menu import ContextArguments


class CallbackPanel(RegisteredPanel):
    """Use the registered-panel layout, nested input, scroll and cleanup policies.

    draw receives a Layout and the current context. The validity callback must
    re-resolve the data owner. Both run on interaction, never from GPU paint.
    """

    def __init__(
        self,
        layout,
        title,
        draw,
        valid,
        *,
        width=20,
        changed=None,
        closed=None,
        content_scroll=False,
        windowed_rows=None,
    ):
        self.layout = layout
        self.name = self.label = title
        self.context = layout.context
        self.direction = "VERTICAL"
        self.invocation = layout.operator_context
        self.pointers = ContextArguments()
        self.windowed_rows = windowed_rows
        self.content_scroll = content_scroll
        self.closed = closed
        self._valid = valid
        self.cls = SimpleNamespace(
            bl_ui_units_x=width,
            draw=lambda panel, ctx: draw(panel.layout, ctx),
            beyond_ui_changed=changed or (lambda ctx, before, after: False),
        )

    def available(self, context, scope=None, *, poll=True):
        return (scope is None or context_key(context) == scope) and self._valid(context)

    def check(self, context, scope=None, *, poll=True):
        if not self.available(context, scope):
            raise ReferenceError("Popup data owner or context changed")

    def refresh_poll(self, context):
        pass

    def native_fallback(self, context, error):
        return False


class WindowedRows:
    """Materialize rows near the scroll thumb, retaining space for the others."""

    def __init__(self, block=32):
        self.block = block
        self.first = 0
        self.stride = 1
        self.count = 0
        self.capacity = 2 * block

    def move(self, offset, viewport):
        first = (
            max(0, min(self.count - 1, int(offset / self.stride)) // self.block - 1)
            * self.block
        )
        capacity = max(2 * self.block, int(viewport / self.stride) + 2 * self.block + 1)
        changed = first != self.first or capacity > self.capacity
        self.first, self.capacity = first, max(self.capacity, capacity)
        return changed and self.count > 2 * self.block

    def visible(self, layout, rows):
        theme = layout.canvas.theme
        self.stride = theme.row_height + theme.gap
        self.count = len(rows)
        if self.count <= self.block * 2:
            self.first = 0
            yield from rows
            return
        start = min(self.first, self.count - 1)
        end = min(self.count, start + self.capacity)

        def spacer(count):
            layout.group.label(
                layout._key("virtual-space"),
                "",
                height=max(0, count * self.stride - theme.gap),
            )

        if start:
            spacer(start)
        yield from rows[start:end]
        if end < self.count:
            spacer(self.count - end)
