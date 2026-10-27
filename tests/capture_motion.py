"""Actual production Canvas animation frames, with a deterministic fixture clock."""

import bpy, gpu
from mathutils import Matrix
from pathlib import Path
import os, sys, json, hashlib, traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from capture_controls import make_widgets, png
from next_fixtures import widgets as next_widgets
from beyond_ui import Canvas, Theme
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts
from beyond_ui.widgets.base import _LINE_CACHE
from types import SimpleNamespace

OUT = Path(os.environ["BEYOND_UI_MOTION_DIR"])
OUT.mkdir(parents=True, exist_ok=True)


def run():
    font = target = None
    try:
        old, _ = make_widgets()
        widgets = old + next_widgets()
        now = [0.0]
        canvases = []
        for slug, title, widget in widgets:
            canvas = Canvas(Theme(padding=10))
            control = canvas.widget(slug, widget)
            canvas.arrange(340)
            widget.motion.clock = lambda: now[0]
            canvases.append((slug, widget, canvas, control))
        font = Fonts()
        width, height = 1360, 560
        target = gpu.types.GPUOffScreen(width, height, format="RGBA8")
        hashes = {}
        caches = []
        with (
            target.bind(),
            gpu_state(),
            gpu.matrix.push_pop(),
            gpu.matrix.push_pop_projection(),
        ):
            gpu.state.viewport_set(0, 0, width, height)
            gpu.state.scissor_set(0, 0, width, height)
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

            def render(name):
                gpu.state.active_framebuffer_get().clear(color=(0.086, 0.098, 0.106, 1))
                for i, (_, widget, canvas, control) in enumerate(canvases):
                    x, y = (i % 4) * 340, height - (i // 4) * 280 - canvas.height
                    canvas.paint(
                        (x, y, 340, canvas.height),
                        (x, y, 340, canvas.height),
                        font=font,
                    )
                data = gpu.state.active_framebuffer_get().read_color(
                    0, 0, width, height, 4, 0, "UBYTE"
                )
                data.dimensions = width * height * 4
                raw = bytes(data)
                hashes[name] = hashlib.sha256(raw).hexdigest()
                png(OUT / (name + ".png"), width, height, raw)

            render("rest")
            cache_before = {key: id(value[1]) for key, value in _LINE_CACHE.items()}
            # Source-like entry, press, drag and release; read-only controls use changes.
            targets = [(100, 90), (480, 105), (100, 175), (170, 90), (260, 120)]
            for frame in range(75):
                now[0] = frame / 30
                if frame in (0, 8, 13, 16):
                    kind, value = (
                        ("MOUSEMOVE", "NOTHING")
                        if frame in (0, 13)
                        else ("LEFTMOUSE", "PRESS" if frame == 8 else "RELEASE")
                    )
                    event = SimpleNamespace(
                        type=kind,
                        value=value,
                        shift=False,
                        ctrl=False,
                        oskey=False,
                        unicode="",
                    )
                    for i, (slug, widget, canvas, control) in enumerate(canvases):
                        if i >= 5:
                            if frame == 0:
                                canvas.notify_changed(slug)
                        else:
                            wx, wy = targets[i]
                            if frame == 13:
                                wx += 8
                            a, b, w, h = control.rect
                            # Decorative input only: no fixture data mutations.
                            canvas._motion_input(
                                event,
                                a + wx * w / widget.width,
                                b + wy * h / widget.height,
                                (0, 0, 340, canvas.height),
                            )
                render(f"frame-{frame:03}")
                for _, _, canvas, _ in canvases:
                    canvas.advance_animations()
            now[0] = 4.0
            for _, _, canvas, _ in canvases:
                canvas.advance_animations()
            render("settled")
            assert hashes["rest"] == hashes["settled"], "Settled image changed"
            for slug, _, canvas, _ in canvases:
                canvas.notify_changed(slug)
            now[0] += 0.10
            render("active")
            for _, _, canvas, _ in canvases:
                canvas.animation.enabled = False
                assert not canvas.advance_animations()
            render("disabled")
            assert hashes["rest"] == hashes["disabled"], (
                "Disable did not restore exact pixels"
            )
            assert hashes["rest"] != hashes["active"], (
                "Motion failed to affect actual rendering"
            )
            assert {
                key: id(value[1]) for key, value in _LINE_CACHE.items()
            } == cache_before, "Motion rebuilt geometry"
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            build=bpy.app.build_hash.decode(),
            backend=gpu.platform.backend_type_get(),
            checks=[
                "actual Canvas motion frames",
                "settled and disabled pixels identical to rest",
                "retained geometry unchanged",
                "finite animation queues empty",
            ],
            hashes=hashes,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            note="Deterministic 30fps fixture clock; tint-only transparency. No reference pixels or live scene modifications. Motion reference matching awaits QA.",
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        if target is not None:
            target.free()
        if font is not None:
            font.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print("BEYOND_UI_MOTION", result.get("passed"), result.get("error", ""), flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=1)
