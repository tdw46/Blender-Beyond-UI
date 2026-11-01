"""Native-compatible inline styling against real RNA in an isolated window."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import beyond_ui as bui
from beyond_ui.layout_recording import Tape
from beyond_ui.context_menu import Target

checks = []
native_draws = []


class StyleData(bpy.types.PropertyGroup):
    number: bpy.props.FloatProperty(default=155.234, min=0, max=500)
    count: bpy.props.IntProperty(default=3)
    flag: bpy.props.BoolProperty(default=True)
    text: bpy.props.StringProperty(default="Camera")
    enum: bpy.props.EnumProperty(items=[("A", "First", ""), ("B", "Second", "")])
    pointer: bpy.props.PointerProperty(type=bpy.types.Object)
    vector: bpy.props.FloatVectorProperty(size=3, subtype="XYZ")
    color: bpy.props.FloatVectorProperty(
        size=4, subtype="COLOR_GAMMA", default=(0.2, 0.6, 0.8, 1)
    )
    length: bpy.props.FloatProperty(unit="LENGTH", default=1)
    angle: bpy.props.FloatProperty(unit="ROTATION", default=1)


def draw(layout, data):
    bui.style(layout, scope="group", gap=8)
    for name in (
        "number",
        "count",
        "flag",
        "text",
        "enum",
        "pointer",
        "vector",
        "color",
    ):
        layout.prop(data, name)
        bui.style(layout, padding=(2, 4), color="#E5ECEF", motion={"strength": 0.4})
    layout.prop(data, "length")
    bui.style(layout, units="cm", precision=1, value_width=78)
    bui.prop(layout, data, "angle", style={"units": "deg", "precision": 1})


class NativeStyleDialog(bpy.types.Operator):
    bl_idname = "wm.bui_native_style_test"
    bl_label = "Native compatibility fixture"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        try:
            draw(self.layout, context.scene.bui_style_data)
            native_draws.append(True)
        except Exception:
            native_draws.append(traceback.format_exc())

    def execute(self, context):
        return {"FINISHED"}


def finish(error=None):
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(
            dict(
                passed=error is None,
                error=error,
                checks=checks,
                version=bpy.app.version_string,
                native_draws=native_draws,
            ),
            indent=2,
        )
    )
    bpy.ops.wm.quit_blender()


def verify():
    try:
        assert native_draws and all(x is True for x in native_draws), native_draws
        checks.append(
            "Unchanged native UILayout.prop calls plus style helpers render without extra RNA keywords"
        )
        finish()
    except Exception:
        finish(traceback.format_exc())


def run():
    try:
        bpy.utils.register_class(StyleData)
        bpy.types.Scene.bui_style_data = bpy.props.PointerProperty(type=StyleData)
        bpy.utils.register_class(NativeStyleDialog)
        data = bpy.context.scene.bui_style_data
        data.pointer = bpy.context.object
        tape = Tape()
        draw(tape.root, data)
        ui = bui.Layout(context=bpy.context)
        tape.play(ui)
        ui.canvas.arrange(420)
        assert len(ui.canvas.controls) == 12, len(ui.canvas.controls)
        for c in ui.canvas.controls.values():
            assert c.binding and c.binding.valid()
        number = next(iter(ui.canvas.controls.values()))
        number.binding.write(180.5)
        assert data.number == 180.5
        c = next(
            c
            for c in ui.canvas.controls.values()
            if c.kind == "number" and c.options["numeric"].unit == "LENGTH"
        )
        n = c.options["numeric"]
        assert n.format(1) == "100.0 (cm)", n.format(1)
        assert abs(n.parse("25 (cm)", 1) - 0.25) < 1e-9
        assert abs(n.parse("250 mm", 1) - 0.25) < 1e-6
        count = ui.canvas.layout_count
        ui.canvas.arrange(420)
        assert ui.canvas.layout_count == count
        checks.append(
            "Boolean/int/float/string/enum/pointer/vector/color styles preserve real bindings and retained layout"
        )
        checks.append(
            "Native length and rotation codecs support explicit displayed units without changing storage"
        )
        before = tuple(tape.signature)
        data.number = 200
        assert tuple(tape.signature) == before
        checks.append("Value edits do not change style recording signatures")
        composition = Tape()
        box = composition.root.box()
        bui.style(box, scope="group", color="#FFFFFF")
        row = box.row()
        row.prop(data, "count")
        row.prop(data, "number")
        bui.style(box, gap=13, padding=4)
        composed = bui.Layout(context=bpy.context)
        composition.play(composed)
        composed.canvas.arrange(420)
        group = composed.canvas.children[0]
        from beyond_ui.flow import Plan
        plan = Plan(composed.canvas.theme)
        assert plan.insets(group) == (plan.box_padding,) * 4
        a, b = tuple(composed.canvas.controls.values())
        assert abs(b.rect[0] - a.rect[0] - a.rect[2] - 13) < 1e-6
        assert a.binding.valid() and b.binding.valid()
        checks.append("Composed row presets retain internal gaps, box padding and RNA owners")
        bpy.ops.wm.bui_native_style_test("INVOKE_DEFAULT")
        bpy.app.timers.register(verify, first_interval=2)
    except Exception:
        finish(traceback.format_exc())


bpy.app.timers.register(run, first_interval=1)
