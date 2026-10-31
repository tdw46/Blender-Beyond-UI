"""One-line setup with manual aliases and Blender's register_classes_factory."""

import bpy, importlib, json, os, sys, traceback
import statistics, time
from pathlib import Path

sys.path.insert(0, os.environ["BEYOND_UI_CONSUMER_ROOT"])
a = importlib.import_module("legacy_manual")
b = importlib.import_module("legacy_factory")
loader_module = importlib.import_module("legacy_loader")
state = {"stage": 0}
checks = []
performance = {}
window = bpy.context.window
area = next(x for x in window.screen.areas if x.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(x for x in area.regions if x.type == "UI")
original = a.LEGACY_MANUAL_PT_panel.draw


def host():
    return next(iter(a.__beyond_ui_integration__.ui._runtime.hosts.values()))


def current():
    return next(r for r in host().records.values() if r["valid"])


def event(kind, value="PRESS"):
    r = current()
    c = r["canvas"]
    control = next(x for x in c.controls.values() if x.kind == "toggle")
    x, y, w, h = control.rect
    rx, ry, rw, rh = r["rect"]
    window.event_simulate(
        type=kind,
        value=value,
        x=int(region.x + rx + (x + w / 2) * rw / c._width),
        y=int(region.y + ry + rh - (y + h / 2) * rh / c.height),
    )


def finish(error=None):
    try:
        a.unregister()
        b.unregister()
        loader_module.unregister()
    finally:
        Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
            json.dumps(
                dict(
                    passed=error is None,
                    version=bpy.app.version_string,
                    checks=checks,
                    performance=performance,
                    error=error,
                ),
                indent=2,
            )
        )
        bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["stage"]
        if n == 0:
            a.register()
            b.register()
            loader_module.register()
            props_area = next(x for x in window.screen.areas if x.type == "PROPERTIES")
            props_area.spaces.active.context = "RENDER"
            props_area.tag_redraw()
            assert (
                a.LEGACY_MANUAL_PT_panel.is_registered
                and b.LEGACY_FACTORY_PT_panel.is_registered
                and loader_module.auto_load.panels.LEGACY_LOADER_PT_panel.is_registered
            )
            for module in (a, b, loader_module):
                report = module.__beyond_ui_integration__.status
                assert report["native_routes"][0]["routes"] == ["invoke_props_dialog"]
        elif n == 1:
            region.active_panel_category = "legacy_manual"
        elif n == 2:
            assert any(
                r["valid"]
                for h in b.__beyond_ui_integration__.ui._runtime.hosts.values()
                for r in h.records.values()
            ), "Factory-registered Properties panel did not render"
            r = current()
            state["canvas"] = r["canvas"]
            state["before"] = bpy.context.scene.render.film_transparent
            assert a.__beyond_ui_integration__.ui._runtime.running
            region.tag_redraw()
        elif n == 3:
            assert current()["canvas"] is state["canvas"]
            from legacy_manual._vendor.beyond_ui.layout_recording import Tape
            from legacy_manual._vendor.beyond_ui.hosts.addon import PanelProxy
            from legacy_manual._vendor.beyond_ui import Layout

            timings = {"record_and_signature_ms": [], "rebuild_layout_ms": []}
            for _ in range(100):
                start = time.perf_counter()
                tape = Tape()
                original(PanelProxy(a.LEGACY_MANUAL_PT_panel, tape.root), bpy.context)
                tuple(tape.signature)
                timings["record_and_signature_ms"].append(
                    (time.perf_counter() - start) * 1000
                )
                start = time.perf_counter()
                layout = Layout(context=bpy.context)
                tape.play(layout)
                timings["rebuild_layout_ms"].append(
                    (time.perf_counter() - start) * 1000
                )
                layout.canvas.park()
            performance.update(
                {
                    key: {
                        "median": statistics.median(values[10:]),
                        "p95": sorted(values[10:])[85],
                    }
                    for key, values in timings.items()
                }
            )
            performance.update(
                samples=90,
                warmup=10,
                controls=len(state["canvas"].controls),
                ui_scale=bpy.context.preferences.system.ui_scale,
                scope="CPU authoring only; not GPU frame timing or BVT equivalence",
            )
            event("MOUSEMOVE", "NOTHING")
            event("LEFTMOUSE")
            event("LEFTMOUSE", "RELEASE")
        elif n == 4:
            assert bpy.context.scene.render.film_transparent != state["before"]
            c = current()["canvas"]
            assert c is not state["canvas"]
            assert (
                any(x.label == "Conditional output" for x in c.controls.values())
                == bpy.context.scene.render.film_transparent
            )
            checks.append(
                "Manual aliases and factory registration retain original classes; unchanged draw retains canvas; conditional rows rebuild automatically"
            )
            event("RIGHTMOUSE")
        elif n == 5:
            assert current()["canvas"].context_menu
            assert (
                current()["canvas"].context_menu.target.binding.context.name
                == "film_transparent"
            )
            event("ESC")
            a.unregister()
            assert a.LEGACY_MANUAL_PT_panel.draw is original
            assert b.LEGACY_FACTORY_PT_panel.is_registered
            a.register()
        elif n == 6:
            assert a.__beyond_ui_integration__.ui._runtime.running
            checks.append(
                "Exact-owner right click, restoration of original draw, isolated teardown and re-registration pass"
            )
            bpy.context.scene["beyond_ui_test_unsupported"] = True
            region.tag_redraw()
        elif n == 7:
            assert a.__beyond_ui_integration__.status["host"]["draw_errors"]
            assert not any(r["valid"] for r in host().records.values())
            del bpy.context.scene["beyond_ui_test_unsupported"]
            region.tag_redraw()
        elif n == 8:
            assert current()["valid"]
            assert not a.__beyond_ui_integration__.status["host"]["draw_errors"]
            region.active_panel_category = "legacy_loader"
        elif n == 9:
            loader = loader_module.__beyond_ui_integration__.ui._runtime
            assert any(
                r["valid"] for h in loader.hosts.values() for r in h.records.values()
            )
            checks.append(
                "Delegating module loader receives custom content; unsupported mode revokes stale input and recovers; direct native dialog routes are reported"
            )
            finish()
            return None
        state["stage"] += 1
        return 0.6
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
