"""Real window navigation of pointer popovers and component decorators."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout, Canvas

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
obj = bpy.context.object
commits = []


def build(key):
    ui = Layout(
        Canvas(menu_commit=commits.append),
        bpy.context,
        commit=lambda a, b: commits.append("POINTER"),
    )
    ui.title(text="Pointers and Decorators")
    ui.prop(obj, "parent", text="Parent")
    ui.use_property_split = True
    ui.prop(obj, "location", index=0, text="Position X")
    for i in range(13):
        ui.label(text="")
    return ui.canvas


demo.build_canvas = build
demo.register()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
state = {"stage": 0, "checks": []}


def current():
    r = next(r for r in demo._host.records.values() if r["valid"])
    return r, r["canvas"]


def control(kind):
    return next(c for c in current()[1].controls.values() if c.kind == kind)


def emit(kind, value="PRESS", where="pointer", logical=None, **mods):
    record, canvas = current()
    c = control(where)
    a, b, w, h = c.rect
    lx, ly = logical or (a + w / 2, b + h / 2)
    rx, ry, rw, rh = record["rect"]
    x = int(region.x + rx + lx * rw / canvas._width)
    y = int(region.y + ry + rh - ly * rh / canvas.height)
    window.event_simulate(type=kind, value=value, x=x, y=y, **mods)


def finish(passed, error=""):
    demo.unregister()
    result = dict(
        passed=passed,
        error=error,
        version=bpy.app.version_string,
        checks=state["checks"],
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("POINTER_WINDOWED", result, flush=True)
    bpy.ops.wm.quit_blender()


def tick():
    try:
        n = state["stage"]
        if n == 0:
            region.active_panel_category = "Beyond UI"
        elif n == 1:
            assert demo._host.bridge is not None, demo._host.reason
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.beyonduidemo.input("INVOKE_DEFAULT")
            emit("MOUSEMOVE", "NOTHING")
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 2:
            r, c = current()
            assert c.overlay is not None, c.menu_error
            widget = c.overlay["widget"]
            state["expected"] = widget.items[-1][0]
            assert r["backdrop"] is not None
            from beyond_ui.gpu import glass

            owner = glass._owners[r["backdrop"]]
            assert owner["strong_productions"] > 0
            emit("END")
            emit("RET")
        elif n == 3:
            _, c = current()
            assert c.overlay is None, c.menu_error
            assert obj.parent.as_pointer() == state["expected"] and commits == [
                "POINTER"
            ]
            state["checks"].append(
                "Real click opens shared strong-glass picker; End/Enter selects exact ID with one host commit"
            )
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 4:
            _, c = current()
            a, b, w, h = c.overlay["rect"]
            widget = c.overlay["widget"]
            emit(
                "RIGHTMOUSE",
                logical=(a + 40 * w / widget.width, b + 160 * h / widget.height),
            )
            emit("RIGHTMOUSE", "RELEASE")
        elif n == 5:
            _, c = current()
            assert c.context_menu is not None, c.menu_error
            assert (
                c.context_menu.target.part[0] == "row"
                and c.context_menu.target.binding is None
            )
            emit("ESC")
        elif n == 6:
            emit("ESC")
        elif n == 7:
            _, c = current()
            assert c.overlay is None
            emit("LEFTMOUSE", where="decorator")
            emit("LEFTMOUSE", "RELEASE", where="decorator")
        elif n == 8:
            assert control("decorator").options["decorator"].state() == "KEYED", (
                current()[1].menu_error
            )
            assert "KEY" in commits
            emit("RIGHTMOUSE", where="decorator")
            emit("RIGHTMOUSE", "RELEASE", where="decorator")
        elif n == 9:
            _, c = current()
            assert c.context_menu.target.binding.context.index == 0
            emit("ESC")
        elif n == 10:
            emit("LEFTMOUSE", where="decorator")
            emit("LEFTMOUSE", "RELEASE", where="decorator")
        elif n == 11:
            _, c = current()
            assert control("decorator").options["decorator"].state() == "EMPTY"
            c.animation.enabled = False
            c.invalidate()
            state["checks"].append(
                "Candidate row context, Escape dismissal and exact component decorator insert/delete/context menu"
            )
        elif n == 12:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"].append(
                "Host disable/invalidation settles all motion and teardown releases ownership"
            )
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.65
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
