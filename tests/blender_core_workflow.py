"""One mixed consumer canvas: properties, lists, menu and popup ownership."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui.editing import Text
import action_parity_fixture as actions
import lists_fixture as lists

checks = []
try:
    actions.register()
    lists.register(count=6)
    ctx = bpy.context
    ui = actions.build(ctx)
    ui.list_identity = lambda data, prop, item: item.uid
    ui.template_list(
        "UI_UL_list",
        "core",
        ctx.scene,
        "bui_list_items",
        ctx.scene,
        "bui_list_active",
        rows=4,
        maxrows=4,
    )
    canvas = ui.canvas
    clip = (0, 0, 560, 1000)

    def named(label):
        return next(c for c in canvas.controls.values() if c.label == label)

    def send(c, kind, value="PRESS", **extra):
        x, y, w, h = c.rect
        return canvas.event(
            NS(type=kind, value=value, **extra), x + w / 2, y + h / 2, clip, context=ctx
        )

    for width in (260, 400, 560):
        canvas.arrange(width)
        for c in canvas.visible_controls((0, 0, width, 1000)):
            x, y, w, h = c.rect
            assert x >= 0 and w >= 0 and x + w <= width + 0.01, (width, c.label, c.rect)
    checks.append(
        "Mixed properties/list canvas remains within narrow and wide logical host bounds"
    )
    toggle = named("Transparent")
    before = ctx.scene.render.film_transparent
    send(toggle, "LEFTMOUSE")
    send(toggle, "LEFTMOUSE", "RELEASE")
    assert ctx.scene.render.film_transparent != before
    field = named("Alert field")
    previous = ctx.scene.render.filepath
    send(field, "LEFTMOUSE")
    canvas.editor.insert("//discard-me/")
    send(field, "RIGHTMOUSE")
    assert ctx.scene.render.filepath == previous and canvas.context_menu is None
    send(field, "RIGHTMOUSE")
    assert canvas.context_menu.target.binding.context.name == "filepath"
    canvas.cancel()
    number = named("Normal field")
    send(number, "LEFTMOUSE", "DOUBLE_CLICK")
    canvas.editor.insert("50 + 25")
    send(number, "RET")
    assert ctx.scene.render.resolution_percentage == 75
    checks.append(
        "Boolean action, text right-cancel before context, and numeric expression editing coexist"
    )
    opener = named("Review Changes")
    send(opener, "LEFTMOUSE")
    assert canvas.overlay and canvas.overlay["widget"].canvas is not canvas
    before = ctx.scene.render.film_transparent
    send(toggle, "LEFTMOUSE")
    assert ctx.scene.render.film_transparent == before, (
        "Click-through changed parent field"
    )
    canvas.cancel()
    checks.append("Popup input does not click through to parent property")
    control = next(c for c in canvas.controls.values() if c.kind == "widget")
    widget = control.options["widget"]

    def list_event(kind, value="PRESS", **extra):
        a, b, w, h = control.rect
        return canvas.event(
            NS(type=kind, value=value, **extra),
            a + 30 * w / widget.width,
            b + 40 * h / widget.height,
            clip,
            context=ctx,
        )

    list_event("LEFTMOUSE")
    assert ctx.scene.bui_list_active == 1
    list_event("RIGHTMOUSE")
    assert canvas.context_menu is not None, canvas.menu_error
    target = canvas.context_menu.target
    assert target.binding.context.name == "name"
    canvas.cancel()
    checks.append(
        "List selection and exact-row property context work alongside ordinary fields"
    )
    canvas.animation.enabled = False
    send(opener, "LEFTMOUSE")
    assert canvas.overlay and not canvas.advance_animations(context=ctx)
    canvas.cancel()
    canvas.park()
    assert not canvas.advance_animations(context=ctx)
    checks.append(
        "Disabled motion leaves popup interaction available; teardown settles without polling"
    )
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=checks,
        visual_acceptance=False,
        scope="Shared Canvas consumer workflow; not actual N-panel/Properties host embedding or GPU visual qualification",
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc(), checks=checks)
finally:
    if hasattr(bpy.types.Scene, "bui_list_items"):
        lists.unregister()
    actions.unregister()
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
