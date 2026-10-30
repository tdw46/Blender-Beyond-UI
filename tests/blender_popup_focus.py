"""Real RNA, popup ownership and keyboard execution, isolated profile."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import popup_focus_fixture as fixture


def run():
    checks = []
    try:
        fixture.register()
        ctx = bpy.context
        from beyond_ui import Layout

        decorated = Layout(context=ctx)
        decorated.activate_init = True
        decorated.use_property_split = True
        decorated.prop(ctx.object, "location")
        numeric = [c for c in decorated.canvas.controls.values() if c.kind == "number"]
        assert len(numeric) == 3 and all(
            c.options.get("activate_init") for c in numeric
        )
        decorated.prop(ctx.scene.render, "filepath")
        assert next(
            c for c in decorated.canvas.controls.values() if c.kind == "text"
        ).options["activate_init"]
        checks.append(
            "Array components and property-split decorators preserve the author's initial activation flag"
        )
        ui, commits = fixture.build(ctx)
        canvas = ui.canvas
        canvas.arrange(560)
        clip = (0, 0, 560, 520)
        text = next(c for c in canvas.controls.values() if c.label == "Output Settings")
        number = next(
            c for c in canvas.controls.values() if c.label == "Resolution Settings"
        )

        def open(control=text):
            assert canvas.open_panel(control, clip, ctx), canvas.menu_error
            return canvas.overlay["widget"]

        def key(popup, kind, **kw):
            return popup.dispatch(
                NS(type=kind, value="PRESS", **kw),
                20,
                20,
                context=ctx,
                clipboard=ctx.window_manager,
            )

        popup = open()
        child = popup.canvas
        assert (
            child.active.label == "Output"
            and child.editor.text == ctx.scene.render.filepath
        )
        assert (child.editor.anchor, child.editor.cursor) == (0, len(child.editor.text))
        assert not fixture.calls and not commits
        key(popup, "A", unicode="//custom-output/")
        key(popup, "RET")
        assert ctx.scene.render.filepath == "//custom-output/" and len(commits) == 1
        assert not fixture.calls and child.edit is None
        key(popup, "RET", is_repeat=True)
        assert not fixture.calls
        key(popup, "RET")
        assert fixture.calls[-1][0] == "text" and canvas.overlay is None
        checks.append(
            "Initial selection edits exact RNA; Return commits before default action; repeats do not execute"
        )

        popup = open(number)
        key(popup, "A", unicode="invalid")
        key(popup, "RET")
        assert popup.canvas.editor is not None and len(fixture.calls) == 1
        popup.canvas.editor.text = "50 + 25"
        key(popup, "RET")
        assert ctx.scene.render.resolution_percentage == 75
        key(popup, "NUMPAD_ENTER")
        assert fixture.calls[-1][0] == "number" and canvas.overlay is None
        checks.append(
            "Numeric expressions commit; invalid text keeps edit; keypad Return invokes default"
        )

        popup = open()
        key(popup, "ESC")
        nested = next(
            c for c in popup.canvas.controls.values() if c.label == "Resolution"
        )
        assert popup.canvas.open_panel(nested, popup.clip, ctx)
        inner = popup.canvas.overlay["widget"]
        key(inner, "RET")
        count = len(fixture.calls)
        key(inner, "RET")
        assert (
            len(fixture.calls) == count + 1
            and popup.canvas.overlay is None
            and canvas.overlay is not None
        )
        assert fixture.calls[-1][0] == "number"
        canvas.cancel()
        popup = open()
        key(popup, "RIGHTMOUSE")
        field = next(c for c in popup.canvas.controls.values() if c.label == "Output")
        a, b, w, h = field.rect
        popup.dispatch(
            NS(type="RIGHTMOUSE", value="PRESS"), a + w / 2, b + h / 2, context=ctx
        )
        assert popup.canvas.context_menu is not None
        row = next(
            i
            for i, r in enumerate(popup.canvas.context_menu.page.rows)
            if r.label == "Copy Full Data Path"
        )
        popup.canvas.context_menu.choose(row, ctx)
        assert "render.filepath" in ctx.window_manager.clipboard
        popup.canvas.close_context()
        checks.append(
            "Nested default stays in child popup; edit cancellation preserves exact-property context menus"
        )

        count = len(fixture.calls)
        fixture.allowed = False
        key(popup, "RET")
        assert canvas.overlay is None and len(fixture.calls) == count
        fixture.allowed = True
        popup = open()
        key(popup, "ESC")
        bpy.utils.unregister_class(fixture.BUI_PT_focus_text)
        key(popup, "RET")
        assert canvas.overlay is None and len(fixture.calls) == count
        assert not popup.canvas._moving
        checks.append(
            "Stale poll and removed registration reject default actions and release popup state"
        )
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        fixture.allowed = True
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("POPUP_FOCUS", result, flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )


bpy.app.timers.register(run, first_interval=1)
