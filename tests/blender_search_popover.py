"""Compact search fields: lazy candidates, overlay ownership and transactions."""

import bpy, json, os, sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import Canvas, Layout

ctx = bpy.context
bpy.types.Scene.search_popover = bpy.props.StringProperty(default="Initial")
try:
    commits = []
    canvas = Canvas(menu_commit=commits.append)
    ui = Layout(canvas, ctx, commit=lambda a, b: commits.append((a, b)))
    field = ui.prop_search(
        ctx.scene,
        "search_popover",
        bpy.data,
        "objects",
        results_are_suggestions=True,
        text="Target",
    )
    template = ui.template_search(
        ctx.scene, "camera", bpy.data, "objects", text="Camera"
    )
    for _ in range(12):
        ui.label(text="")
    canvas.arrange(560)
    clip = (0, 0, 560, 520)
    model = field.options["search_field"]
    assert field.kind == template.kind == "search" and field.rect[3] == 32
    assert model.widget.items == () and model.label() == "Initial"
    original = model.collection
    model.collection = lambda: (_ for _ in ()).throw(
        AssertionError("Scan from closed label")
    )
    for _ in range(100):
        assert model.label() == "Initial"
    model.collection = original

    def event(kind, x=20, y=20, **kwargs):
        return canvas.event(
            NS(type=kind, value="PRESS", **kwargs), x, y, clip, context=ctx
        )

    def open_field(control=field):
        a, b, w, h = control.rect
        assert event("LEFTMOUSE", a + 10, b + 10)
        assert canvas.overlay and canvas.overlay["owner"] is control
        return canvas.overlay["widget"]

    widget = open_field()
    assert widget.glass_blur == 0.7 and widget.focused and not widget.capturing
    a, b, w, h = canvas.overlay["rect"]
    assert event("RIGHTMOUSE", a + 40 * w / widget.width, b + 160 * h / widget.height)
    assert canvas.context_menu.target.part[0] == "row"
    canvas.close_context()
    event("Z", unicode="z")
    assert widget.query == "z" and widget.capturing
    event("RET")
    assert (
        ctx.scene.search_popover == "z"
        and canvas.overlay is None
        and commits == [("Initial", "z")]
    )
    widget = open_field()
    event("X", unicode="x")
    event("ESC")
    assert canvas.overlay is None and ctx.scene.search_popover == "z"
    widget = open_field()
    event("X", unicode="x")
    event("RIGHTMOUSE")
    assert (
        canvas.overlay is None
        and canvas.context_menu is None
        and ctx.scene.search_popover == "z"
    )
    widget = open_field()
    event("X", unicode="x")
    event("LEFTMOUSE", -10, -10)
    assert canvas.overlay is None and ctx.scene.search_popover == "z"

    def reject(a, b):
        raise RuntimeError("Host rejected")

    model.binding.commit = reject
    widget = open_field()
    event("X", unicode="x")
    event("RET")
    assert (
        canvas.overlay is not None
        and widget.text_edit.text == "x"
        and ctx.scene.search_popover == "z"
    )
    assert canvas.menu_error == "Host rejected"
    model.binding.commit = lambda a, b: None
    canvas.cancel()
    widget = open_field()
    ctx.scene.search_popover = "External"
    widget.select(widget.items[0][0])
    assert canvas.overlay is not None and ctx.scene.search_popover == "External"
    canvas.cancel()
    field.motion.settings.enabled = False
    widget = open_field()
    assert widget.motion.strength == 0
    canvas.cancel()
    field.motion.settings.enabled = True
    widget = open_field()
    model.refresh()
    assert canvas.overlay is None
    canvas.cancel()
    assert canvas.open_context(field, 20, 20, clip, context=ctx)
    assert canvas.context_menu.target.binding.context.name == "search_popover"
    canvas.cancel()
    legacy = Layout(context=ctx)
    legacy.search_popovers = False
    assert legacy.row().search_popovers is False
    assert (
        legacy.prop_search(ctx.scene, "search_popover", bpy.data, "objects").kind
        == "widget"
    )
    checks = [
        "Compact prop_search/template_search geometry and lazy closed-field candidates",
        "Immediate typing, successful commit closes owned popover, failed commit preserves edit",
        "Escape/right-click/outside-click cancellation and stale owner value rejection",
        "Exact property/row context, per-control animation disable, refresh teardown and full-card opt-out",
    ]
finally:
    del bpy.types.Scene.search_popover
result = dict(passed=True, version=bpy.app.version_string, checks=checks)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("SEARCH_POPOVER", result)
