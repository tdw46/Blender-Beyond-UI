"""Isolated actual-RNA theme updates through production Canvas and all 8 cards.

Synthetic light/custom roles are execution fixtures, not approved theme references.
"""

import bpy, gpu
import hashlib, json, os, sys, traceback
from pathlib import Path
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import make_widgets, png
from next_fixtures import widgets as next_widgets
from beyond_ui import Canvas, Theme
from beyond_ui.gpu import style, skin, progress
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts
from beyond_ui.widgets.base import _LINE_CACHE

OUT = Path(os.environ["BEYOND_UI_THEME_DIR"])
OUT.mkdir(parents=True, exist_ok=True)
FIELDS = (
    ("wcol_radio", "inner_sel"),
    ("wcol_regular", "inner"),
    ("wcol_regular", "text"),
    ("wcol_tool", "inner"),
    ("wcol_num", "inner"),
    ("wcol_tab", "inner_sel"),
    ("wcol_numslider", "inner"),
    ("wcol_numslider", "item"),
    ("wcol_toggle", "inner"),
    ("wcol_toggle", "inner_sel"),
    ("wcol_radio", "text_sel"),
)


def run():
    font = target = None
    ui = bpy.context.preferences.themes[0].user_interface
    original = {(w, f): tuple(getattr(getattr(ui, w), f)) for w, f in FIELDS}
    result = {"passed": False}
    try:
        font = Fonts()
        widgets, _ = make_widgets()
        widgets += next_widgets()
        canvases = []
        for slug, title, widget in widgets:
            canvas = Canvas(Theme(padding=10))
            canvas.widget(slug, widget)
            canvas.arrange(340)
            canvases.append(canvas)
        width, height = 1360, 560
        target = gpu.types.GPUOffScreen(width, height, format="RGBA8")

        def resources():
            return (
                {k: id(v[1]) for k, v in _LINE_CACHE.items()},
                tuple(
                    id(t) for _, _, w in widgets for t in getattr(w, "_textures", ())
                ),
                id(skin._batch),
                id(progress._batch),
                tuple(c.layout_count for c in canvases),
            )

        def render():
            gpu.state.active_framebuffer_get().clear(color=(0.086, 0.098, 0.106, 1))
            for i, canvas in enumerate(canvases):
                x, y = (i % 4) * 340, height - (i // 4) * 280 - canvas.height
                r = (x, y, 340, canvas.height)
                canvas.paint(r, r, font=font, preferences=bpy.context.preferences)
            buffer = gpu.state.active_framebuffer_get().read_color(
                0, 0, width, height, 4, 0, "UBYTE"
            )
            buffer.dimensions = width * height * 4
            return bytes(buffer)

        def data_pixels(data):
            # Interior pixels avoid chrome/markers. Locations are fixture-space,
            # mapped through the actual retained Canvas control rectangles.
            samples = []
            for index, points in (
                (1, ((50, 230), (310, 230), (560, 230))),
                (3, ((100, 180), (220, 240), (150, 423))),
                (4, ((60, 100), (160, 100), (260, 100), (560, 190))),
            ):
                canvas = canvases[index]
                control = next(iter(canvas.controls.values()))
                widget = control.options["widget"]
                a, b, w, h = control.rect
                for px, py in points:
                    x = int((index % 4) * 340 + a + px * w / widget.width)
                    y = int(height - (index // 4) * 280 - b - py * h / widget.height)
                    samples.append(data[(y * width + x) * 4 : (y * width + x) * 4 + 4])
            return samples

        states = []
        color_samples = None
        with (
            target.bind(),
            gpu_state(),
            gpu.matrix.push_pop(),
            gpu.matrix.push_pop_projection(),
        ):
            gpu.state.viewport_set(0, 0, width, height)
            gpu.state.scissor_set(0, 0, width, height)
            gpu.state.scissor_test_set(True)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(
                Matrix(
                    (
                        (2 / width, 0, 0, -1),
                        (0, 2 / height, 0, -1),
                        (0, 0, 1, 0),
                        (0, 0, 0, 1),
                    )
                )
            )
            try:
                render()
                warm = resources()
                for name in ("native-dark", "synthetic-light", "synthetic-purple"):
                    if name != "native-dark":
                        light = name == "synthetic-light"
                        accent = (
                            (0.12, 0.34, 0.72, 1) if light else (0.66, 0.24, 0.78, 1)
                        )
                        regular = (
                            (0.8, 0.82, 0.85, 1) if light else (0.15, 0.11, 0.19, 1)
                        )
                        text = (0.06, 0.07, 0.09) if light else (0.94, 0.89, 0.98)
                        for w, f in FIELDS:
                            value = (
                                text
                                if f == "text"
                                else (1, 1, 1)
                                if f == "text_sel"
                                else accent
                                if f in ("inner_sel", "item")
                                else regular
                            )
                            setattr(getattr(ui, w), f, value)
                    p = style.theme_palette(bpy.context.preferences)
                    assert p["source"] == "blender" and not p["fallback_roles"]
                    assert p is style.theme_palette(bpy.context.preferences)
                    assert p["accent"][:3] == tuple(ui.wcol_radio.inner_sel)[:3]
                    data = render()
                    samples = data_pixels(data)
                    if color_samples is None:
                        color_samples = samples
                    assert samples == color_samples, "Theme recolored bound data pixels"
                    assert resources() == warm, (
                        "Theme change rebuilt geometry/textures/layout"
                    )
                    png(OUT / (name + ".png"), width, height, data)
                    states.append(
                        {
                            "name": name,
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "palette": dict(
                                p, surfaces=dict(p["surfaces"]), tokens=None
                            ),
                            "rna": {
                                w + "." + f: list(getattr(getattr(ui, w), f))
                                for w, f in FIELDS
                            },
                        }
                    )
                assert len({s["sha256"] for s in states}) == 3
                # An explicit reference canvas remains independent of live Blender colors.
                for c in canvases:
                    c.theme = Theme(padding=10, palette="REFERENCE")
                reference = render()
                ui.wcol_regular.text = (0.1, 0.2, 0.3)
                assert reference == render(), "Theme leaked into reference fixtures"
                assert resources() == warm
                png(OUT / "reference.png", width, height, reference)
            finally:
                gpu.state.scissor_test_set(False)
        result = {
            "passed": True,
            "runtime": bpy.app.version_string,
            "build": bpy.app.build_hash.decode(),
            "backend": gpu.platform.backend_type_get(),
            "size": [width, height],
            "states": states,
            "warm_resources_unchanged": True,
            "reference_independent": True,
            "bound_data_pixels_unchanged": True,
            "color_management": "UI display-space; offscreen RGBA8, no scene view transform",
            "acceptance": "Execution evidence only; light/custom references and Tyler visual QA pending",
            "source_sha256": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
        }
    except Exception:
        result = {"passed": False, "error": traceback.format_exc()}
    finally:
        for (w, f), value in original.items():
            setattr(getattr(ui, w), f, value)
        result["rna_restored"] = all(
            tuple(getattr(getattr(ui, w), f)) == v for (w, f), v in original.items()
        )
        if target:
            target.free()
        if font is not None:
            font.close()
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "BEYOND_UI_THEME",
        json.dumps(
            {k: v for k, v in result.items() if k not in ("states", "source_sha256")}
        ),
        flush=True,
    )
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=1)
