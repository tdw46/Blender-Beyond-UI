"""Scalar menu transactions and real registered custom-popup dispatch."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, ShortcutRegistry
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target
from beyond_ui.context_fields import property_row
from beyond_ui.context_shortcuts import Action


def event(kind, **kw):
    return NS(type=kind, value="PRESS", **kw)


def run():
    checks = []
    ctx = bpy.context
    area = next(a for a in ctx.screen.areas if a.type == "VIEW_3D")
    with ctx.temp_override(area=area):
        obj = ctx.active_object
        commits = []
        target = Target("fields", commit=commits.append)

        def menu(name, index=-1, target=target):
            return Menu(
                target,
                (property_row(obj, name, index=index),),
                (10, 10),
                (0, 0, 640, 560),
                context=ctx,
            )

        m = menu("location", 1)
        m.choose(0, ctx)
        m.event(event("TEXTINPUT", unicode="2+3"), 20, 20, ctx)
        assert obj.location.y == 0
        m.event(event("RET"), 20, 20, ctx)
        assert obj.location.y == 5 and commits == ["PROPERTY"]
        m.choose(0, ctx)
        m.event(event("TEXTINPUT", unicode="9"), 20, 20, ctx)
        m.event(event("RIGHTMOUSE"), 20, 20, ctx)
        assert not m.closed and m.editor is None and obj.location.y == 5
        m.choose(0, ctx)
        m.event(event("TEXTINPUT", unicode="invalid"), 20, 20, ctx)
        m.event(event("RET"), 20, 20, ctx)
        assert m.editor is not None and m.error and obj.location.y == 5
        m.event(event("ESC"), 20, 20, ctx)
        m.choose(0, ctx)
        obj.location.y = 7
        m.event(event("RET"), 20, 20, ctx)
        assert m.error and obj.location.y == 7
        m.close()
        checks.append(
            "inline numeric arithmetic, deferred commit, cancellation, invalid text and concurrent-value rejection"
        )

        def reject(key):
            raise RuntimeError("reject transaction")

        m = menu("location", 1, Target("reject", commit=reject))
        m.choose(0, ctx)
        m.event(event("TEXTINPUT", unicode="8"), 20, 20, ctx)
        m.event(event("RET"), 20, 20, ctx)
        assert obj.location.y == 7 and m.error == "reject transaction"
        m.close()
        m = menu("name")
        m.choose(0, ctx)
        m.event(event("TEXTINPUT", unicode="Menu owner"), 20, 20, ctx)
        m.event(event("RET"), 20, 20, ctx)
        assert obj.name == "Menu owner"
        m.close()
        m = menu("location")
        m.choose(0, ctx)
        assert len(m.page.rows) == 4 and all(r.field for r in m.page.rows[1:])
        m.close()
        checks.append(
            "string fields, numeric array components and rollback through the host commit boundary"
        )
        registry = ShortcutRegistry("beyond-ui-completion-fixture")
        registry.register()
        try:
            canvas = Canvas(shortcut_registry=registry, shortcut_namespace="test")
            c = canvas.enum(
                "rotation",
                "Rotation",
                rna_binding(lambda: obj, "rotation_mode"),
                items=(("XYZ", "XYZ"), ("ZYX", "ZYX")),
                shortcut_key="rotation",
            )
            canvas.arrange(600)
            canvas.bind_shortcuts(ctx, (0, 0, 640, 560))
            assert registry.available("test:rotation", ctx)
            assert canvas.open_context(c, 20, 20, (0, 0, 640, 560), context=ctx), (
                canvas.menu_error
            )
            row = canvas.context_menu.page.rows[0]
            assert row.label == "Shortcut to Open Menu"
            command = "test:rotation"
            action = Action(registry.idname, {"command": command}, ctx, keymap="Window")
            assert action.capture(
                None, ctx, event("F19", ctrl=True, alt=True, shift=True)
            )
            canvas.close_context()
            category, name = registry.idname.split(".")
            op = getattr(getattr(bpy.ops, category), name)
            assert op("EXEC_DEFAULT", command=command) == {"FINISHED"}
            assert canvas.context_menu is not None
            canvas.context_menu.choose(1, ctx)
            assert obj.rotation_mode == "ZYX"
            canvas.close_context()
            canvas.visible = False
            assert op("EXEC_DEFAULT", command=command) == {"CANCELLED"}
            canvas.visible = True
            canvas.controls.clear()
            assert op("EXEC_DEFAULT", command=command) == {"CANCELLED"}
            action = Action(registry.idname, {"command": command}, ctx, keymap="Window")
            action.remove(None, ctx)
            checks.append(
                "real keymap and registered host dispatcher reopen custom enum, commit selection, revoke hidden/replaced controls"
            )
            config = ctx.window_manager.keyconfigs.new("Beyond custom scope fixture")
            try:
                extra = config.keymaps.new(
                    "Host custom conflict map", space_type="EMPTY"
                )
                extra.keymap_items.new(
                    "wm.context_toggle", "F17", "PRESS", ctrl=True, alt=True, shift=True
                )
                conflict = Action(
                    registry.idname,
                    {"command": "custom-invocation"},
                    ctx,
                    keymap="Window",
                    conflict_keymaps=lambda context, selected: (extra,),
                )
                try:
                    conflict.capture(
                        None, ctx, event("F17", ctrl=True, alt=True, shift=True)
                    )
                    raise AssertionError("Host conflict was ignored")
                except ValueError as error:
                    assert "already used" in str(error)
            finally:
                ctx.window_manager.keyconfigs.remove(config)
            checks.append(
                "host editor/modal conflict maps reject colliding shortcuts without changing existing assignments"
            )
            called = []
            registry.bind(
                "custom-invocation",
                ctx,
                lambda context, event: called.append(context.area.as_pointer()),
            )
            assert op("EXEC_DEFAULT", command="custom-invocation") == {"FINISHED"}
            assert called == [area.as_pointer()]
            checks.append(
                "host callbacks support custom invocation routing without dropping their context"
            )
        finally:
            registry.close()
        assert not registry.commands and registry.operator_class is None
        checks.append(
            "dispatcher teardown clears callbacks and unregisters its owned operator"
        )
    result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print("BEYOND_UI_RESULT=" + json.dumps(result))


def timer():
    try:
        run()
    except Exception:
        traceback.print_exc()
    finally:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
