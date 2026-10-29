"""Operator-choice parity in a disposable Blender profile."""

import bpy, os, sys, json, traceback, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Layout, Canvas, ShortcutRegistry
from beyond_ui.hosts import menu_native
from beyond_ui.layout import UnsupportedControl
from test_operator_enum import OperatorChoices
import operator_choices_fixture as fixture

fixture.register()
registry = None
try:
    assert (
        unittest.TextTestRunner()
        .run(unittest.defaultTestLoader.loadTestsFromTestCase(OperatorChoices))
        .wasSuccessful()
    )
    context = bpy.context
    config_count = len(context.window_manager.keyconfigs)
    ui = Layout(context=context)
    ui.operator_context = "EXEC_DEFAULT"
    ui.context_pointer_set("fixture_object", context.object)
    props = ui.operator_menu_enum("bui.choice", "choice")
    props.amount = 7
    dropdown = list(ui.canvas.controls.values())[-1]
    ui.operator_enum("bui.choice", "choice")
    button = next(c for c in ui.canvas.controls.values() if c.label == "Sphere")
    ui.canvas.arrange(560)
    clip = (0, 0, 560, 700)
    assert ui.canvas.open_operator_menu(dropdown, clip, context), ui.canvas.menu_error
    menu = ui.canvas.context_menu
    assert [r.label for r in menu.page.rows if r.heading] == ["Geometry", "Lighting"]
    assert not fixture.calls
    menu.choose(
        next(i for i, r in enumerate(menu.page.rows) if r.label == "Sphere"), context
    )
    assert fixture.calls[-1][:2] == ("B", 7)
    assert fixture.calls[-1][3] == context.object
    ui.canvas.close_context()
    button.action()
    assert fixture.calls[-1][:2] == ("B", 1)
    # Real command-copy context targets the selected enum, never a stale raw value.
    context.preferences.view.show_developer_ui = True
    rows = button.options["context_menu"](None, context)

    class CopyContext:
        # Keep the real RNA context/keyconfigs, but isolate the clipboard sink.
        window_manager = NS(clipboard="", keyconfigs=context.window_manager.keyconfigs)

        def __getattr__(self, name):
            return getattr(context, name)

    copy_context = CopyContext()
    next(r for r in rows if r.key == "COMMAND").action(None, copy_context)
    assert "choice='B'" in copy_context.window_manager.clipboard
    old_count = len(fixture.calls)
    ui.canvas.open_operator_menu(dropdown, clip, context)
    props.amount = 8
    ui.canvas.context_menu.choose(1, context)
    assert len(fixture.calls) == old_count
    ui.canvas.close_context()
    fixture.available = False
    button.action()
    assert len(fixture.calls) == old_count and ui.canvas.menu_error
    fixture.available = True
    long_props = ui.operator_menu_enum("bui.long_choice", "choice")
    long_props.count = 20
    long_control = list(ui.canvas.controls.values())[-1]
    ui.canvas.arrange(560)
    assert ui.canvas.open_operator_menu(long_control, clip, context), (
        ui.canvas.menu_error
    )
    assert (
        len(ui.canvas.context_menu.page.rows) == 20
        and ui.canvas.context_menu.page.search
    )
    ui.canvas.context_menu.event(
        NS(type="TEXTINPUT", value="PRESS", unicode="019"), 0, 0, context
    )
    assert len(ui.canvas.context_menu.page.rows) == 1
    ui.canvas.context_menu.choose(0, context)
    assert fixture.calls[-1] == ("I19", 1, 20)
    ui.canvas.close_context()
    # A dynamic numeric remap invalidates an already-open choice.
    ui.canvas.open_operator_menu(long_control, clip, context)
    original = fixture.long_items[0]
    fixture.long_items[0] = ("I0", "Action 000", "", 999)
    old_count = len(fixture.calls)
    ui.canvas.context_menu.choose(0, context)
    assert len(fixture.calls) == old_count and ui.canvas.menu_error
    fixture.long_items[0] = original
    ui.canvas.close_context()
    assert len(context.window_manager.keyconfigs) == config_count
    flags = Layout(context=context)
    flags.operator_context = "EXEC_DEFAULT"
    flags.operator_enum("bui.flag_choice", "choice")
    list(flags.canvas.controls.values())[1].action()
    assert fixture.calls[-1] == {"Y"}
    with patch.object(menu_native, "api", return_value=None):
        assert len(dropdown.options["operator_enum"].snapshot()) == 3
    for call in (
        lambda: ui.operator_enum("bui.choice", "choice", icon_only=True),
        lambda: ui.operator_menu_enum("bui.choice", "amount"),
    ):
        try:
            call()
            raise AssertionError("Unsupported request silently accepted")
        except (ValueError, UnsupportedControl):
            pass
    # Host-owned shortcut opens the custom popup, not an operator-native popup.
    registry = ShortcutRegistry("operator-enum-fixture")
    registry.register()
    c = Canvas(shortcut_registry=registry, shortcut_namespace="test")
    u = Layout(c, context)
    u.operator_menu_enum("bui.choice", "choice")
    control = next(iter(c.controls.values()))
    c.arrange(560)
    c.bind_shortcuts(context, clip)
    command = "test:" + control.key
    registry.dispatch(command, context)
    assert c.context_menu and c.context_menu.page.rows[1].label == "Cube"
    c.close_context()
    c.open_context(control, 10, 10, clip, context=context)
    assert c.context_menu.page.rows[0].label == "Shortcut to Open Menu"
    c.visible = False
    assert registry.dispatch(command, context) == {"CANCELLED"}
    registry.close()
    registry = None
    invoke_ui = Layout(context=context)
    invoke_ui.operator_enum("bui.choice", "choice")
    next(c for c in invoke_ui.canvas.controls.values() if c.kind == "button").action()
    assert fixture.calls[-2] == "INVOKED"
    # Right-click nested choices retain all 200 entries and shared search.
    long_props.count = 200
    ui.canvas.open_context(long_control, 10, 10, clip, context=context)
    ui.canvas.context_menu.choose(0, context)
    assert len(ui.canvas.context_menu.page.rows) == 201
    ui.canvas.close_context()
    # A selection change must not redirect an already-open operator action.
    ui.canvas.open_operator_menu(dropdown, clip, context)
    other = bpy.data.objects.new("Temporary operator selection", None)
    context.scene.collection.objects.link(other)
    try:
        other.select_set(True)
        old_count = len(fixture.calls)
        ui.canvas.context_menu.choose(1, context)
        assert (
            len(fixture.calls) == old_count
            and "selection changed" in ui.canvas.menu_error
        )
    finally:
        bpy.data.objects.remove(other, do_unlink=True)
        ui.canvas.close_context()
    # Removing/re-registering an operator revokes old controls.
    bpy.utils.unregister_class(fixture.BUI_OT_choice)
    button.action()
    assert ui.canvas.menu_error
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Expanded and dropdown actions use exact enum arguments, context overrides and invocation",
            "Dynamic menus are searchable and use supplied operator arguments; scratch keyconfigs are released",
            "Stale arguments, numeric remaps, selection changes, poll failures and removed operators reject execution",
            "Flag choices pass singleton sets; public static fallback remains available",
            "Choice right-click command contains selected value; host shortcuts open custom popup and revoke hidden controls",
            "Unsupported icon-only and non-enum requests fail explicitly",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
finally:
    if registry:
        registry.close()
    fixture.unregister()
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("OPERATOR_ENUM_RUNTIME", result)
if not bpy.app.background:
    bpy.app.timers.register(
        lambda: (bpy.ops.wm.quit_blender(), None)[1], first_interval=0.2
    )
