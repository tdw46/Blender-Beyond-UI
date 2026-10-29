"""Disposable RNA collection search and expanded decorator behavior."""

import bpy, os, sys, json
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import Canvas, Layout as _Layout, PointerItems, UnsupportedControl
from beyond_ui.editing import Text
from beyond_ui.widgets.context import target


def Layout(*args, **kwargs):
    ui = _Layout(*args, **kwargs)
    ui.search_popovers = False
    return ui


class SearchItem(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty()


bpy.utils.register_class(SearchItem)
bpy.types.Scene.search_rows = bpy.props.CollectionProperty(type=SearchItem)
bpy.types.Scene.search_value = bpy.props.StringProperty()
checks = []
try:
    ctx = bpy.context
    scene = ctx.scene
    for i in range(500):
        row = scene.search_rows.add()
        row.name = f"Bone {i:03}"
        row.label = f"Display {i:03}"
    commits = []
    ui = Layout(
        Canvas(menu_commit=commits.append),
        ctx,
        commit=lambda a, b: commits.append((a, b)),
    )
    control = ui.prop_search(scene, "search_value", scene, "search_rows", text="Bones")
    model = control.options["search_field"]
    widget = model.widget
    key = scene.search_rows[30].as_pointer()
    assert (
        widget.select(key)
        and scene.search_value == "Bone 030"
        and commits == [("", "Bone 030")]
    )
    assert widget.selected() == key
    scene.search_rows[30].name = "Renamed Bone"
    assert widget.select(key) is False and scene.search_value == "Bone 030"
    widget.refresh()
    assert widget.select(key) and scene.search_value == "Renamed Bone"
    assert widget.selected() == key
    checks.append(
        "String collection selection, renamed-item identity, host commit and explicit refresh"
    )

    def reject(a, b):
        raise RuntimeError("Rejected commit")

    model.binding.commit = reject
    assert widget.select(scene.search_rows[20].as_pointer()) is False
    assert (
        scene.search_value == "Renamed Bone"
        and ui.canvas.menu_error == "Rejected commit"
    )
    model.binding.commit = lambda a, b: None
    scene.search_value = "External value"
    assert widget.select(key) is False and scene.search_value == "External value"
    widget.refresh()
    removed = scene.search_rows[10].as_pointer()
    scene.search_rows.remove(10)
    assert widget.select(removed) is False
    copy_context = NS(window_manager=NS(clipboard="Original"))
    assert model.copy_name(removed, copy_context) is False
    assert copy_context.window_manager.clipboard == "Original"
    checks.append(
        "Failed commit rollback, concurrent property change and removed search item rejected"
    )
    widget.refresh()
    ui.canvas.arrange(560)
    hit = target(widget, control.key, 40, 160)
    assert hit.binding is None and callable(hit.payload)
    rows = hit.payload(hit, ctx)
    assert [r.key for r in rows] == ["SELECT_SEARCH", "COPY_NAME"]
    rows[1].action(hit, copy_context)
    assert copy_context.window_manager.clipboard == "Bone 000"
    assert ui.canvas.open_context(control, 40, 160, (0, 0, 560, 520), context=ctx)
    ui.canvas.widget_capture = control
    widget.refresh()
    assert ui.canvas.context_menu is None and ui.canvas.widget_capture is None
    # No collection iteration in repeated draw-facing reads.
    original = model.collection
    counts = [0]

    class NoScan:
        def __iter__(self):
            counts[0] += 1
            raise AssertionError("Collection scan during visible read")

    model.collection = lambda: NoScan()
    for _ in range(100):
        widget.selected()
        assert widget.valid(scene.search_rows[0].as_pointer())
    assert counts == [0]
    model.collection = original
    checks.append(
        "Exact candidate right-click and zero collection scans in repeated paint-facing reads"
    )
    custom = ui.prop_search(
        scene,
        "search_value",
        scene,
        "search_rows",
        item_search_property="label",
        results_are_suggestions=True,
    )
    w = custom.options["widget"]
    assert (
        w.select(scene.search_rows[2].as_pointer())
        and scene.search_value == "Display 002"
    )
    w.text_edit = Text("Free typed value")
    w.query = "Free typed value"
    w._filter()
    assert w._accept() and scene.search_value == "Free typed value"
    w.text_edit = Text("Canceled")
    w.query = "Canceled"
    w._filter()
    w.capturing = True
    w.event(NS(type="ESC", value="PRESS"), 0, 0)
    assert scene.search_value == "Free typed value"
    checks.append(
        "Custom item string property, free suggestions, Escape cancellation and no invented data creation"
    )
    pointer = ui.prop_search(scene, "camera", bpy.data, "objects")
    pw = pointer.options["widget"]
    assert all(
        bpy.data.objects[label].type == "CAMERA" for key, label, icon in pw.items
    )
    assert pw.select(ctx.object.as_pointer()) is False
    camera = next(v for v in bpy.data.objects if v.type == "CAMERA")
    assert pw.select(camera.as_pointer()) and scene.camera == camera
    allowed = [camera]
    restricted = Layout(
        context=ctx, pointer_sources=lambda o, p: PointerItems(lambda: allowed)
    )
    rw = restricted.prop_search(scene, "camera", bpy.data, "objects").options["widget"]
    assert [key for key, label, icon in rw.items] == [camera.as_pointer()]
    allowed.clear()
    assert rw.select(camera.as_pointer()) is False
    checks.append(
        "ID search intersects collection with host candidate policy and retains camera type/poll enforcement"
    )
    obj = ctx.object
    obj.animation_data_clear()
    deco_ui = Layout(Canvas(menu_commit=lambda action: None), ctx)
    components = deco_ui.prop_decorator(obj, "location")
    assert len(components) == 3 and [c.binding.context.index for c in components] == [
        0,
        1,
        2,
    ]
    color_decorator = deco_ui.prop_decorator(obj, "color")
    assert color_decorator.binding.context.index is None
    assert not isinstance(color_decorator, tuple)
    try:
        deco_ui.prop_decorator(obj, "location", index=-2)
    except ValueError:
        pass
    else:
        raise AssertionError("Undocumented negative component semantics accepted")
    deco_ui.canvas.arrange(560)
    assert all(c.rect[2] == 32 for c in components)
    assert len(set(c.rect[1] for c in components)) == 3
    components[2].options["decorator"].click(deco_ui.canvas, components[2], ctx)
    assert [c.options["decorator"].state() for c in components] == [
        "EMPTY",
        "EMPTY",
        "KEYED",
    ]
    color_decorator.options["decorator"].click(deco_ui.canvas, color_decorator, ctx)
    assert color_decorator.options["decorator"].state() == "KEYED"
    checks.append(
        "Standalone vector decorator expansion, exact component writes and aggregate nonexpanded color decorators"
    )
    del bpy.types.Scene.search_rows
    assert widget.select(key) is False
    checks.append(
        "Removed collection RNA rejects stale selection before reading old items"
    )
finally:
    if hasattr(bpy.types.Scene, "search_rows"):
        del bpy.types.Scene.search_rows
    del bpy.types.Scene.search_value
    bpy.utils.unregister_class(SearchItem)
result = dict(passed=True, version=bpy.app.version_string, checks=checks)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("COLLECTION_SEARCH", result)
