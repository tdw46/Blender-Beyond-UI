"""Blender scroll events to a top-origin content offset (positive = later rows)."""

SCROLL_EVENTS = frozenset({"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"})


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
