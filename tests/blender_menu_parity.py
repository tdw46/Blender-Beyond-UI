"""Remaining menu parity cases in a disposable Blender profile."""

import bpy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout
from beyond_ui.context_menu import Menu, Target, Shortcut, Entry
from beyond_ui.context_shortcuts import Action, property_entry
from beyond_ui.bindings import rna_binding
from beyond_ui.hosts import menu_native


def event(kind, value="PRESS", **kwargs):
    return NS(type=kind, value=value, **kwargs)


def run():
    checks = []
    ctx = bpy.context
    area = next(a for a in ctx.screen.areas if a.type == "VIEW_3D")
    with ctx.temp_override(area=area):
        obj = ctx.active_object
        target = Target("fixture")
        props = {"data_path": "object.show_name"}

        def menu_for(action):
            return Menu(
                target, (action.entry(ctx),), (10, 10), (0, 0, 640, 700), context=ctx
            )

        action = Action("wm.context_toggle", props, ctx)
        m = menu_for(action)
        m.choose(0, ctx)
        assert m.page.rows[2].key == "MOUSE_CAPTURE"
        m.start_capture(m.page.rows[2], ctx, replace_mode=True)
        m.event(
            event("MIDDLEMOUSE", shift=True, ctrl=True, alt=True, oskey=True),
            400,
            400,
            ctx,
        )
        assert m.closed and m.error is None, m.error
        action = Action("wm.context_toggle", props, ctx)
        _, item = action.current(ctx)
        assert item.type == "MIDDLEMOUSE"
        action.remove(target, ctx)
        checks.append(
            "explicit mouse capture writes real keymap; exact properties retained"
        )

        action = Action("wm.context_toggle", props, ctx)
        m = menu_for(action)
        m.choose(0, ctx)
        m.start_capture(m.page.rows[3], ctx, replace_mode=True)
        m.event(event("A"), 20, 20, ctx)
        assert "Hold A" in m.page.rows[1].label
        m.event(event("A", "RELEASE"), 20, 20, ctx)
        assert "Hold one key" in m.page.rows[1].label
        m.event(event("B"), 20, 20, ctx)
        m.event(event("F19", shift=True, ctrl=True, alt=True), 20, 20, ctx)
        assert m.closed and m.error is None, m.error
        action = Action("wm.context_toggle", props, ctx)
        _, item = action.current(ctx)
        assert item.key_modifier == "B" and item.type == "F19"
        action.remove(target, ctx)
        checks.append(
            "key-modifier chord capture handles release/reset and persists both keys"
        )

        action = Action("wm.context_toggle", props, ctx)
        global_map = ctx.window_manager.keyconfigs.user.keymaps.get("User Interface")
        blocker = global_map.keymap_items.new(
            "wm.context_toggle", "F17", "PRESS", ctrl=True, alt=True, shift=True
        )
        blocker.properties.data_path = "object.show_in_front"
        try:
            m = menu_for(action)
            m.choose(0, ctx)
            m.event(event("F17", ctrl=True, alt=True, shift=True), 20, 20, ctx)
            assert not m.closed and "already used" in m.error, m.error
            assert action.existing is None
            m.event(event("RIGHTMOUSE"), -10, -10, ctx)
            assert m.closed and not m.held_keys
        finally:
            global_map.keymap_items.remove(blocker)
        checks.append(
            "cross-map conflicts reject without mutation; outside right-click cancels and passes through"
        )

        invoked = []
        m = Menu(
            target,
            (
                Entry(
                    "shortcut",
                    "Test",
                    lambda t, c: invoked.append(True),
                    bindings=(Shortcut("F19", ctrl=-1, key_modifier="B"),),
                ),
            ),
            (10, 10),
            (0, 0, 640, 700),
            context=ctx,
        )
        m.event(event("F19"), 20, 20, ctx)
        assert not invoked
        m.event(event("B"), 20, 20, ctx)
        m.event(event("F19", ctrl=True), 20, 20, ctx)
        assert invoked == [True]
        checks.append(
            "menu shortcut dispatch supports held key modifiers and wildcard modifiers"
        )

        layout = Layout(context=ctx)
        control = layout.prop_enum(obj, "rotation_mode", "ZYX")
        source = control.binding.context
        assert source.enum_value == "ZYX"
        row = property_entry(source, ctx)
        assert row.capture(target, ctx, event("F19", shift=True, ctrl=True, alt=True))
        spec = {"data_path": "object.rotation_mode", "value": "ZYX"}
        action = Action("wm.context_set_enum", spec, ctx)
        _, item = action.current(ctx)
        before = obj.rotation_mode
        bpy.ops.wm.context_set_enum(
            data_path=item.properties.data_path, value=item.properties.value
        )
        assert obj.rotation_mode == "ZYX"
        obj.rotation_mode = before
        action.remove(target, ctx)
        collapsed = rna_binding(lambda: obj, "rotation_mode").context
        assert property_entry(collapsed, ctx).children(target, ctx)
        checks.append(
            "expanded enum binds exact item; collapsed enum offers custom value choices"
        )

        bpy.types.Scene.beyond_ui_test_flags = bpy.props.EnumProperty(
            items=[("A", "A", ""), ("B", "B", "")], options={"ENUM_FLAG"}, default={"A"}
        )
        try:
            control = layout.prop_enum(ctx.scene, "beyond_ui_test_flags", "B")
            row = property_entry(control.binding.context, ctx)
            assert row.capture(
                target, ctx, event("F19", shift=True, ctrl=True, alt=True)
            )
            spec = {
                "data_path": "scene.beyond_ui_test_flags",
                "value": "(context.scene.beyond_ui_test_flags) ^ {'B'}",
            }
            action = Action("wm.context_set_value", spec, ctx)
            _, item = action.current(ctx)
            bpy.ops.wm.context_set_value(
                data_path=item.properties.data_path, value=item.properties.value
            )
            assert ctx.scene.beyond_ui_test_flags == {"A", "B"}
            bpy.ops.wm.context_set_value(
                data_path=item.properties.data_path, value=item.properties.value
            )
            assert ctx.scene.beyond_ui_test_flags == {"A"}
            action.remove(target, ctx)
        finally:
            del bpy.types.Scene.beyond_ui_test_flags
        checks.append(
            "enum-flag shortcut toggles only its exact flag and preserves other flags"
        )

        from beyond_ui.context_extensions import collect

        observed = []

        class BEYONDUI_OT_parity_choice(bpy.types.Operator):
            bl_idname = "beyondui.parity_choice"
            bl_label = "Choice"
            choice: bpy.props.EnumProperty(
                items=[("A", "Alpha", ""), ("B", "Beta", "")]
            )
            amount: bpy.props.IntProperty()

            @classmethod
            def poll(cls, context):
                return context.button_pointer == obj

            def execute(self, context):
                observed.append((self.choice, self.amount))
                return {"FINISHED"}

        bpy.utils.register_class(BEYONDUI_OT_parity_choice)
        try:

            def contribution(holder, context):
                holder.layout.prop(obj, "show_name", text="Object Name")
                holder.layout.prop(obj, "rotation_mode", text="Rotation Mode")
                holder.layout.operator_context = "EXEC_DEFAULT"
                properties = holder.layout.operator_menu_enum(
                    "beyondui.parity_choice", "choice"
                )
                properties.amount = 7
                disabled = holder.layout.row()
                disabled.enabled = False
                disabled.prop(obj, "show_in_front")

            source = rna_binding(lambda: obj, "location", index=1).context
            commits = []
            target = Target("extension", valid=source.valid, commit=commits.append)
            rows = collect(ctx, source, (contribution,))
            obj.show_name = False
            m = Menu(target, rows, (10, 10), (0, 0, 640, 700), context=ctx)
            assert not m.page.checked[0] and not m.page.available[3]
            m.choose(0, ctx)
            assert obj.show_name and commits == ["PROPERTY"]

            def reject(key):
                raise RuntimeError("rejected property transaction")

            denied = Target("extension", valid=source.valid, commit=reject)
            m = Menu(denied, rows, (10, 10), (0, 0, 640, 700), context=ctx)
            m.choose(0, ctx)
            assert obj.show_name and "rejected property" in m.error
            m = Menu(target, rows, (10, 10), (0, 0, 640, 700), context=ctx)
            m.choose(1, ctx)
            choice = next(
                i for i, r in enumerate(m.page.rows) if r.key.endswith(":ZYX")
            )
            m.choose(choice, ctx)
            assert obj.rotation_mode == "ZYX"
            m = Menu(target, rows, (10, 10), (0, 0, 640, 700), context=ctx)
            m.choose(2, ctx)
            m.choose(2, ctx)
            assert observed == [("B", 7)], (observed, m.error)
            checks.append(
                "contributed boolean/enum rows use prepared checked states, exact owner, disabled inheritance and undo rollback"
            )
            checks.append(
                "operator enum submenu preserves invocation, clicked-button context and argument snapshots"
            )
        finally:
            bpy.utils.unregister_class(BEYONDUI_OT_parity_choice)

    result = dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=checks,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print("BEYOND_UI_RESULT=" + json.dumps(result))
    bpy.ops.wm.quit_blender()


def timer():
    try:
        run()
    except Exception:
        import traceback

        traceback.print_exc()
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
