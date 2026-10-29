"""Enum field RNA behavior in disposable Blender profiles."""

import bpy, os, sys, json
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, Layout

rows = [("A", "Alpha", "Alpha tooltip", 1), ("B", "Beta", "Beta tooltip", 2)]
calls = []


def dynamic(owner, context):
    calls.append(True)
    return rows


bpy.types.Scene.enum_choice = bpy.props.EnumProperty(items=rows, default="A")
bpy.types.Scene.enum_flags = bpy.props.EnumProperty(
    items=rows, options={"ENUM_FLAG"}, default={"A"}
)
bpy.types.Scene.enum_dynamic = bpy.props.EnumProperty(items=dynamic)
bpy.types.Scene.enum_long = bpy.props.EnumProperty(
    items=[(f"I{i}", f"Choice {i:03}", "") for i in range(200)]
)
try:
    ctx = bpy.context
    ctx.scene.enum_dynamic = "A"
    commits = []
    canvas = Canvas(menu_commit=lambda action: None)
    fail = [False]

    def commit(a, b):
        if fail[0]:
            raise RuntimeError("reject commit")
        commits.append((a, b))

    ui = Layout(canvas, context=ctx, commit=commit)
    scalar = ui.prop(ctx.scene, "enum_choice")
    flags = ui.prop_menu_enum(ctx.scene, "enum_flags")
    dyn = ui.prop(ctx.scene, "enum_dynamic")
    long = ui.prop(ctx.scene, "enum_long")
    expanded = ui.prop_enum(ctx.scene, "enum_choice", "B")
    canvas.arrange(360)
    clip = (0, 0, 360, 500)

    def open_menu(c):
        canvas.cancel()
        x, y, w, h = c.rect
        assert canvas.event(
            NS(type="LEFTMOUSE", value="PRESS"), x + 5, y + 5, clip, context=ctx
        )
        assert canvas.context_menu is not None, canvas.menu_error
        return canvas.context_menu

    menu = open_menu(scalar)
    assert menu.page.checked == (True, False)
    menu.choose(1, ctx)
    assert ctx.scene.enum_choice == "B" and commits[-1] == ("A", "B")
    fail[0] = True
    ctx.scene.enum_choice = "A"
    expanded.action()
    assert ctx.scene.enum_choice == "A" and canvas.menu_error == "reject commit"
    menu = open_menu(scalar)
    menu.choose(1, ctx)
    assert ctx.scene.enum_choice == "A" and menu.error == "reject commit"
    fail[0] = False
    assert expanded.binding.context.enum_value == "B"
    menu = open_menu(flags)
    menu.choose(1, ctx)
    assert ctx.scene.enum_flags == {"A", "B"}
    assert commits[-1] == ({"A"}, {"A", "B"})
    menu = open_menu(flags)
    menu.choose(0, ctx)
    assert ctx.scene.enum_flags == {"B"}
    menu = open_menu(dyn)
    assert len(menu.page.rows) == 2 and len(calls) > 0
    rows[:] = [("A", "Alpha", "Alpha tooltip", 1)]
    menu.choose(1, ctx)
    assert menu.error and "choice changed" in menu.error
    assert ctx.scene.enum_dynamic == "A"
    menu = open_menu(dyn)
    assert len(menu.page.rows) == 1
    menu = open_menu(long)
    menu.event(NS(type="END", value="PRESS"), 20, 30, ctx)
    assert menu.page.highlight == 199
    menu.event(NS(type="RET", value="PRESS"), 20, 30, ctx)
    assert ctx.scene.enum_long == "I199"
    menu = open_menu(scalar)
    ctx.scene.enum_choice = "B"
    menu.choose(0, ctx)
    assert menu.closed and ctx.scene.enum_choice == "B"
    canvas.cancel()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Ordinary enum clicks and explicit enum menus use shared glass Menu",
            "Scalar and expanded enum commit failures restore authoritative RNA values",
            "Flag menu toggles preserve unrelated flags and commit real sets",
            "Dynamic callbacks refresh on open and removed choices are rejected on selection",
            "Long enum menus reach item 199 with keyboard scrolling; no truncation",
            "Concurrent property writes invalidate old menus; exact expanded enum context retained",
        ],
    )
finally:
    for name in ("enum_choice", "enum_flags", "enum_dynamic", "enum_long"):
        delattr(bpy.types.Scene, name)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(result)
