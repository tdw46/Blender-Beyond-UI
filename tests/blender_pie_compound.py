"""Disposable headless RNA/compound/timing checks; no window, capture or save."""

import bpy, json, os, sys, traceback, hashlib, time, statistics
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout
from beyond_ui.pie_timing import PieSettings
from beyond_ui.context_menu import Entry, Target
from beyond_ui.pie_menu import PieMenu
import pie_fixture

groups = []


class BUI_MT_compound_pie(bpy.types.Menu):
    bl_label = "Compound Pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator_context = "EXEC_DEFAULT"
        column = pie.box().column(heading="Transform")
        row = column.row(align=True)
        row.operator("bui.pie_test", text="Move").slot = 21
        row.operator("bui.pie_test", text="Rotate").slot = 22
        column.prop(context.scene.render, "film_transparent", text="Transparent")
        column.prop(context.scene.render, "resolution_percentage", text="Resolution")
        groups.append(column)
        pie.operator("bui.pie_test", text="East").slot = 23
        pie.menu("BUI_MT_pie_more")


def run():
    checks = []
    try:
        assert bpy.app.background, "This fixture must never create a window"
        pie_fixture.register()
        bpy.utils.register_class(BUI_MT_compound_pie)
        ctx = bpy.context
        ui = Layout(context=ctx)
        ui.menu("BUI_MT_compound_pie")
        canvas = ui.canvas
        canvas.arrange(1200)
        button = next(iter(canvas.controls.values()))
        clip = (0, 0, 1200, 900)

        def open():
            assert canvas.open_operator_menu(button, clip, ctx, anchor=(600, 450)), (
                canvas.menu_error
            )
            return canvas.context_menu

        def click(menu, label):
            i, rect, row = next(v for v in menu.visible_rows() if v[2].label == label)
            x, y, w, h = rect
            count = len(pie_fixture.calls)
            canvas.event(
                NS(type="LEFTMOUSE", value="PRESS"),
                x + w / 2,
                y + h / 2,
                clip,
                context=ctx,
            )
            assert len(pie_fixture.calls) == count
            canvas.event(
                NS(type="LEFTMOUSE", value="RELEASE"),
                x + w / 2,
                y + h / 2,
                clip,
                context=ctx,
            )

        menu = open()
        assert len(menu.slots.roots) == 3 and menu.layout_mode == "PIE"
        assert len(menu.page.rows) == 7
        assert menu.origin == (600, 450)
        click(menu, "Rotate")
        assert pie_fixture.calls[-1] == 22
        menu = open()
        before = ctx.scene.render.film_transparent
        click(menu, "Transparent")
        assert ctx.scene.render.film_transparent != before
        menu = open()
        click(menu, "Resolution")
        menu.editor.text.text = "62"
        menu.event(NS(type="RET", value="PRESS"), 0, 0, ctx)
        assert ctx.scene.render.resolution_percentage == 62
        index = next(i for i, r in enumerate(menu.page.rows) if r.label == "Resolution")
        assert menu.open_row_context(index, ctx)
        assert any("Full Data Path" in r.label for r in menu.page.rows)
        menu.back()
        assert menu.radial()
        checks.append(
            "One compound direction holds a box, column, heading, horizontal operator row and exact scalar property owners; release actions and right-click navigation work"
        )
        menu = open()
        groups[-1].enabled = False
        menu.refresh(ctx)
        assert not menu.page.available[
            next(i for i, r in enumerate(menu.page.rows) if r.label == "Move")
        ]
        assert menu.page.available[
            next(i for i, r in enumerate(menu.page.rows) if r.label == "East")
        ]
        menu = open()
        click(menu, "More Actions")
        assert menu.page.search is not None and len(menu.page.rows) == 21
        checks.append(
            "Ancestor disable remains live per child; nested menu retains all searchable rows"
        )
        view = ctx.preferences.view
        settings = PieSettings.from_context(ctx)
        prefs = {
            name: getattr(view, name)
            for name in dir(view)
            if name.startswith("pie_") or "reduce_motion" in name
        }
        assert settings.tap == view.pie_tap_timeout / 100
        assert settings.animation == view.pie_animation_timeout / 100
        assert settings.recenter == view.pie_initial_timeout / 100
        assert settings.radius == view.pie_menu_radius
        assert settings.threshold == view.pie_menu_threshold
        assert settings.confirm == view.pie_menu_confirm
        clock = [0.0]
        calls = []
        rows = [
            Entry(str(i), f"Action {i}", lambda t, c, i=i: calls.append(i))
            for i in range(8)
        ]

        def timed(**options):
            clock[0] = 0
            return PieMenu(
                Target("timed"),
                rows,
                (600, 450),
                clip,
                context=ctx,
                clock=lambda: clock[0],
                trigger="Q",
                settings=PieSettings(**options),
            )

        menu = timed()
        menu.event(NS(type="Q", value="RELEASE"), 600, 450, ctx)
        assert not menu.closed and not calls
        menu = timed()
        clock[0] = 0.21
        menu.event(NS(type="Q", value="RELEASE"), 600, 450, ctx)
        assert menu.closed
        menu = timed(confirm=20)
        menu.event(NS(type="MOUSEMOVE", value="NOTHING"), 700, 450, ctx)
        clock[0] = 0.019
        menu.advance(ctx)
        assert not calls
        clock[0] = 0.021
        menu.advance(ctx)
        assert calls == [1]
        checks.append(
            "Installed pie preference values match the snapshot; quick tap, long neutral hold and optional stationary 20ms distance confirmation match the source timing branches"
        )
        menu = timed(animation=0.1)
        geometry = dict(menu.row_rectangles)
        clock[0] = 0.05
        assert menu.opening() == 0.5
        menu.event(NS(type="MOUSEMOVE", value="NOTHING"), 650, 450, ctx)
        faint = menu.highlight_alpha(menu.page, 1)
        x, y, w, h = menu.rectangles[1]
        menu.event(NS(type="MOUSEMOVE", value="NOTHING"), x - 1, y + h / 2, ctx)
        assert menu.highlight_alpha(menu.page, 1) > faint
        assert menu.guide()[0] == (600, 450)
        clock[0] = 1
        assert menu.pull(1) != (0, 0)
        assert geometry == menu.row_rectangles
        menu.motion.settings.enabled = False
        assert menu.opening() == 1 and menu.pull(1) == (0, 0) and not menu.advance(ctx)
        checks.append(
            "Pointer-origin grow, proximity highlight, guide origin and finite source-spring pull preserve logical hit geometry; disabling motion restores rest"
        )
        # Exact same headless event workload with/without animation policy. No GPU claim.
        timings = {}
        for enabled in (False, True):
            menu = timed()
            menu.trigger = None
            menu.motion.settings.enabled = enabled
            samples = []
            for i in range(1200):
                clock[0] = i / 60
                t = time.perf_counter()
                menu.event(
                    NS(type="MOUSEMOVE", value="NOTHING"), 650 + i % 40, 450, ctx
                )
                menu.advance(ctx)
                menu.motion.advance()
                if i >= 200:
                    samples.append((time.perf_counter() - t) * 1000)
            assert len(menu.motion.positions) <= 16 and len(menu.motion.tracks) <= 32
            timings[str(enabled)] = dict(
                median_ms=statistics.median(samples), p95_ms=sorted(samples)[949]
            )
            menu.close()
            assert (
                not menu.motion.positions
                and not menu.motion.tracks
                and not menu.advance(ctx)
            )
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            checks=checks,
            preferences=prefs,
            event_timings=timings,
            visual_verified=False,
            windowed_tests="blocked",
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / "beyond_ui").rglob("*.py")
            },
        )
    except Exception:
        result = dict(passed=False, checks=checks, error=traceback.format_exc())
    finally:
        if BUI_MT_compound_pie.is_registered:
            bpy.utils.unregister_class(BUI_MT_compound_pie)
        pie_fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("COMPOUND_PIE", result.get("passed"), result.get("error", ""), flush=True)


if __name__ == "__main__":
    run()
