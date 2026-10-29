"""Real window non-ID pointer/search popovers and immediate typing."""

import bpy, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from non_id_fixture import selection_transaction
from beyond_ui import Layout, Canvas, PointerItems

spec = importlib.util.spec_from_file_location("pointer_demo", ROOT / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
obj = bpy.context.object
commits = []
tree = bpy.data.node_groups.new("WindowPointers", "ShaderNodeTree")
for i in range(30):
    node = tree.nodes.new("ShaderNodeValue")
    node.name = f"Node {i:02}"
tree.nodes.active = tree.nodes[0]
revision = [0]


def build(key):
    ui = Layout(
        Canvas(menu_commit=commits.append),
        bpy.context,
        commit=lambda a, b: commits.append("POINTER"),
    )
    ui.pointer_sources = lambda o, p: PointerItems(
        lambda: tree.nodes,
        revision=lambda: revision[0],
        transaction=selection_transaction,
    )
    ui.title(text="Non-ID Pointers")
    ui.prop(tree.nodes, "active", text="Active Node")
    ui.prop_search(tree.nodes, "active", tree, "nodes", text="Find Node")
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
            assert tree.nodes.active.name == "Node 29"
            assert len(commits) == 1
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 4:
            emit("TWO", unicode="2")
            emit("RET")
        elif n == 5:
            assert tree.nodes.active.name == "Node 02" and len(commits) == 2
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 6:
            _, c = current()
            a, b, w, h = c.overlay["rect"]
            widget = c.overlay["widget"]
            point = (a + 40 * w / widget.width, b + 160 * h / widget.height)
            emit("RIGHTMOUSE", logical=point)
            emit("RIGHTMOUSE", "RELEASE", logical=point)
        elif n == 7:
            menu = current()[1].context_menu
            assert menu is not None and menu.target.part[0] == "row"
            emit("ESC")
        elif n == 8:
            emit("ESC")
        elif n == 9:
            assert current()[1].overlay is None
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 10:
            emit("X", unicode="x")
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif n == 11:
            c = current()[1]
            assert c.overlay is None and c.context_menu is None
            assert tree.nodes.active.name == "Node 02"
            emit("LEFTMOUSE", where="search")
            emit("LEFTMOUSE", "RELEASE", where="search")
        elif n == 12:
            assert current()[1].overlay["owner"].kind == "search"
            emit("HOME", where="search")
            emit("RET", where="search")
        elif n == 13:
            assert tree.nodes.active.name == "Node 00" and len(commits) == 3
            emit("RIGHTMOUSE", where="search")
            emit("RIGHTMOUSE", "RELEASE", where="search")
        elif n == 14:
            assert current()[1].context_menu.target.binding.context.name == "active"
            emit("ESC")
            c = current()[1]
            c.animation.enabled = False
            c.invalidate()
        elif n == 15:
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual click opens non-ID pointer with shared strong glass",
                "End/Enter and immediate typed node selection commit once and close",
                "Candidate context, Escape and right-click cancellation",
                "Motion disable and teardown leave no timers",
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
