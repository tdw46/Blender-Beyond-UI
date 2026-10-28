"""Real window collection search, suggestions and component decorators."""

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
bpy.types.Scene.search_fixture = bpy.props.StringProperty()
for i in range(30):
    bpy.data.objects.new(f"Search Item {i:02}", None)


def build(key):
    ui = Layout(
        Canvas(menu_commit=commits.append),
        bpy.context,
        commit=lambda a, b: commits.append("POINTER"),
    )
    ui.prop_search(
        bpy.context.scene,
        "search_fixture",
        bpy.data,
        "objects",
        text="Collection Search",
        results_are_suggestions=True,
    )
    ui.prop_decorator(obj, "location")
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


def emit(kind, value="PRESS", where="widget", logical=None, **mods):
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
    del bpy.types.Scene.search_fixture
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
            c = control("widget")
            a, b, w, h = c.rect
            widget = c.options["widget"]
            state["point"] = lambda x, y: (
                a + x * w / widget.width,
                b + y * h / widget.height,
            )
            emit("LEFTMOUSE", logical=state["point"](150, 30))
            emit("LEFTMOUSE", "RELEASE", logical=state["point"](150, 30))
            emit("END")
            emit("RET")
        elif n == 2:
            w = control("widget").options["widget"]
            assert bpy.context.scene.search_fixture == w.items[-1][1], (
                bpy.context.scene.search_fixture,
                current()[1].menu_error,
            )
            assert len(commits) == 1
            emit("RIGHTMOUSE", logical=state["point"](40, 160))
            emit("RIGHTMOUSE", "RELEASE", logical=state["point"](40, 160))
        elif n == 3:
            c = current()[1]
            assert c.context_menu.target.part[0] == "row"
            assert [r.key for r in c.context_menu.page.rows] == [
                "SELECT_SEARCH",
                "COPY_NAME",
            ]
            emit("ESC")
        elif n == 4:
            emit("LEFTMOUSE", logical=state["point"](180, 100))
            emit("LEFTMOUSE", "RELEASE", logical=state["point"](180, 100))
            emit("Z", unicode="z")
            emit("Z", unicode="z")
            emit("RET")
        elif n == 5:
            assert bpy.context.scene.search_fixture == "zz", (
                bpy.context.scene.search_fixture,
                current()[1].menu_error,
            )
            assert len(commits) == 2
            emit("LEFTMOUSE", logical=state["point"](180, 100))
            emit("LEFTMOUSE", "RELEASE", logical=state["point"](180, 100))
            emit("X", unicode="x")
            emit("RIGHTMOUSE", logical=state["point"](180, 100))
            emit("RIGHTMOUSE", "RELEASE", logical=state["point"](180, 100))
        elif n == 6:
            assert bpy.context.scene.search_fixture == "zz"
            assert current()[1].context_menu is None
            assert current()[1].widget_capture is None
            emit("LEFTMOUSE", where="decorator")
            emit("LEFTMOUSE", "RELEASE", where="decorator")
        elif n == 7:
            decorators = [
                c for c in current()[1].controls.values() if c.kind == "decorator"
            ]
            assert [c.options["decorator"].state() for c in decorators] == [
                "KEYED",
                "EMPTY",
                "EMPTY",
            ]
            emit("RIGHTMOUSE", where="decorator")
            emit("RIGHTMOUSE", "RELEASE", where="decorator")
        elif n == 8:
            assert current()[1].context_menu.target.binding.context.index == 0
            emit("ESC")
        elif n == 9:
            c = current()[1]
            c.animation.enabled = False
            c.invalidate()
        elif n == 10:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual window End/Enter selects collection item with one commit",
                "Row right-click actions and arbitrary string suggestion entry",
                "Right-click cancels typed edit; standalone component decorator targets exact channel",
                "Host disable settles all motion and teardown releases ownership",
            ]
            finish(True)
            return None
        state["stage"] += 1
        area.tag_redraw()
        return 0.65
    except Exception:
        finish(False, traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
