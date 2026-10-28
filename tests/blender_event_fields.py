"""Disposable RNA event property capture through the production Canvas/menu."""

import bpy, json, os, sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Layout, UnsupportedControl
from beyond_ui.event_field import event_types


def ev(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


def run():
    ctx = bpy.context
    wm = ctx.window_manager
    config = wm.keyconfigs.new("Beyond event fields fixture")
    checks = []
    try:
        km = config.keymaps.new("Beyond event fields", space_type="EMPTY")
        item = km.keymap_items.new("wm.context_toggle", "F5", "RELEASE")
        item.properties.data_path = "scene.render.use_file_extension"
        commits = []
        ui = Layout(
            context=ctx, commit=lambda before, after: commits.append((before, after))
        )
        control = ui.prop(item, "type", full_event=True, text="Shortcut")
        plain = ui.prop(item, "type", event=True, text="Key")
        canvas = ui.canvas
        canvas.arrange(560)
        clip = (0, 0, 560, 560)

        def open_field(control=control, mode=1):
            x, y, w, h = control.rect
            canvas.event(ev("LEFTMOUSE"), x + 40, y + 10, clip, context=ctx)
            assert canvas.context_menu is not None, canvas.menu_error
            canvas.context_menu.choose(mode, ctx)
            assert canvas.context_menu.capture_row is not None, (
                canvas.context_menu.error
            )
            return x + 40, y + 10

        x, y = open_field()
        assert item.type == "F5"
        canvas.event(ev("LEFT_SHIFT"), x, y, clip, context=ctx)
        assert item.type == "F5"
        canvas.event(ev("F8", ctrl=True, shift=True), x, y, clip, context=ctx)
        assert (
            item.type == "F8"
            and item.ctrl == 1
            and item.shift == 1
            and item.value == "RELEASE"
        ), (item.type, canvas.menu_error)
        assert len(commits) == 1 and isinstance(commits[0][0], dict)
        assert control.options["event_field"].format(item.type) == item.to_string()
        checks.append(
            "full-event captures keyboard modifiers, preserves activation value and commits the chord once"
        )
        x, y = open_field()
        before = control.options["event_field"].snapshot()
        canvas.event(ev("RIGHTMOUSE"), x, y, clip, context=ctx)
        assert control.options["event_field"].snapshot() == before
        canvas.close_context()
        assert canvas.open_context(control, x, y, clip, context=ctx)
        assert canvas.context_menu.target.binding.context.owner() == item
        canvas.close_context()
        x, y = open_field()
        item.ctrl = 0
        canvas.event(ev("F7"), x, y, clip, context=ctx)
        assert item.type == "F8"
        canvas.close_context()
        checks.append(
            "right-click cancellation, exact RNA context target and stale modifier rejection"
        )
        x, y = open_field(plain)
        canvas.event(ev("F6", alt=True), x, y, clip, context=ctx)
        assert item.type == "F6" and not item.alt and item.shift == 1
        checks.append(
            "event-only capture changes the key without changing modifier properties"
        )
        x, y = open_field(mode=2)
        canvas.event(ev("MIDDLEMOUSE"), x, y, clip, context=ctx)
        assert item.type == "MIDDLEMOUSE" and item.map_type == "MOUSE", (
            item.type,
            canvas.menu_error,
        )
        x, y = open_field(mode=3)
        canvas.event(ev("B"), x, y, clip, context=ctx)
        canvas.event(ev("F9"), x, y, clip, context=ctx)
        assert item.type == "F9" and item.key_modifier == "B", (
            item.type,
            canvas.menu_error,
        )
        checks.append(
            "explicit mouse mode and held-key chord mode use shared capture navigation"
        )
        collision = km.keymap_items.new(
            "wm.context_toggle", "F10", "RELEASE", ctrl=True
        )
        x, y = open_field()
        before = control.options["event_field"].snapshot()
        canvas.event(ev("F10", ctrl=True), x, y, clip, context=ctx)
        assert canvas.menu_error and control.options["event_field"].snapshot() == before
        canvas.close_context()
        km.keymap_items.remove(collision)

        def reject(before, after):
            raise RuntimeError("reject host commit")

        control.binding.commit = reject
        x, y = open_field()
        before = control.options["event_field"].snapshot()
        canvas.event(ev("F11", alt=True), x, y, clip, context=ctx)
        assert (
            canvas.menu_error == "reject host commit"
            and control.options["event_field"].snapshot() == before
        ), canvas.menu_error
        canvas.close_context()
        checks.append(
            "existing chord collisions and failed host commits leave the entire keymap item unchanged"
        )
        x, y = open_field()
        km.keymap_items.remove(item)
        canvas.event(ev("F12"), x, y, clip, context=ctx)
        assert canvas.context_menu is None
        checks.append(
            "deleted keymap owner revokes capture without redirecting the edit"
        )
        try:
            ui.prop(ctx.scene.render, "resolution_percentage", full_event=True)
        except UnsupportedControl:
            pass
        else:
            raise AssertionError("Unsupported full-event owner accepted")
        # Standalone integer event storage, no keymap assignment.
        bpy.types.Scene.beyond_event_code = bpy.props.IntProperty()
        try:
            standalone = Layout(context=ctx)
            c = standalone.prop(ctx.scene, "beyond_event_code", event=True)
            standalone.canvas.arrange(560)
            standalone.canvas.event(ev("LEFTMOUSE"), 20, 20, clip, context=ctx)
            standalone.canvas.context_menu.choose(1, ctx)
            standalone.canvas.event(ev("F8"), 20, 20, clip, context=ctx)
            assert ctx.scene.beyond_event_code == event_types()["F8"][0]
        finally:
            del bpy.types.Scene.beyond_event_code
        checks.append(
            "standalone integer event properties retain native event codes; unsupported full-event owners fail explicitly"
        )
    finally:
        wm.keyconfigs.remove(config)
    result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("EVENT_FIELDS", json.dumps(result))


run()
