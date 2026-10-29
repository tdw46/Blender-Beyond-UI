"""Audit every current control family at three physical scales using production Canvas."""

import bpy, gpu, os, sys, json, hashlib, traceback, time, statistics
from pathlib import Path
from mathutils import Matrix
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from capture_controls import make_widgets, png, binding
from next_fixtures import widgets as next_widgets
from beyond_ui import Canvas, Theme
from beyond_ui.widgets import Progress
from beyond_ui.widgets.socket import Socket
from beyond_ui.widgets.base import Painter
from beyond_ui.gpu import glass, skin
from beyond_ui.gpu.paint import gpu_state
from beyond_ui.gpu.typography import Fonts, face
from beyond_ui.gpu.menus import text_run
from beyond_ui.context_menu import Entry

OUT = Path(os.environ["BEYOND_UI_SCALE_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)


def canvases():
    specs = (
        make_widgets()[0]
        + next_widgets()
        + [
            (
                "compact-progress-bar",
                "Compact progress bar",
                Progress(0.65, text="Processing", framed=False),
            ),
            (
                "compact-progress-ring",
                "Compact progress ring",
                Progress(0.65, type="RING", text="Processing", framed=False),
            ),
            ("socket", "Node socket", Socket((0.3, 0.7, 1, 1))),
        ]
    )
    result = []
    for slug, title, widget in specs:
        canvas = Canvas()
        canvas.title("heading", "Surrounding panel title")
        canvas.number("number", "Value", binding(0.5), min=0, max=1)
        control = canvas.widget("compound", widget)
        canvas.label("caption", "Surrounding panel body text")
        canvas.arrange(360)
        result.append((slug, title, canvas, control))
    canvas = Canvas()
    canvas.title("heading", "Standard controls")
    canvas.button("button", "Button", lambda: None)
    canvas.toggle("toggle", "Toggle", binding(True))
    canvas.number("number", "Number", binding(0.5), min=0, max=1)
    canvas.text("text", "Text", binding("Value"))
    canvas.enum("enum", "Enum", binding("A"), items=(("A", "Alpha"), ("B", "Beta")))
    canvas.color("color", "Color", binding((0.2, 0.7, 0.9, 1)), linear=False)
    canvas.add(
        "pointer", "pointer", "Pointer", pointer_field=NS(label=lambda: "Active Node")
    )
    canvas.add("search", "search", "Search", search_field=NS(label=lambda: "Target"))
    canvas.add("decorator", "decorator", decorator=None, width=32)
    canvas.arrange(360)
    result.append(("standard-controls", "Standard controls", canvas, None))
    menu = Canvas(
        context_provider=lambda t, c: [
            Entry(
                "COPY", "Copy Name", lambda t, c: None, tip="Context menu tooltip text"
            ),
            Entry("DISABLED", "Disabled option", enabled=False),
            Entry(
                "NESTED",
                "Nested menu",
                children=lambda t, c: [Entry("CHILD", "Child action")],
            ),
        ]
    )
    menu.title("title", "Menu scale")
    c = menu.button("button", "Right-click menu", lambda: None)
    for i in range(8):
        menu.label(f"space{i}", "")
    menu.arrange(360)
    assert menu.open_context(c, 25, 85, (0, 0, 360, 410), context=bpy.context)
    menu.context_menu.motion.clear()
    menu.context_menu.tooltip = ((20, 220, 240, 40), ("Context menu tooltip text",))
    result.append(("context-menu", "Context menu and tooltip", menu, None))
    return result


def run():
    font = off = under = None
    original_text = Painter.text
    rows = []
    try:
        from menu_motion_batch import configure

        batch, admission = configure()
        font = Fonts()
        for dpi in (1, 1.5, 2):
            width, height = int(380 * dpi), int(440 * dpi)
            off = gpu.types.GPUOffScreen(width, height, format="RGBA8")
            under = gpu.types.GPUOffScreen(width, height, format="RGBA8")
            with (
                off.bind(),
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
                with under.bind():
                    gpu.state.viewport_set(0, 0, width, height)
                    gpu.state.scissor_set(0, 0, width, height)
                    gpu.state.active_framebuffer_get().clear(color=(0.1, 0.13, 0.16, 1))
                    skin.draw(
                        (0, 0, width * 0.45, height), (0.16, 0.28, 0.36, 1), radius=0
                    )
                    skin.draw(
                        (width * 0.65, 0, width * 0.35, height),
                        (0.3, 0.2, 0.15, 1),
                        radius=0,
                    )
                    for i in range(12):
                        text_run(
                            face(font, "body"),
                            f"Underlying controls 0.{i:03}",
                            11 * dpi,
                            (0.85, 0.88, 0.91, 1),
                            (20 * dpi, (20 + 34 * i) * dpi),
                            ((0, 0, width, height),),
                        )
                assert glass.prepare_texture(
                    "scale-audit", dpi, under.texture_color, (0, 0, width, height)
                )
                fb = gpu.state.active_framebuffer_get()
                for slug, title, canvas, control in canvases():
                    text_sizes = []

                    def observed(p, r, value, role="text", size=22, **kwargs):
                        text_sizes.append(
                            (
                                "readout"
                                if str(value).endswith("%") and size >= 24
                                else kwargs.get("weight", "body"),
                                round(size * p.scale / dpi, 3),
                            )
                        )
                        return original_text(p, r, value, role, size, **kwargs)

                    Painter.text = observed
                    rect = (
                        10 * dpi,
                        height - (10 + canvas.height) * dpi,
                        360 * dpi,
                        canvas.height * dpi,
                    )

                    def render():
                        fb.clear(color=(0.09, 0.1, 0.11, 1))
                        glass._draw(
                            under.texture_color,
                            (0, 0, width, height),
                            (0, 0, 1, 1),
                            (0, 0, 2, 0),
                            (0, 0, 0, 0),
                            gpu.matrix.get_projection_matrix()
                            @ gpu.matrix.get_model_view_matrix(),
                        )
                        glass.lens(
                            "scale-audit",
                            rect,
                            canvas.theme.radius * dpi,
                            (0, 0, 0, 0),
                            blur=0.3,
                        )
                        canvas.paint(
                            rect,
                            (10 * dpi, 10 * dpi, 360 * dpi, 420 * dpi),
                            font=font,
                            preferences=bpy.context.preferences,
                            backdrop="scale-audit",
                        )

                    render()
                    sizes = sorted(set(text_sizes))
                    Painter.text = original_text
                    assert all(size <= 12 for role, size in sizes if role == "title"), (
                        sizes
                    )

                    def capture(name):
                        pixels = fb.read_color(0, 0, width, height, 4, 0, "UBYTE")
                        pixels.dimensions = width * height * 4
                        png(OUT / name, width, height, bytes(pixels))

                    name = f"{slug}-{dpi:g}x.png"
                    capture(name)
                    with batch():
                        render()
                    capture("batched.png")
                    assert (OUT / name).read_bytes() == (
                        OUT / "batched.png"
                    ).read_bytes(), name
                    owner = glass._owners["scale-audit"]
                    before = (
                        owner["productions"],
                        owner["strong_productions"],
                        owner["allocations"],
                        id(skin._shader),
                        id(skin._batch),
                        canvas.layout_count,
                    )
                    for _ in range(10):
                        render()
                    samples = []
                    for _ in range(50):
                        start = time.perf_counter()
                        render()
                        samples.append((time.perf_counter() - start) * 1000)
                    after = (
                        owner["productions"],
                        owner["strong_productions"],
                        owner["allocations"],
                        id(skin._shader),
                        id(skin._batch),
                        canvas.layout_count,
                    )
                    assert before == after
                    rows.append(
                        dict(
                            slug=slug,
                            title=title,
                            dpi=dpi,
                            image=name,
                            rect=control.rect if control else None,
                            text_sizes=sizes,
                            median_ms=statistics.median(samples),
                            p95_ms=sorted(samples)[47],
                            stable_resources=True,
                            resources=before,
                        )
                    )
            glass.release("scale-audit")
            off.free()
            under.free()
            off = under = None
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            backend=gpu.platform.backend_type_get(),
            theme="Factory active Blender theme; raw display-space output",
            rows=rows,
            batch_admission=admission,
            native_text_batching_equal=len(rows),
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
            fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            exact_match=False,
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        Painter.text = original_text
        glass.release("scale-audit")
        if off:
            off.free()
        if under:
            under.free()
        if font:
            font.close()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("UI_SCALE_CAPTURE", result.get("passed"), result.get("error", ""), flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.1
    )


bpy.app.timers.register(run, first_interval=1)
