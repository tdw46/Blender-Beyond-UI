"""Disposable actual-RNA numeric units, transactions and source-style gestures."""

import bpy, json, os, sys, math, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout
from beyond_ui.numeric import Numeric, _unit_text, _unit_factor
from beyond_ui.context_fields import property_row
from beyond_ui.context_menu import Menu, Target


def ev(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


class BEYONDUI_PG_numbers(bpy.types.PropertyGroup):
    distance: bpy.props.FloatProperty(
        unit="LENGTH", subtype="DISTANCE", default=1, precision=3
    )
    area_value: bpy.props.FloatProperty(unit="AREA", default=2)
    volume: bpy.props.FloatProperty(unit="VOLUME", default=3)
    angle: bpy.props.FloatProperty(subtype="ANGLE", default=1.23456789)
    factor: bpy.props.FloatProperty(subtype="FACTOR", min=0, max=1, default=0.25)
    bounded: bpy.props.FloatProperty(
        min=-10, max=10, soft_min=-1, soft_max=1, default=0.25
    )
    count: bpy.props.IntProperty(min=0, max=100, default=12)


def run():
    bpy.utils.register_class(BEYONDUI_PG_numbers)
    bpy.types.Scene.beyond_numbers = bpy.props.PointerProperty(type=BEYONDUI_PG_numbers)
    checks = []
    try:
        ctx = bpy.context
        scene = ctx.scene
        obj = ctx.active_object
        data = scene.beyond_numbers
        settings = scene.unit_settings
        settings.system = "METRIC"
        settings.scale_length = 0.1
        settings.length_unit = "CENTIMETERS"
        c = Numeric(data.bl_rna.properties["distance"], ctx)
        assert (
            c.format(1).endswith(" cm")
            and abs(float(c.format(1).split()[0]) - 10) < 1e-4
        )
        assert abs(c.parse("1m 3cm", 1) - 10.3) < 1e-5
        assert abs(c.parse("50", 1) - 5) < 1e-5
        assert abs(c.display_scale(c.snapshot()) - 10) < 1e-5
        settings.system = "IMPERIAL"
        settings.length_unit = "FEET"
        settings.scale_length = 1
        assert abs(c.parse("1ft", 1) - 0.3048) < 1e-6
        settings.system = "METRIC"
        settings.length_unit = "METERS"
        settings.scale_length = 0.1
        for prop, power in [("area_value", 2), ("volume", 3)]:
            n = Numeric(data.bl_rna.properties[prop], ctx)
            assert abs(n.scale(n.snapshot()) - 0.1**power) < 1e-7
            before = getattr(data, prop)
            assert n.parse(n.format(before), before) == before
        checks.append(
            "metric/imperial input, explicit preferred units, bare values, scene scale and area/volume powers"
        )
        angle = Numeric(data.bl_rna.properties["angle"], ctx)
        assert abs(angle.parse("90°", 0) - math.pi / 2) < 1e-6
        assert abs(angle.parse("1rad", 0) - 1) < 1e-6
        settings.system_rotation = "RADIANS"
        assert angle.parse("2", 0) == 2
        settings.system_rotation = "DEGREES"
        ctx.preferences.view.factor_display_type = "PERCENTAGE"
        factor = Numeric(data.bl_rna.properties["factor"], ctx)
        assert factor.format(0.25) == "25%" and factor.parse("50", 0) == 0.5
        checks.append(
            "rotation units, radians preference, factor percentage preference, exact unchanged roundtrip"
        )
        commits = []
        ui = Layout(
            context=ctx, commit=lambda before, after: commits.append((before, after))
        )
        a = ui.prop(data, "angle")
        length = ui.prop(data, "distance")
        bounded = ui.prop(data, "bounded", slider=True)
        ui.prop(obj, "rotation_euler")
        canvas = ui.canvas
        canvas.arrange(600)
        clip = (0, 0, 600, canvas.height)
        assert all(c.options.get("numeric") for c in canvas.controls.values())

        def input(control, text):
            x, y, w, h = control.rect
            canvas.event(
                ev("LEFTMOUSE", "DOUBLE_CLICK"), x + 30, y + 10, clip, context=ctx
            )
            canvas.event(
                ev("TEXTINPUT", unicode=text), x + 30, y + 10, clip, context=ctx
            )
            canvas.event(ev("RET"), x + 30, y + 10, clip, context=ctx)

        original = data.angle
        x, y, w, h = a.rect
        canvas.event(ev("LEFTMOUSE"), x + 20, y + 10, clip, context=ctx)
        canvas.event(ev("LEFTMOUSE", "RELEASE"), x + 20, y + 10, clip, context=ctx)
        assert canvas.editor and not commits
        canvas.event(ev("RET"), x + 20, y + 10, clip, context=ctx)
        assert data.angle == original and not commits
        input(a, "90")
        assert abs(data.angle - math.pi / 2) < 1e-6 and len(commits) == 1
        input(length, "30cm")
        assert abs(data.distance - 3) < 1e-5
        input(bounded, "5")
        assert data.bounded == 5
        x, y, w, h = bounded.rect
        canvas.event(ev("LEFTMOUSE"), x + 20, y + 10, clip, context=ctx)
        canvas.event(ev("MOUSEMOVE", "NOTHING"), x + 60, y + 10, clip, context=ctx)
        assert -1 <= data.bounded <= 1
        canvas.event(ev("RIGHTMOUSE"), x + 60, y + 10, clip, context=ctx)
        assert data.bounded == 5 and canvas.context_menu is None
        data.bounded = 0.25
        x, y, w, h = bounded.rect
        canvas.event(ev("LEFTMOUSE"), x + 20, y + 10, clip, context=ctx)
        canvas.event(
            ev("MOUSEMOVE", "NOTHING", ctrl=True), x + 47, y + 10, clip, context=ctx
        )
        snap = bounded.options["numeric"].step / 100
        assert abs(data.bounded / snap - round(data.bounded / snap)) < 1e-4
        canvas.event(ev("RIGHTMOUSE"), x + 47, y + 10, clip, context=ctx)
        assert data.bounded == 0.25
        x, y, w, h = length.rect
        canvas.event(ev("LEFTMOUSE", "DOUBLE_CLICK"), x + 20, y + 10, clip, context=ctx)
        settings.scale_length = 2
        canvas.event(ev("TEXTINPUT", unicode="20"), x + 20, y + 10, clip, context=ctx)
        canvas.event(ev("RET"), x + 20, y + 10, clip, context=ctx)
        assert canvas.editor and abs(data.distance - 3) < 1e-5
        canvas.cancel()
        settings.scale_length = 0.1
        checks.append(
            "custom canvas click-to-type, unchanged confirmation, converted writes, soft drag/hard text bounds, cancel-before-menu and changed unit rejection"
        )
        m = Menu(
            Target("numbers", commit=lambda action: commits.append(action)),
            (property_row(data, "distance"),),
            (10, 10),
            (0, 0, 600, 560),
            context=ctx,
        )
        assert "m" in m.page.values[0]
        m.choose(0, ctx)
        m.event(ev("TEXTINPUT", unicode="40cm"), 20, 20, ctx)
        m.event(ev("RET"), 20, 20, ctx)
        assert abs(data.distance - 4) < 1e-5
        m.choose(0, ctx)
        settings.scale_length = 3
        m.event(ev("RET"), 20, 20, ctx)
        assert m.error and abs(data.distance - 4) < 1e-5
        m.close()
        settings.scale_length = 0.1
        # Same clicked RNA component, shared context contract, not display-converted binding.
        assert canvas.open_context(a, 20, 20, clip, context=ctx)
        assert canvas.context_menu.target.binding.read() == data.angle
        canvas.close_context()
        checks.append(
            "contributed field units and settings guard; exact native RNA context target retained"
        )
        c.format(4)
        start = (_unit_text.cache_info().misses, _unit_factor.cache_info().misses)
        for _ in range(1000):
            c.format(4)
        assert start == (
            _unit_text.cache_info().misses,
            _unit_factor.cache_info().misses,
        )
        checks.append(
            "warm formatting reuses bounded unit caches without registration or timers"
        )
    finally:
        del bpy.types.Scene.beyond_numbers
        bpy.utils.unregister_class(BEYONDUI_PG_numbers)
    result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print("BEYOND_UI_NUMERIC", json.dumps(result))


run()
