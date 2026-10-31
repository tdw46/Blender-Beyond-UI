"""Read a COPY of saved preferences, then verify the installed CamKeys entry point."""

import bpy, json, os, sys, traceback
from pathlib import Path


def run():
    result = {}
    try:
        # Loading preferences normally also reloads every enabled addon. Keep this
        # disposable probe scoped to CamKeys instead of importing unrelated plugins.
        import addon_utils
        from unittest.mock import patch

        with patch.object(addon_utils, "enable", lambda *a, **kw: None):
            bpy.ops.wm.read_userpref()
        name = "bl_ext.user_default.CamKeys"
        assert name in bpy.context.preferences.addons
        import addon_utils

        # Factory startup initialized a temporary extension namespace before reading
        # the saved profile. Point this test namespace at the actual canonical repo.
        import importlib

        namespace = importlib.import_module("bl_ext.user_default")
        namespace.__path__.append(
            "/Users/tylerwalker/Documents/Blender/extensions/user_default"
        )
        importlib.invalidate_caches()
        errors = []
        addon_utils.enable(
            name,
            default_set=False,
            handle_error=lambda: errors.append(traceback.format_exc()),
        )
        assert not errors, errors
        module = sys.modules[name]
        expected = Path(
            "/Users/tylerwalker/Documents/Blender/extensions/user_default/CamKeys/__init__.py"
        )
        assert Path(module.__file__).resolve() == expected
        state = module.__beyond_ui_integration__.status
        assert state["state"] == "registered", state
        assert addon_utils.check(name) == (True, True)
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            saved_preference_enabled=True,
            loaded_file=str(expected),
            single_line_integration=True,
            status=state,
            profile=bpy.utils.user_resource("CONFIG"),
        )
        addon_utils.disable(name, default_set=False)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2, default=str)
    )
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=1)
