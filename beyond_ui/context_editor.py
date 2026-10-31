"""Route exact visible channels to an existing native Graph/Drivers Editor."""

from .context_menu import Entry
from .decorator import channel_collections


def curves(source, drivers):
    owner = source.owner()
    collections, driven = channel_collections(owner.id_data)
    path = source.property_path(owner)
    return tuple(
        f
        for group in ((driven or (),) if drivers else collections)
        for f in group
        if f.data_path == path
        and (source.index is None or f.array_index == source.index)
    )


def route(source, context, drivers):
    matches = curves(source, drivers)
    if not matches:
        return None
    wanted = {f.as_pointer() for f in matches}
    window = getattr(context, "window", None)
    if window is None:
        return None
    # Stay in this window and scene; don't focus or create another window.
    for area in window.screen.areas:
        if area.type != "GRAPH_EDITOR":
            continue
        space = area.spaces.active
        if space.mode != ("DRIVERS" if drivers else "FCURVES"):
            continue
        region = next((r for r in area.regions if r.type == "WINDOW"), None)
        if region is None:
            continue
        with context.temp_override(window=window, area=area, region=region):
            import bpy

            visible = tuple(bpy.context.visible_fcurves or ())
            if (
                wanted.issubset({f.as_pointer() for f in visible})
                and bpy.ops.graph.view_selected.poll()
            ):
                return window, area, region, visible, matches
    return None


def navigate(source, target, context, drivers):
    if not target.valid() or not source.valid():
        raise ReferenceError("Editor target changed")
    resolved = route(source, context, drivers)
    if resolved is None:
        raise RuntimeError("Open a Graph/Drivers Editor showing this owner and channel")
    import bpy

    window, area, region, visible, matches = resolved
    wanted = {f.as_pointer() for f in matches}
    states = [
        (
            f,
            f.select,
            [
                (p, p.select_control_point, p.select_left_handle, p.select_right_handle)
                for p in f.keyframe_points
            ],
        )
        for f in visible
    ]
    try:
        for f in visible:
            selected = f.as_pointer() in wanted
            f.select = selected
            for point in f.keyframe_points:
                point.select_control_point = point.select_left_handle = (
                    point.select_right_handle
                ) = selected
        with context.temp_override(window=window, area=area, region=region):
            if "FINISHED" not in bpy.ops.graph.view_selected():
                raise RuntimeError("Graph Editor could not frame the selected channels")
        area.tag_redraw()
    except Exception:
        for f, selected, points in states:
            f.select = selected
            for point, co, left, right in points:
                (
                    point.select_control_point,
                    point.select_left_handle,
                    point.select_right_handle,
                ) = co, left, right
        raise


def entries(source):
    rows = []
    for driven, key, label in (
        (False, "VIEW_CURVE", "View in Graph Editor"),
        (True, "VIEW_DRIVER", "View Driver in Drivers Editor"),
    ):
        choices = [(source, key, label)]
        if source.index is not None:
            choices.append(
                (
                    source.component(None),
                    key + "_ALL",
                    "View All Drivers in Drivers Editor"
                    if driven
                    else "View All in Graph Editor",
                )
            )
        for binding, action, text in choices:
            rows.append(
                Entry(
                    action,
                    text,
                    lambda t, c, b=binding, d=driven: navigate(b, t, c, d),
                    lambda t, c, b=binding, d=driven: t.valid()
                    and b.valid()
                    and route(b, c, d) is not None,
                    tip="Requires an existing editor in this window with the exact channels visible. Does not change editor filters or create a window.",
                )
            )
    return rows
