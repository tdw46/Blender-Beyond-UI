"""Read-only source-file startup regression in an isolated CamKeys test profile."""

import bpy, importlib.util, os, sys, json, traceback
from pathlib import Path

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"]).resolve()
assert (source / "__init__.py").is_file(), source
scene_path = Path(os.environ["BEYOND_UI_CRASH_FILE"]).resolve()
assert scene_path.is_file()
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
state = {"refreshes": 0}


def finish(error=None):
    result = dict(
        passed=error is None,
        error=error,
        version=bpy.app.version_string,
        refreshes=state["refreshes"],
        scene_loaded=bpy.data.filepath == str(scene_path),
        objects=len(bpy.data.objects),
        status=addon.__beyond_ui_integration__.status,
    )
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2, default=str)
    )
    # No save or preference writes. Quit only this disposable process.
    bpy.ops.wm.quit_blender()


def refresh():
    try:
        addon.viewport_navigation.refresh_keymaps(force=True)
        keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
            name="3D View", space_type="VIEW_3D"
        )
        for macro, _native in addon.viewport_navigation._macros.values():
            item = keymap.keymap_items.new(macro.bl_idname, "F8", "PRESS")
            child = item.properties.CAMKEYS_OT_begin_dolly_navigation
            child.source_id = 99
            child.source_signature = "fixture"
            assert child.source_id == 99
            keymap.keymap_items.remove(item)
        state["refreshes"] += 1
        if state["refreshes"] < 5:
            return 2.0
        dependencies = addon.__beyond_ui_integration__.status["popups"][
            "preserved_macro_dependencies"
        ]
        assert len(dependencies) >= 6, dependencies
        assert bpy.data.filepath == str(scene_path)
        finish()
    except Exception:
        finish(traceback.format_exc())
    return None


def start():
    try:
        addon.register()
        bpy.ops.wm.open_mainfile(
            filepath=str(scene_path), load_ui=True, use_scripts=False
        )
        bpy.app.timers.register(refresh, first_interval=3.0)
    except Exception:
        finish(traceback.format_exc())
    return None


bpy.app.timers.register(start, first_interval=1.0)
