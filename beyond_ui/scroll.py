"""Blender scroll events to a top-origin content offset (positive = later rows)."""

SCROLL_EVENTS = frozenset({"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"})


class NativeScrollGesture:
    """Keep a native panel scroll from being intercepted as its contents move.

    Wheel/trackpad events have no portable public gesture-end phase. Expire on
    input-time inactivity instead; pointer motion and redraws are not an end.
    Only scalar window/region identifiers are retained, never RNA or controls.
    """

    settle_seconds = 0.30

    def __init__(self):
        self.windows = {}

    def clear(self, window=None):
        if window is None:
            self.windows.clear()
        else:
            self.windows.pop(window, None)

    def continuing(self, key, now):
        previous = self.windows.get(key[0])
        if previous and previous[0] == key and 0 <= now - previous[1] < self.settle_seconds:
            self.remember(key, now)
            return True
        self.clear(key[0])
        return False

    def remember(self, key, now):
        if len(self.windows) >= 16 and key[0] not in self.windows:
            self.windows.pop(next(iter(self.windows)))
        self.windows[key[0]] = (key, now)


def panel_scroll_region(context, event):
    """Find the region under window-space input, not the modal's invoke region."""
    window = getattr(context, "window", None)
    if window is None:
        return None
    x, y = event.mouse_x, event.mouse_y
    for area in window.screen.areas:
        if area.type not in {"VIEW_3D", "PROPERTIES"}:
            continue
        region_type = "UI" if area.type == "VIEW_3D" else "WINDOW"
        if region_type == "UI" and not area.spaces.active.show_region_ui:
            continue
        for region in area.regions:
            if (region.type == region_type and region.width > 0 and region.height > 0
                    and region.x <= x < region.x + region.width
                    and region.y <= y < region.y + region.height):
                return window.as_pointer(), area.as_pointer(), region.as_pointer()
    return None


def scroll_delta(event, wheel_step=1.0):
    if event.type == "WHEELUPMOUSE":
        return -wheel_step
    if event.type == "WHEELDOWNMOUSE":
        return wheel_step
    if event.type == "TRACKPADPAN":
        # Match native popup smooth scrolling. Blender's GHOST conversion has
        # already applied the OS preference. is_direction_inverted is metadata
        # for *physical gesture* consumers; applying it here reverses natural
        # scrolling a second time. Do not infer direction from the platform.
        return getattr(event, "mouse_y", 0) - getattr(event, "mouse_prev_y", 0)
    return 0.0


def scroll_step(event):
    delta = scroll_delta(event)
    return (delta > 0) - (delta < 0)
