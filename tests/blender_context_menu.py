"""Public RNA menu actions and extension callbacks in a disposable Blender profile."""

import bpy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout, MenuTarget
from beyond_ui.context_menu import Menu
from beyond_ui.bindings import rna_binding
from beyond_ui.context_extensions import collect
from beyond_ui.widgets.rna import color_ramp, curve_mapping, palette_source
from beyond_ui.widgets.context import target as widget_target
from beyond_ui.widgets import ColorRamp, CurveMapping, Palette


def run():
    checks = []
    commits = []
    ctx = bpy.context
    obj = ctx.active_object
    other = bpy.data.objects.new("Menu receiver", None)
    ctx.collection.objects.link(other)
    other.select_set(True)
    obj.location = (3, 4, 5)
    other.location = (8, 9, 10)
    binding = rna_binding(
        lambda: obj, "location", index=1, commit=lambda a, b: commits.append((a, b))
    )
    source = binding.context
    target = MenuTarget(
        "location", binding=binding, valid=source.valid, commit=commits.append
    )

    def execute(key, source=source, target=target):
        rows = source.entries(target, ctx)
        menu = Menu(target, rows, (0, 0), (0, 0, 640, 600), context=ctx)
        index = next(i for i, r in enumerate(rows) if r.key == key)
        assert menu.page.available[index], (key, menu.error)
        menu.choose(index, ctx)
        assert menu.closed and menu.error is None, (key, menu.error)

    execute("RESET")
    assert tuple(obj.location) == (3, 0, 5)
    execute("SELECTED")
    assert tuple(other.location) == (8, 0, 10)
    execute("PATH")
    assert ctx.window_manager.clipboard == "location[1]"
    execute("FULL_PATH")
    assert ctx.window_manager.clipboard == source.paths()[1], repr(
        ctx.window_manager.clipboard
    )
    checks.append("component reset/copy selected and explicit owner paths")

    def reject(a, b):
        raise RuntimeError("undo rejected")

    source.commit = reject
    obj.location.y = 7
    rows = source.entries(target, ctx)
    menu = Menu(target, rows, (0, 0), (0, 0, 640, 600), context=ctx)
    menu.choose(next(i for i, r in enumerate(rows) if r.key == "SELECTED"), ctx)
    assert menu.closed and menu.error == "undo rejected"
    assert other.location.y == 0
    source.commit = lambda a, b: commits.append((a, b))
    checks.append("copy selected rolls back after host transaction failure")
    execute("KEY")
    assert obj.animation_data.action is not None
    execute("DELETE_KEY")
    execute("DRIVER")
    assert obj.animation_data.drivers.find("location", index=1) is not None
    execute("REMOVE_DRIVER")
    assert obj.animation_data.drivers.find("location", index=1) is None
    checks.append(
        "keyframes and drivers use explicit data owner and host undo callback"
    )
    no_undo = MenuTarget("location", binding=binding, valid=source.valid)
    rows = source.entries(no_undo, ctx)
    menu = Menu(no_undo, rows, (0, 0), (0, 0, 640, 600), context=ctx)
    assert not menu.page.available[
        next(i for i, r in enumerate(rows) if r.key == "KEY")
    ]
    readonly = rna_binding(lambda: obj, "dimensions")
    # Public read-only metadata remains menu-readable, independently of edit binding.
    readonly = rna_binding(lambda: obj, "users")
    assert readonly.context.valid() and not readonly.context.editable()
    checks.append("read-only values remain readable; animation requires host undo")

    observed = []

    class BEYONDUI_OT_menu_fixture(bpy.types.Operator):
        bl_idname = "beyondui.menu_fixture"
        bl_label = "Fixture Action"
        amount: bpy.props.IntProperty()

        @classmethod
        def poll(cls, context):
            return (
                context.button_pointer == obj
                and context.button_prop.identifier == "location"
            )

        def execute(self, context):
            observed.append(
                (
                    context.button_pointer.as_pointer(),
                    self.amount,
                    context.menu_fixture_marker.as_pointer(),
                )
            )
            return {"FINISHED"}

    class BEYONDUI_MT_menu_fixture(bpy.types.Menu):
        bl_label = "Fixture submenu"

        def draw(self, context):
            assert context.menu_fixture_marker == other, repr(
                context.menu_fixture_marker.as_pointer()
            )
            self.layout.operator_context = "EXEC_DEFAULT"
            self.layout.operator("beyondui.menu_fixture").amount = 42

    bpy.utils.register_class(BEYONDUI_OT_menu_fixture)
    bpy.utils.register_class(BEYONDUI_MT_menu_fixture)

    def contribution(self, context):
        assert context.button_pointer == obj
        self.layout.context_pointer_set("menu_fixture_marker", other)
        self.layout.menu("BEYONDUI_MT_menu_fixture")
        self.layout.operator("ui.reset_default_button", text="Native forbidden")

    bpy.types.UI_MT_button_context_menu.append(contribution)
    try:
        rows = source.entries(target, ctx)
        menu = Menu(target, rows, (0, 0), (0, 0, 640, 600), context=ctx)
        menu.choose(
            next(i for i, r in enumerate(rows) if r.key == "BEYONDUI_MT_menu_fixture"),
            ctx,
        )
        assert len(menu.parents) == 1, menu.error
        menu.choose(1, ctx)
        assert observed == [(obj.as_pointer(), 42, other.as_pointer())], (
            observed,
            menu.error,
        )
        native = next(r for r in rows if r.label == "Native forbidden")
        assert native.enabled is False
        checks.append(
            "public button contributions preserve nested context, poll and operator properties; native button calls disabled"
        )
    finally:
        bpy.types.UI_MT_button_context_menu.remove(contribution)
        bpy.utils.unregister_class(BEYONDUI_MT_menu_fixture)
        bpy.utils.unregister_class(BEYONDUI_OT_menu_fixture)

    # Compound RNA targets are exact elements, never the current selection by accident.
    material = bpy.data.materials.new("Menu fixture")
    material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeValToRGB")
    b, ramp = color_ramp(node, "color_ramp", lambda a, b: None)
    w = ColorRamp(b)
    hit = widget_target(w, "ramp", 26, 240)
    # Explicit stop hit survives selection changes but rejects data reordering/mutation.
    from dataclasses import replace

    hit = b.context_target(MenuTarget("ramp", ("stop", 0), b, b.valid))
    assert hit.binding.context.owner() == ramp.elements[0]
    ramp.elements[0].position = 0.3
    execute("RESET", hit.binding.context, hit)
    assert ramp.elements[0].position == 0
    node2 = material.node_tree.nodes.new("ShaderNodeRGBCurve")
    node2.mapping.initialize()
    b, mapping, curve = curve_mapping(node2, "mapping", lambda a, b: None, [0])
    hit = b.context_target(MenuTarget("curve", ("point_field", 0, 0, 1), b, b.valid))
    assert hit.binding.context.index == 1
    assert hit.binding.context.owner() == curve().points[0]
    checks.append("ramp stop and curve component bind exact RNA elements")

    layout = Layout(context=ctx)
    control = layout.prop_enum(obj, "rotation_mode", "XYZ")
    assert control.binding.context.owner() == obj
    checks.append("expanded enum buttons retain property menu ownership")

    palette = bpy.data.palettes.new("Menu palette")
    paint = ctx.scene.tool_settings.image_paint
    paint.palette = palette
    palette.colors.new().color = (0.2, 0.4, 0.6)
    palette.colors.new().color = (0.9, 0.3, 0.1)
    ps = palette_source(paint, "palette", lambda a, b: None)
    widget = Palette(ps)
    hit = widget_target(widget, "palette", 140, 100)
    assert hit.binding.context.owner() == palette.colors[1]
    execute("RESET", hit.binding.context, hit)
    assert tuple(palette.colors[1].color) == (0, 0, 0)
    palette.colors.remove(palette.colors[0])
    assert not hit.valid() and not hit.binding.context.valid()
    checks.append("palette swatch property action and deletion identity validation")

    stale = rna_binding(lambda: other, "location").context
    bpy.data.objects.remove(other, do_unlink=True)
    assert not stale.valid()
    checks.append("deleted RNA owner fails closed")
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=checks,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CONTEXT_MENU_PASS", result)

    if not bpy.app.background:
        bpy.ops.wm.quit_blender()


if bpy.app.background:
    run()
else:
    bpy.app.timers.register(run, first_interval=1.0)
