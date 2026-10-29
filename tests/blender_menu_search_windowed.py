"""Real window typing, search selection and unchanged owner context menus."""

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
bpy.types.Scene.followup_flags = bpy.props.EnumProperty(
    items=[("A", "Alpha", "", 1), ("B", "Beta", "", 2)],
    options={"ENUM_FLAG"},
    default={"A"},
)
bpy.types.Scene.search_window = bpy.props.EnumProperty(
    items=[(f"I{i}", f"Choice {i:03}", "Choice tooltip") for i in range(200)]
)


def build(key):
    ui = Layout(
        Canvas(menu_commit=commits.append),
        bpy.context,
        commit=lambda a, b: commits.append("POINTER"),
    )
    ui.title(text="Enum Properties")
    ui.prop(bpy.context.scene, "search_window", text="Mode")
    ui.prop(bpy.context.scene, "followup_flags")
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


def emit(kind, value="PRESS", where="enum", logical=None, **mods):
    record, canvas = current()
    c = where if not isinstance(where, str) else control(where)
    a, b, w, h = c.rect
    lx, ly = logical or (a + w / 2, b + h / 2)
    rx, ry, rw, rh = record["rect"]
    x = int(region.x + rx + lx * rw / canvas._width)
    y = int(region.y + ry + rh - ly * rh / canvas.height)
    window.event_simulate(type=kind, value=value, x=x, y=y, **mods)


def finish(passed, error=""):
    demo.unregister()
    del bpy.types.Scene.search_window
    del bpy.types.Scene.followup_flags
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
            assert c.context_menu is not None, c.menu_error
            assert len(c.context_menu.page.rows) == 200
            assert r["backdrop"] is not None
            from beyond_ui.gpu import glass

            assert glass._owners[r["backdrop"]]["strong_productions"] > 0
            assert c.context_menu.page.search is not None
            for digit in "199":
                emit("ONE", unicode=digit)
        elif n == 3:
            _, c = current()
            assert [r.key for r in c.context_menu.page.rows] == ["enum:I199"]
            assert bpy.context.scene.search_window == "I0" and not commits
            emit("RET")
        elif n == 4:
            _, c = current()
            assert c.context_menu is None
            assert bpy.context.scene.search_window == "I199" and len(commits) == 1
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 5:
            assert current()[1].context_menu.page.highlight == 199
            emit("HOME")
            emit("ESC")
        elif n == 6:
            assert bpy.context.scene.search_window == "I199" and len(commits) == 1
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif n == 7:
            menu = current()[1].context_menu
            assert (
                menu is not None and menu.target.binding.context.name == "search_window"
            )
            emit("ESC")
        elif n == 8:
            emit("LEFTMOUSE")
            emit("LEFTMOUSE", "RELEASE")
        elif n == 9:
            emit("X", unicode="z")
        elif n == 10:
            assert current()[1].context_menu.page.rows[0].label == "No matches"
            emit("RIGHTMOUSE")
            emit("RIGHTMOUSE", "RELEASE")
        elif n == 11:
            assert len(current()[1].context_menu.page.rows) == 200
            emit("RIGHTMOUSE")
        elif n == 12:
            c = current()[1]
            assert c.context_menu is None
            assert bpy.context.scene.search_window == "I199"
            c.animation.enabled = False
            c.invalidate()
        elif n == 13:
            buttons = [b for b in current()[1].controls.values() if b.kind == "button"]
            state["buttons"] = buttons
            emit("LEFTMOUSE", where=buttons[1])
            emit("LEFTMOUSE", "RELEASE", where=buttons[1])
        elif n == 14:
            assert bpy.context.scene.followup_flags == {"B"}
            emit("LEFTMOUSE", where=state["buttons"][0], shift=True)
            emit("LEFTMOUSE", "RELEASE", where=state["buttons"][0], shift=True)
        elif n == 15:
            assert bpy.context.scene.followup_flags == {"A", "B"}
            assert not demo._host._animation_keys and not demo._host._tooltip_keys
            assert not demo._host.bridge.errors, demo._host.bridge.errors
            state["checks"] = [
                "Actual click opens 200-choice shared strong-glass enum menu",
                "Actual Unicode typing filters 200 choices; Enter commits the exact original item once",
                "No-match state and right-click clear then dismissal preserve the property",
                "Reopening reveals current choice; Escape and right-click cancel",
                "Resting right-click retains exact property context",
                "Actual expanded flag clicks distinguish plain exclusive and Shift toggle",
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
