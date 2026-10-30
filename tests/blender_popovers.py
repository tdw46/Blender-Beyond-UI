"""Registered-panel runtime interactions with a disposable Blender profile."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout
import popovers_fixture as fixture


def run():
    checks = []
    try:
        fixture.register()
        ctx = bpy.context
        ui, commits = fixture.build(ctx)
        canvas = ui.canvas
        canvas.arrange(560)
        clip = (0, 0, 560, 600)
        opener = next(
            c for c in canvas.controls.values() if c.label == "Render Controls"
        )
        assert not ui.is_popover
        assert canvas.open_panel(opener, clip, ctx), canvas.menu_error
        widget = canvas.overlay["widget"]
        child = widget.canvas
        assert widget.width == 320
        assert child.theme.font_size == canvas.theme.font_size

        def click(label, kind="LEFTMOUSE", event=None):
            c = next(c for c in child.controls.values() if c.label == label)
            a, b, w, h = c.rect
            return widget.dispatch(
                event or NS(type=kind, value="PRESS"),
                a + w / 2,
                b + h / 2 - widget.scroll,
                context=ctx,
                clipboard=ctx.window_manager,
            )

        before = ctx.scene.render.film_transparent
        click("Transparent")
        assert ctx.scene.render.film_transparent != before and len(commits) == 1
        click("Scale", "RIGHTMOUSE")
        assert child.context_menu is not None
        assert canvas.active_menu() is child.context_menu
        menu = child.context_menu
        index = next(
            i for i, r in enumerate(menu.page.rows) if r.label == "Copy Full Data Path"
        )
        menu.choose(index, ctx)
        assert "render.resolution_percentage" in ctx.window_manager.clipboard
        child.close_context()
        click("Settings Menu")
        assert child.context_menu is not None
        menu = child.context_menu
        index = next(
            i for i, r in enumerate(menu.page.rows) if r.label == "Transparent"
        )
        menu.choose(index, ctx)
        child.close_context()
        checks.append(
            "Shared scalar and registered-menu edits commit through the host; right-click retains exact property ownership"
        )
        click("Nested Controls")
        assert child.overlay is not None
        nested = child.overlay["widget"]
        assert nested.width <= widget.width
        nested.dispatch(NS(type="ESC", value="PRESS"), 20, 20, context=ctx)
        assert child.overlay is None and canvas.overlay is not None
        before = fixture.draws
        widget.dimensions(11, 240, 120)
        assert widget.width == 240 and widget.height == 120
        widget.dispatch(NS(type="WHEELDOWNMOUSE", value="PRESS"), 20, 100, context=ctx)
        assert widget.scroll > 0 and fixture.draws == before
        canvas.cancel()
        assert (
            not child._moving and child.context_menu is None and child.overlay is None
        )
        checks.append(
            "Nested dismissal preserves the parent; narrow/short bounds scroll without rebuilding draw callbacks; teardown clears children"
        )
        attached = next(c for c in canvas.controls.values() if c.label == "Display")
        assert canvas.open_panel(attached, clip, ctx), canvas.menu_error
        widget = canvas.overlay["widget"]
        child = widget.canvas
        click("Wire")
        assert ctx.object.display_type == "WIRE"
        canvas.cancel()
        color = next(c for c in canvas.controls.values() if c.label == "Color")
        assert canvas.open_panel(color, clip, ctx), canvas.menu_error
        assert any(
            c.kind == "widget"
            for c in canvas.overlay["widget"].canvas.controls.values()
        )
        canvas.cancel()
        checks.append(
            "Enum and color property popovers receive exact button_pointer/button_prop context"
        )
        group = Layout(context=ctx)
        group.popover_group("VIEW_3D", "UI", "", "BUI Popover Fixture")
        assert [
            c.label
            for c in group.canvas.controls.values()
            if c.options.get("panel_model")
        ] == ["Render Controls", "Nested Controls"]
        assert canvas.open_panel(opener, clip, ctx)
        fixture.allowed = False
        widget = canvas.overlay["widget"]
        widget.dispatch(NS(type="LEFTMOUSE", value="PRESS"), 20, 20, context=ctx)
        assert canvas.overlay is None
        fixture.allowed = True
        assert canvas.open_panel(opener, clip, ctx)
        widget = canvas.overlay["widget"]
        assert not widget.dispatch(
            NS(type="RIGHTMOUSE", value="PRESS"), -10, -10, context=ctx
        )
        assert canvas.overlay is None
        bad = Layout(context=ctx)
        bad.popover("BUI_PT_bad")
        bad.canvas.arrange(560)
        assert not bad.canvas.open_panel(
            next(iter(bad.canvas.controls.values())), clip, ctx
        )
        assert bad.canvas.overlay is None
        failed = Layout(context=ctx)
        failed.popover("BUI_PT_failed")
        failed.canvas.arrange(320)
        assert not failed.canvas.open_panel(
            next(iter(failed.canvas.controls.values())), clip, ctx
        )
        assert (
            failed.canvas.overlay is None
            and "Fixture callback failure" in failed.canvas.menu_error
        )
        from beyond_ui import UnsupportedControl

        original = tuple(canvas.controls)
        original_children = tuple(canvas.children)
        try:
            ui.popover("BUI_PT_bad_header")
        except UnsupportedControl:
            pass
        else:
            raise AssertionError("Unsupported header was silently admitted")
        assert (
            tuple(canvas.controls) == original
            and tuple(canvas.children) == original_children
        )
        fixture.allowed = False
        opener.options["panel_model"].refresh_poll(ctx)
        assert not opener.enabled
        fixture.allowed = True
        a, b, w, h = opener.rect
        canvas.event(
            NS(type="MOUSEMOVE", value="NOTHING"),
            a + w / 2,
            b + h / 2,
            clip,
            context=ctx,
        )
        assert opener.enabled
        canvas.open_panel(opener, clip, ctx)
        action = next(
            c
            for c in canvas.overlay["widget"].canvas.controls.values()
            if c.label == "Run Action"
        )
        fixture.allowed = False
        try:
            action.action()
        except ReferenceError:
            pass
        else:
            raise AssertionError("Stale deferred panel action ran")
        fixture.allowed = True
        canvas.cancel()
        try:
            action.action()
        except ReferenceError:
            pass
        else:
            raise AssertionError("Dismissed popup action remained active")
        from beyond_ui.context_dispatch import ShortcutRegistry

        registry = ShortcutRegistry("popover-runtime")
        registry.register()
        canvas.shortcut_registry = registry
        try:
            assert canvas.open_panel(opener, clip, ctx)
            assert registry.commands
            tokens = list(registry.commands)
            canvas.cancel()
            assert not registry.commands
            assert canvas.open_panel(opener, clip, ctx)
            assert registry.commands and not set(registry.commands).intersection(tokens)
            canvas.cancel()
            assert not registry.commands
        finally:
            registry.close()
            canvas.shortcut_registry = None
        checks.append(
            "Group filtering/order, poll reactivation, guarded deferred actions, outside right-click and atomic body/header rejection pass"
        )
        canvas.open_panel(opener, clip, ctx)
        bpy.utils.unregister_class(fixture.BUI_PT_popover)
        canvas.overlay["widget"].dispatch(
            NS(type="LEFTMOUSE", value="PRESS"), 20, 20, context=ctx
        )
        assert canvas.overlay is None
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("POPOVER_RUNTIME", result, flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.2
    )


bpy.app.timers.register(run, first_interval=1)
