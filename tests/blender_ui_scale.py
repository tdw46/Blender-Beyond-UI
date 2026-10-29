"""Shared popup sizing and color/palette input in disposable Blender profiles."""

import bpy, os, sys, json
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, Layout
from beyond_ui.widgets.metrics import COLOR

ctx = bpy.context
bpy.types.Scene.scale_palette = bpy.props.PointerProperty(type=bpy.types.Palette)
palette = bpy.data.palettes.new("ScaleFixture")
for rgb in ((0.2, 0.4, 0.6), (0.7, 0.3, 0.1)):
    palette.colors.new().color = rgb
palette.colors.active = palette.colors[0]
ctx.scene.scale_palette = palette
try:
    canvas = Canvas()
    ui = Layout(canvas, context=ctx)
    pointer = ui.prop(ctx.scene, "camera", text="Target")
    search = ui.prop_search(ctx.scene, "camera", bpy.data, "objects", text="Search")
    color = ui.prop(ctx.object, "color", text="Color")
    pal = ui.template_palette(ctx.scene, "scale_palette", color=True)
    for width in (360, 560, 960):
        canvas.arrange(width)
        clip = (0, 0, width, 520)
        for control in (pointer, search, color):
            canvas.cancel()
            x, y, w, h = control.rect
            canvas.event(
                NS(type="LEFTMOUSE", value="PRESS"), x + 10, y + 10, clip, context=ctx
            )
            assert canvas.overlay is not None, canvas.menu_error
            assert canvas.overlay["rect"][2:] == (315, 236)
            assert canvas.overlay["widget"].glass_blur == 0.7
            if control is color:
                before = tuple(ctx.object.color)
                a, b, w, h = canvas.overlay["rect"]
                sx, sy, sw, sh = COLOR["sv"]
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    a + (sx + sw * 0.3) * w / 630,
                    b + (sy + sh * 0.6) * h / 472,
                    clip,
                    context=ctx,
                )
                assert tuple(ctx.object.color) != before
                canvas.event(
                    NS(type="RIGHTMOUSE", value="PRESS"), a, b, clip, context=ctx
                )
                assert tuple(ctx.object.color) == before and canvas.overlay is None
        canvas.cancel()
        clip = (15, 10, 320, 300)
        canvas.event(NS(type="MOUSEMOVE", value="NOTHING"), -1, -1, clip, context=ctx)
        pal.options["widget"].source.edit(0)
        assert canvas.overlay["owner"] is pal and canvas.overlay["rect"][2:] == (
            315,
            236,
        )
        assert canvas.overlay["widget"].glass_blur == 0.7
        x, y, w, h = canvas.overlay["rect"]
        assert x >= 15 and x + w <= 335 and y >= 10 and y + h <= 310
        canvas.cancel()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Pointer, search and color popovers retain 315x236 logical size at 360/560/960 panel widths",
            "Rescaled color hit mapping edits and right-click cancellation restores the bound color",
            "Palette editing uses the shared scale, current viewport clip, exact owner and strong glass",
        ],
    )
finally:
    del bpy.types.Scene.scale_palette
    bpy.data.palettes.remove(palette)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("UI_SCALE", result)
