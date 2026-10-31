"""Actual integrated CamKeys N-panel captures in a disposable no-focus window."""

import bpy, gpu, importlib.util, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from capture_controls import png

source = Path("/Users/tylerwalker/dev/CamKeys-beyond-ui")
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
from unittest.mock import patch

register_class = bpy.utils.register_class


def register_fixture(cls):
    if cls.__name__ == "CAMKEYS_PT_auto_fov":
        cls.bl_category = "Forced QA"
    return register_class(cls)


with patch.object(bpy.utils, "register_class", register_fixture):
    addon.register()
scene = bpy.context.scene
for name in ("Hero mesh", "Hair strands", "Jacket folds", "Accessories")[
    : int(os.environ.get("BEYOND_UI_LIST_COUNT", "4"))
]:
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    scene.collection.objects.link(obj)
    item = scene.mesh_object_items.add()
    item.object = obj
if os.environ.get("BEYOND_UI_EMPTY_POINTERS"):
    scene.camera = None
    for item in scene.mesh_object_items:
        item.object = None
scene.mesh_object_items_index = 0
item = scene.mesh_object_items[0]
item["auto_fov_enabled"] = True
item.object.name = "Face"
item["auto_fov_focus_object"] = item.object

ids = addon.__beyond_ui_integration__.list_ids
try:
    ids.prepare(scene, "mesh_object_items")
except Exception:
    ids.flush()
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
area.spaces.active.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
OUT = Path(os.environ["BEYOND_UI_EMBEDDED_CAPTURE"])
OUT.mkdir(parents=True, exist_ok=True)
state = {"step": 0, "captures": [], "pending": None}


def capture():
    if bpy.context.region.as_pointer() != region.as_pointer() or not state["pending"]:
        return
    try:
        fb = gpu.state.active_framebuffer_get()
        w, h = region.width, region.height
        pixels = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
        pixels.dimensions = w * h * 4
        name = state["pending"]
        png(OUT / (name + ".png"), w, h, bytes(pixels))
        state["captures"].append(name)
        state["pending"] = None
    except Exception:
        state["error"] = traceback.format_exc()


handle = bpy.types.SpaceView3D.draw_handler_add(capture, (), "UI", "POST_PIXEL")


def finish(error=None):
    bpy.types.SpaceView3D.draw_handler_remove(handle, "UI")
    runtime = addon.__beyond_ui_integration__.ui._runtime
    records = []
    for cls, host in runtime.hosts.items():
        for record in host.records.values():
            canvas = record["canvas"]
            records.append(
                dict(
                    panel=cls.__name__,
                    width=canvas._width,
                    height=canvas.height,
                    rect=record["rect"],
                    glass=record.get("backdrop") is not None,
                    controls=[
                        dict(
                            kind=c.kind,
                            label=c.label,
                            rect=c.rect,
                            icon=c.options.get("icon"),
                        )
                        for c in canvas.controls.values()
                    ],
                )
            )
    result = dict(
        passed=not error,
        error=error,
        captures=state["captures"],
        owner_context_verified=state.get("owner_context_verified", False),
        version=bpy.app.version_string,
        records=records,
        status=addon.__beyond_ui_integration__.status,
    )
    addon.unregister()
    (OUT / "capture.json").write_text(json.dumps(result, indent=2, default=str))
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2, default=str)
    )
    bpy.ops.wm.quit_blender()


def focal_context():
    runtime = addon.__beyond_ui_integration__.ui._runtime
    host = next(
        h for cls, h in runtime.hosts.items() if cls.__name__ == "CAMKEYS_PT_auto_fov"
    )
    record = next(r for r in host.records.values() if r.get("rect"))
    canvas = record["canvas"]
    c = next(c for c in canvas.controls.values() if c.label == "Apparent Focal Length")
    x, y, w, h = record["rect"]
    a, b, cw, ch = c.rect
    px = int(region.x + x + (a + cw * 0.6) * w / canvas._width)
    py = int(region.y + y + h - (b + ch * 0.75) * h / canvas.height)
    state["context_canvas"] = canvas
    state["context_key"] = c.key
    for value in ("PRESS", "RELEASE"):
        window.event_simulate(type="RIGHTMOUSE", value=value, x=px, y=py)


def tick():
    try:
        n = state["step"]
        if state.get("error"):
            raise RuntimeError(state["error"])
        runtime = addon.__beyond_ui_integration__.ui._runtime
        assert not runtime.errors, runtime.errors
        if n == 0:
            region.active_panel_category = "Forced QA"
        if n in (3, 5, 7, 10, 13, 16):
            state["pending"] = {
                3: "idle",
                5: "hover",
                7: "settled",
                10: "context",
                13: "dismissed",
                16: "scrolled",
            }[n]
        if n == 5:
            window.event_simulate(
                type="MOUSEMOVE",
                value="NOTHING",
                x=region.x + 100,
                y=region.y + region.height - 150,
            )
        if n in (7, 9, 12):
            window.event_simulate(
                type="MOUSEMOVE", value="NOTHING", x=area.x + 50, y=area.y + 50
            )
        if n == 8:
            focal_context()
        if n == 10:
            owner = state["context_canvas"].context_focus
            assert owner is not None and owner.key == state["context_key"]
            state["owner_context_verified"] = True
        if n == 11:
            window.event_simulate(type="ESC", value="PRESS")
            window.event_simulate(type="ESC", value="RELEASE")
        if n == 14:
            for _ in range(8):
                window.event_simulate(
                    type="WHEELDOWNMOUSE",
                    value="PRESS",
                    x=region.x + region.width - 20,
                    y=region.y + region.height // 2,
                )
        if n >= 18:
            assert len(state["captures"]) == 6, state
            finish()
            return None
        area.tag_redraw()
        state["step"] += 1
        return 0.6
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
