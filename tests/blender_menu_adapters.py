"""Menu adapter semantics in a disposable, windowed Blender process."""

import bpy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target
from beyond_ui.hosts import menu_native as native
from beyond_ui.context_paths import owner_path


def run():
    ctx = bpy.context
    checks = []
    commits = []
    obj = ctx.active_object
    binding = rna_binding(lambda: obj, "location", index=1, source=run)
    source = binding.context
    target = Target(
        "location", binding=binding, valid=source.valid, commit=commits.append
    )

    def execute(key, src=source, tgt=target):
        rows = src.entries(tgt, ctx)
        menu = Menu(tgt, rows, (0, 0), (0, 0, 640, 800), context=ctx)
        idx = next(i for i, row in enumerate(rows) if row.key == key)
        assert menu.page.available[idx], (key, menu.error, native.reason())
        menu.choose(idx, ctx)
        assert menu.closed and menu.error is None, (key, menu.error)

    assert native.api() is not None, native.reason()
    driver = obj.driver_add("location", 1)
    driver.driver.expression = "2.5"
    execute("COPY_DRIVER")
    driver.driver.expression = "9.0"
    execute("PASTE_DRIVER")
    assert native.curve(source).driver.expression == "2.5"
    assert len(obj.animation_data.drivers) == 1
    assert commits[-1] == "PASTE_DRIVER"
    assert not any(
        o.name.startswith("Beyond UI driver clipboard staging")
        for o in bpy.data.objects
    )
    checks.append(
        "real native driver clipboard preserves expression and replaces exact component"
    )

    def reject(action):
        raise RuntimeError("undo rejected")

    denied = Target("location", binding=binding, valid=source.valid, commit=reject)
    native.curve(source).driver.expression = "7.0"
    try:
        native.driver_apply("PASTE_DRIVER", source, denied)
        raise AssertionError("expected rollback")
    except RuntimeError as error:
        assert str(error) == "undo rejected"
    assert native.curve(source).driver.expression == "7.0"
    assert len(obj.animation_data.drivers) == 1
    checks.append(
        "host undo failure restores complete previous driver and removes staging ID"
    )
    no_undo = Target("location")
    assert not native.driver_enabled("PASTE_DRIVER", source, no_undo)
    assert not native.driver_enabled(
        "NATIVE_DRIVER", source.component(0).__class__(lambda: obj, "location"), target
    )
    execute("NATIVE_DRIVER")
    receiver_obj = bpy.data.objects.new("Driver receiver", None)
    receiver = rna_binding(lambda: receiver_obj, "scale", index=2).context
    execute("PASTE_DRIVER", receiver, target)
    copied = native.curve(receiver)
    variable = copied.driver.variables[0]
    assert (
        variable.targets[0].id == obj and variable.targets[0].data_path == "location[1]"
    )
    readonly = rna_binding(lambda: obj, "users").context
    assert native.driver_enabled("NATIVE_DRIVER", readonly, target)
    assert not native.driver_enabled("PASTE_DRIVER", readonly, target)
    checks.append(
        "new-driver clipboard uses exact ID/path; readonly input and unsupported whole-array guards"
    )

    with ctx.temp_override(
        area=next(a for a in ctx.screen.areas if a.type == "VIEW_3D")
    ):
        assert owner_path(source, ctx) in {"object", "active_object"}
        execute("FAVORITE")
        functions = native.api()
        menu = functions["favorites"](ctx.as_pointer())
        args = (menu + 88, owner_path(source, ctx).encode(), b"location", 1)
        first = functions["find_property"](*args)
        assert first
        execute("FAVORITE")
        assert functions["find_property"](*args) == first
        assert ctx.preferences.is_dirty
        other = bpy.data.objects.new("Unlinked owner", None)
        assert owner_path(rna_binding(lambda: other, "location").context, ctx) is None
        bpy.data.objects.remove(other)
        checks.append(
            "real native Quick Favorites stores exact property/component idempotently; unrelated owner rejected"
        )
        from beyond_ui.context_shortcuts import Action, property_entry
        from beyond_ui.context_extensions import operator_entries

        config_count = len(ctx.window_manager.keyconfigs)
        props = {"data_path": "object.show_name"}
        native.add_operator_favorite("wm.context_toggle", props, "INVOKE_DEFAULT", ctx)
        native.add_operator_favorite("wm.context_toggle", props, "INVOKE_DEFAULT", ctx)
        assert len(ctx.window_manager.keyconfigs) == config_count
        checks.append(
            "real operator favorite copies typed arguments; temporary configuration is always released"
        )

        def event(kind, **modifiers):
            return SimpleNamespace(type=kind, value="PRESS", **modifiers)

        action = Action("wm.context_toggle", props, ctx)
        assert action.name == "Window", action.name
        km = action.keymap(ctx)
        before_count = len(km.keymap_items)
        row = action.entry(ctx)
        capture = Menu(target, (row,), (0, 0), (0, 0, 640, 800), context=ctx)
        capture.choose(0, ctx)
        assert capture.capture_row is not None and len(capture.parents) == 1
        capture.event(event("LEFT_SHIFT", shift=True), 4, 4, ctx)
        assert capture.capture_row is not None and len(km.keymap_items) == before_count
        capture.event(event("ESC"), 4, 4, ctx)
        assert capture.capture_row is None and len(km.keymap_items) == before_count
        capture.choose(0, ctx)
        capture.event(event("F19", shift=True, ctrl=True, alt=True), 4, 4, ctx)
        assert capture.closed and capture.error is None, capture.error
        assert len(km.keymap_items) == before_count + 1
        action = Action("wm.context_toggle", props, ctx)
        _, item = action.current(ctx)
        assert item.type == "F19" and item.shift and item.ctrl and item.alt
        assert item.properties.data_path == "object.show_name"
        old = obj.show_name
        bpy.ops.wm.context_toggle(data_path=item.properties.data_path)
        assert obj.show_name != old
        obj.show_name = old
        blocker = km.keymap_items.new("wm.context_toggle", "F18", "PRESS")
        blocker.properties.data_path = "object.show_in_front"
        capture = Menu(
            target, (action.entry(ctx),), (0, 0), (0, 0, 640, 800), context=ctx
        )
        capture.choose(0, ctx)
        capture.choose(1, ctx)
        capture.event(event("F18"), 4, 4, ctx)
        assert not capture.closed and "already used" in capture.error
        assert item.type == "F19"
        capture.event(event("F17", ctrl=True), 4, 4, ctx)
        assert capture.closed and item.type == "F17" and item.ctrl and not item.alt
        km.keymap_items.remove(blocker)
        action = Action("wm.context_toggle", props, ctx)
        item.type = "F16"
        assert not action.enabled(target, ctx)
        action = Action("wm.context_toggle", props, ctx)
        action.remove(target, ctx)
        assert len(km.keymap_items) == before_count
        toggle = rna_binding(lambda: obj, "show_name").context
        assert property_entry(toggle, ctx).capture is not None
        assert property_entry(source, ctx).enabled is False
        rows = operator_entries("wm.context_toggle", props, ctx)
        assert next(r for r in rows if r.key == "SHORTCUT").capture is not None
        assert (
            next(
                r
                for r in operator_entries(
                    "wm.context_toggle", props, ctx, pointers={"object": obj}
                )
                if r.key == "SHORTCUT"
            ).enabled
            is False
        )
        checks.append(
            "custom glass capture: assign/change/remove real keymap, cancel, modifier-only input, conflicts, stale-item rejection and exact properties"
        )
        ctx.preferences.view.show_developer_ui = True
        ctx.preferences.view.show_tooltips_python = True
        assert any(
            "Python: Object.location" in r.tip for r in source.entries(target, ctx)
        )
        old_area = ctx.area.type
        execute("SOURCE")
        assert ctx.area.type == "TEXT_EDITOR"
        assert Path(ctx.area.spaces.active.text.filepath) == Path(__file__).resolve()
        assert (
            ctx.area.spaces.active.text.current_line_index
            == run.__code__.co_firstlineno - 1
        )
        ctx.area.type = old_area
        checks.append(
            "explicit authoring source opens correct file/line; Python tooltip preference honored"
        )

    output = dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=checks,
    )
    print("BEYOND_UI_RESULT=" + json.dumps(output))
    path = os.environ.get("BEYOND_UI_TEST_RESULT")
    if path:
        Path(path).write_text(json.dumps(output, indent=2))
    bpy.ops.wm.quit_blender()


def timer():
    try:
        run()
    except Exception:
        import traceback

        traceback.print_exc()
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
