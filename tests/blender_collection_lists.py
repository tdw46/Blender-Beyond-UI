"""Real RNA list selection, identity, menus, editing and teardown."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout, UnsupportedControl
import lists_fixture as fixture


def run():
    checks = []
    try:
        fixture.register()
        ctx = bpy.context
        ui, commits = fixture.build(ctx)
        canvas = ui.canvas
        canvas.arrange(560)
        controls = [c for c in canvas.controls.values() if c.kind == "widget"]
        control = controls[0]
        widget = control.options["widget"]
        clip = (0, 0, 560, 900)

        def send(kind, x=30, y=40, value="PRESS", **kw):
            a, b, w, h = control.rect
            return canvas.event(
                NS(type=kind, value=value, **kw),
                a + x * w / widget.width,
                b + y * h / widget.height,
                clip,
                context=ctx,
                clipboard=ctx.window_manager,
            )

        send("LEFTMOUSE")
        assert ctx.scene.bui_list_active == 1 and commits == [(0, 1)]
        send("LEFTMOUSE", value="DOUBLE_CLICK")
        assert widget.text_edit is not None and canvas.widget_capture is control
        send("A", ctrl=True)
        send("A", unicode="Renamed Effect")
        send("RET")
        assert ctx.scene.bui_list_items[1].name == "Renamed Effect"
        assert commits[-1] == ("Layer 001", "Renamed Effect")
        checks.append(
            "First click selects the original index; active double-click rename commits through host"
        )
        send("RIGHTMOUSE")
        menu = canvas.context_menu
        assert menu is not None, canvas.menu_error
        row = next(
            i for i, r in enumerate(menu.page.rows) if r.label == "Copy Full Data Path"
        )
        menu.choose(row, ctx)
        assert (
            "bui_list_items" in ctx.window_manager.clipboard
            and ".name" in ctx.window_manager.clipboard
        )
        canvas.close_context()
        send("APP")
        assert canvas.context_menu is not None
        canvas.close_context()
        send("RIGHTMOUSE")
        menu = canvas.context_menu
        menu.choose(
            next(i for i, r in enumerate(menu.page.rows) if r.key == "LIST_RENAME"), ctx
        )
        canvas.close_context()
        assert canvas.widget_capture is control
        send("A", unicode="Cancelled")
        send("RIGHTMOUSE")
        assert (
            canvas.context_menu is None
            and ctx.scene.bui_list_items[1].name == "Renamed Effect"
        )
        checks.append(
            "Mouse/keyboard menus target exact row name; menu-started rename captures and right-click cancels"
        )
        widget.state.update(query="Effect", alpha=True, reverse=True)
        widget.reorder()
        widget.focus()
        widget.navigate("HOME")
        assert ctx.scene.bui_list_active == 1
        widget.navigate("END")
        assert ctx.scene.bui_list_active == 0
        assert widget.source.items[0].index == 0
        old = widget.source.items[1]
        binding = widget.source.name_binding(old)
        ctx.scene.bui_list_items.move(1, 2)
        assert not widget.source.valid_item(old) and not binding.valid(), (
            old,
            [(x.name, x.as_pointer()) for x in ctx.scene.bui_list_items][:4],
            widget.source.valid_item(old),
            binding.valid(),
        )
        widget.refresh()
        old = widget.source.items[2]
        binding = widget.source.name_binding(old)
        ctx.scene.bui_list_items.remove(2)
        assert not binding.valid()
        widget.refresh()
        checks.append(
            "Wildcard sorting preserves source indices; moved/deleted deferred row bindings fail closed"
        )
        previous = ctx.scene.bui_list_active
        widget.source.active.commit = lambda a, b: (_ for _ in ()).throw(
            RuntimeError("host rejected")
        )
        try:
            widget.source.select(widget.source.items[4])
        except RuntimeError:
            pass
        else:
            raise AssertionError("Missing commit rejection")
        assert ctx.scene.bui_list_active == previous
        for kind, expected in (
            ("NOT_A_LIST", UnsupportedControl),
            ("MESH_UL_vgroups", AttributeError),
        ):
            try:
                ui.template_list(
                    kind,
                    "invalid",
                    ctx.scene,
                    "bui_list_items",
                    ctx.scene,
                    "bui_list_active",
                )
            except expected:
                pass
            else:
                raise AssertionError("Invalid list silently admitted")
        assert len([c for c in canvas.controls.values() if c.kind == "widget"]) == 3
        checks.append(
            "Host commit failure rolls back; missing lists and incompatible callback data fail atomically"
        )
        try:
            Layout(context=ctx).template_list(
                "UI_UL_list",
                "unsafe",
                ctx.scene,
                "bui_list_items",
                ctx.scene,
                "bui_list_active",
            )
        except ValueError as error:
            assert "list_identity" in str(error)
        else:
            raise AssertionError("Unstable PropertyGroup slot pointers admitted")
        plain = Layout(context=ctx)
        object_list = plain.template_list(
            "UI_UL_list", "objects", ctx.scene, "objects", ctx.scene, "bui_list_active"
        )
        assert object_list.options["widget"].source.valid_item(
            object_list.options["widget"].source.items[0]
        )
        checks.append(
            "PropertyGroup rows require host keys; ID collections work with public RNA identity"
        )
        probe = bpy.data.objects.new("List Ownership Probe", None)
        ctx.scene.collection.objects.link(probe)
        source = object_list.options["widget"].source
        source.refresh()
        snapshot = next(item for item in source.items if item.name == probe.name)
        bpy.data.objects.remove(probe, do_unlink=True)
        replacement = bpy.data.objects.new("List Ownership Probe", None)
        ctx.scene.collection.objects.link(replacement)
        assert not source.valid_item(snapshot)
        bpy.data.objects.remove(replacement, do_unlink=True)
        checks.append(
            "Retained original RNA wrappers reject deleted ID rows, even after equal-count replacement"
        )
        canvas.cancel()
        assert not canvas.advance_animations() and canvas.widget_capture is None
        fixture.unregister()
        fixture.register(5)
        fixture.unregister()
        result = dict(
            passed=True,
            checks=checks,
            version=bpy.app.version_string,
            build=bpy.app.build_hash.decode(),
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("COLLECTION_LISTS", result, flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=0.5)
