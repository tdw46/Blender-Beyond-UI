"""Macro operator properties must survive one-line UI adoption and teardown."""

import bpy, os, sys, json, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_ui import integrate


class MACROTEST_OT_step(bpy.types.Operator):
    bl_idname = "macrotest.step"
    bl_label = "Step"
    value: bpy.props.StringProperty(default="original")

    def execute(self, context):
        return {"FINISHED"}


class MACROTEST_OT_group(bpy.types.Macro):
    bl_idname = "macrotest.group"
    bl_label = "Group"


def register():
    bpy.utils.register_class(MACROTEST_OT_step)
    bpy.utils.register_class(MACROTEST_OT_group)
    MACROTEST_OT_group.define("MACROTEST_OT_step")
    keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
        name="3D View", space_type="VIEW_3D"
    )
    item = keymap.keymap_items.new("macrotest.group", "F8", "PRESS")
    item.properties.MACROTEST_OT_step.value = "before integration"


def unregister():
    bpy.utils.unregister_class(MACROTEST_OT_group)
    bpy.utils.unregister_class(MACROTEST_OT_step)


if os.environ.get("BEYOND_UI_MACRO_INTEGRATE", "1") == "1":
    integrate(globals())

state = [0]


def run():
    try:
        if state[0] == 0:
            register()
            state[0] = 1
            return 0.5
        keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
            name="3D View", space_type="VIEW_3D"
        )
        item = keymap.keymap_items.new("macrotest.group", "F8", "PRESS")
        print("MACRO_PROPERTY_WRITE", flush=True)
        item.properties.MACROTEST_OT_step.value = "after integration"
        assert item.properties.MACROTEST_OT_step.value == "after integration"
        keymap.keymap_items.remove(item)
        if os.environ.get("BEYOND_UI_MACRO_INTEGRATE", "1") == "1":
            integration = globals()["__beyond_ui_integration__"]
            assert integration.router.macro_dependencies
            integration.stop()
            # Teardown must also leave the original child RNA alive.
            item = keymap.keymap_items.new("macrotest.group", "F8", "PRESS")
            item.properties.MACROTEST_OT_step.value = "after teardown"
            assert item.properties.MACROTEST_OT_step.value == "after teardown"
            keymap.keymap_items.remove(item)
            integration.original_unregister()
        else:
            unregister()
        result = dict(passed=True, version=bpy.app.version_string)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
