"""Actual Uraraka N-panel screenshots with owned no-focus Blender windows."""

import bpy, gpu, os, sys, json, traceback, importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from capture_controls import png

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"])
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
OUT = Path(
    os.environ.get(
        "BEYOND_UI_STUDIO_EMBEDDED",
        str(ROOT / "docs/design/qa/camkeys-studio-v1/embedded"),
    )
)
OUT.mkdir(parents=True, exist_ok=True)
slugs = [
    "camkeys_main",
    "camkeys_linking",
    "auto_fov",
    "baking",
    "camprops",
    "lattice_auto_fov_modifier",
]
categories = {f"CAMKEYS_PT_{slug}": f"Studio {i}" for i, slug in enumerate(slugs)}
state = {"step": 0, "pending": None, "captures": []}
handle = None
register = bpy.utils.register_class


def fixture_register(cls):
    if cls.__name__ in categories:
        cls.bl_category = categories[cls.__name__]
        cls.bl_idname = cls.__name__ + "_STUDIO_QA"
        cls.bl_options = set(getattr(cls, "bl_options", set())) - {"DEFAULT_CLOSED"}
    return register(cls)


def capture():
    if bpy.context.region.as_pointer() != region.as_pointer() or not state["pending"]:
        return
    try:
        w, h = region.width, region.height
        fb = gpu.state.active_framebuffer_get()
        px = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
        px.dimensions = w * h * 4
        png(OUT / (state["pending"] + ".png"), w, h, bytes(px))
        state["captures"].append(state["pending"])
        state["pending"] = None
    except Exception:
        state["error"] = traceback.format_exc()


def finish(error=None):
    if handle:
        bpy.types.SpaceView3D.draw_handler_remove(handle, "UI")
    result = dict(
        passed=error is None,
        error=error,
        captures=state["captures"],
        version=bpy.app.version_string,
        scene=bpy.data.filepath,
        status=addon.__beyond_ui_integration__.status,
    )
    (OUT / "report.json").write_text(json.dumps(result, indent=2, default=str))
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2, default=str)
    )
    addon.unregister()
    bpy.ops.wm.quit_blender()


def tick():
    try:
        if state.get("error"):
            raise RuntimeError(state["error"])
        n = state["step"]
        i = n // 4
        phase = n % 4
        if i >= len(slugs):
            assert len(state["captures"]) == len(slugs) * 2, state["captures"]
            finish()
            return None
        if phase == 0:
            region.active_panel_category = categories["CAMKEYS_PT_" + slugs[i]]
            for _ in range(50):
                window.event_simulate(
                    type="WHEELUPMOUSE",
                    value="PRESS",
                    x=region.x + region.width - 20,
                    y=region.y + region.height // 2,
                )
        if phase == 1:
            state["pending"] = slugs[i] + "-top"
        if phase == 2:
            for _ in range(12):
                window.event_simulate(
                    type="WHEELDOWNMOUSE",
                    value="PRESS",
                    x=region.x + region.width - 20,
                    y=region.y + region.height // 2,
                )
        if phase == 3:
            state["pending"] = slugs[i] + "-lower"
        state["step"] += 1
        area.tag_redraw()
        return 0.8
    except Exception:
        finish(traceback.format_exc())
        return None


def setup_capture():
    global window, area, region, handle
    try:
        window = next(iter(bpy.context.window_manager.windows))
        area = max(
            (a for a in window.screen.areas if a.type == "VIEW_3D"),
            key=lambda a: a.width * a.height,
        )
        area.spaces.active.show_region_ui = True
        # Lattice panel is conditional and absent in this saved selection.
        slugs[:] = [slug for slug in slugs if slug != "lattice_auto_fov_modifier"]
        region = next(r for r in area.regions if r.type == "UI")
        handle = bpy.types.SpaceView3D.draw_handler_add(capture, (), "UI", "POST_PIXEL")
        bpy.app.timers.register(tick, first_interval=2)
    except Exception:
        finish(traceback.format_exc())
    return None


def start():
    global window, area, region, handle
    try:
        with patch.object(bpy.utils, "register_class", fixture_register):
            addon.register()
        bpy.ops.wm.open_mainfile(
            filepath=os.environ["BEYOND_UI_CRASH_FILE"], load_ui=True, use_scripts=False
        )
        bpy.context.window_manager.EnableCamKeys = False
        bpy.app.timers.register(setup_capture, first_interval=2)
    except Exception:
        finish(traceback.format_exc())
    return None


bpy.app.timers.register(start, first_interval=1)
