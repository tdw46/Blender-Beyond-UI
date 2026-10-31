"""Real custom-ID driver clipboard, native Favorites and numeric keymap actions."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target
from beyond_ui.hosts import menu_native as native
from beyond_ui.context_paths import owner_path
from beyond_ui.context_shortcuts import numeric_property_entry, Action


def run():
    ctx = bpy.context
    checks, commits = [], []
    from beyond_ui.context_dispatch import ShortcutRegistry

    registry = ShortcutRegistry("test.custom.adapters")
    registry.register()
    namespace, op_name = registry.property_idname.split(".")
    set_value = getattr(getattr(bpy.ops, namespace), op_name)
    area = next(a for a in ctx.screen.areas if a.type == "VIEW_3D")
    with ctx.temp_override(area=area):
        obj = ctx.active_object
        key = 'quoted "gain"\\雪'
        obj[key] = 0.625
        path = "[" + json.dumps(key, ensure_ascii=False) + "]"
        source = rna_binding(lambda: obj, path).context
        target = Target("custom", valid=source.valid, commit=commits.append)

        def rows(src=source, t=target):
            return src.entries(t, ctx)

        def choose(key, src=source, t=target, error=None):
            m = Menu(t, rows(src, t), (0, 0), (0, 0, 900, 1500), context=ctx)
            index = next(i for i, r in enumerate(m.page.rows) if r.key == key)
            assert m.page.available[index], (key, m.error, native.reason())
            m.choose(index, ctx)
            assert m.error == error, (key, m.error)
            return m

        assert native.api() is not None, native.reason()
        obj.driver_add(path).driver.expression = "0.75"
        choose("COPY_DRIVER")
        native.curve(source).driver.expression = "0.5"
        choose("PASTE_DRIVER")
        assert native.curve(source).driver.expression == "0.75"

        def reject(action):
            obj["untouched"] = 17
            raise RuntimeError("reject")

        native.curve(source).driver.expression = "0.25"
        choose("PASTE_DRIVER", t=replace(target, commit=reject), error="reject")
        assert (
            native.curve(source).driver.expression == "0.25" and obj["untouched"] == 17
        )
        obj.driver_remove(path)
        obj.keyframe_insert(data_path=path)
        paste = next(r for r in rows() if r.key == "PASTE_DRIVER")
        assert not paste.enabled(target, ctx)
        obj.keyframe_delete(data_path=path)
        choose("NATIVE_DRIVER")
        receiver = bpy.data.objects.new("custom receiver", None)
        ctx.collection.objects.link(receiver)
        receiver["gain"] = 0.0
        dst = rna_binding(lambda: receiver, '["gain"]').context
        choose("PASTE_DRIVER", dst, replace(target, valid=dst.valid))
        driver = native.curve(dst).driver
        assert driver.variables[0].targets[0].id == obj
        assert driver.variables[0].targets[0].data_path == path
        source.assign(obj, 0.875)
        ctx.view_layer.update()
        evaluated = receiver.evaluated_get(ctx.evaluated_depsgraph_get())
        assert abs(evaluated["gain"] - 0.875) < 1e-6, evaluated["gain"]
        assert not any(
            o.name.startswith("Beyond UI driver clipboard staging")
            for o in bpy.data.objects
        )
        checks.append(
            "real clipboard copy/paste/new-driver handles escaped Unicode custom paths, evaluation, keyed guards and rollback"
        )

        choose("FAVORITE")
        funcs = native.api()
        menu = funcs["favorites"](ctx.as_pointer())
        args = (menu + 88, owner_path(source, ctx).encode(), path.encode(), -1)
        handle = funcs["find_property"](*args)
        assert handle
        native.add_property_favorite(source, ctx)
        assert funcs["find_property"](*args) == handle
        ctx.preferences.is_dirty = False
        assert native.property_favorite(source, ctx) and not ctx.preferences.is_dirty
        choose("REMOVE_FAVORITE")
        assert not native.property_favorite(source, ctx)
        # Byte-bound native fields must never retain a truncated custom key.
        long_key = "雪" * 20
        obj[long_key] = 0.5
        long_src = rna_binding(
            lambda: obj, "[" + json.dumps(long_key, ensure_ascii=False) + "]"
        ).context
        assert not native.favorite_supported(long_src, ctx)
        try:
            native.add_property_favorite(long_src, ctx)
            raise AssertionError("must reject oversized UTF-8 Favorite identifiers")
        except RuntimeError:
            pass
        other = ctx.view_layer.objects.active
        ctx.view_layer.objects.active = receiver
        assert not native.favorite_supported(source, ctx)
        ctx.view_layer.objects.active = other
        checks.append(
            "native Favorites store exact custom path, deduplicate, remove, stay read-only on query and reject truncation/context drift"
        )

        def event(key):
            return SimpleNamespace(
                type=key, value="PRESS", shift=True, ctrl=True, alt=True, oskey=True
            )

        source.assign(obj, 0.123456789012345)
        captured = source.read()
        row = numeric_property_entry(source, ctx, registry)
        m = Menu(target, (row,), (0, 0), (0, 0, 900, 1000), context=ctx)
        assert m.page.available == (True,), m.error
        m.choose(0, ctx)
        m.choose(1, ctx)
        m.choose(1, ctx)
        assert m.capture_row is not None
        m.event(event("F19"), 5, 5, ctx)
        assert m.closed and m.error is None, m.error
        prop_path = owner_path(source, ctx)
        assert prop_path == "object", prop_path
        props = {
            "owner_path": prop_path,
            "key": source.key,
            "kind": "FLOAT",
            "value": repr(captured),
        }
        action = Action(registry.property_idname, props, ctx, keymap=registry.keymap)
        km, item = action.current(ctx)
        assert item is not None and item.type == "F19"
        source.assign(obj, 0.2)
        result = set_value(**props)
        assert "FINISHED" in result and source.read() == captured, (
            result,
            source.read(),
        )
        ctx.view_layer.update()
        evaluated = receiver.evaluated_get(ctx.evaluated_depsgraph_get())
        assert abs(evaluated["gain"] - captured) < 1e-6, evaluated["gain"]
        source.assign(obj, 0.3)
        choices = numeric_property_entry(source, ctx, registry).children(target, ctx)
        old = next(r for r in choices if repr(captured) in r.label)
        children = old.children(target, ctx)
        assert children[0].label == "Change Shortcut"
        children[0].capture(target, ctx, event("F18"))
        assert item.type == "F18"
        children = next(
            r
            for r in numeric_property_entry(source, ctx, registry).children(target, ctx)
            if repr(captured) in r.label
        ).children(target, ctx)
        children[1].action(target, ctx)
        assert not any(
            i.idname == registry.property_idname
            and i.properties.owner_path == prop_path
            for i in km.keymap_items
        )
        checks.append(
            "custom shortcut capture/change/remove and registered execution preserve double precision; prior values remain discoverable"
        )

        from beyond_ui import Canvas

        canvas = Canvas(shortcut_registry=registry, menu_commit=commits.append)
        control = canvas.number("custom", "Gain", rna_binding(lambda: obj, path))
        canvas.arrange(600)
        assert canvas.open_context(control, 20, 20, (0, 0, 640, 560), context=ctx), (
            canvas.menu_error
        )
        shortcut_index = next(
            i
            for i, r in enumerate(canvas.context_menu.page.rows)
            if r.key == "SHORTCUT"
        )
        assert canvas.context_menu.page.available[shortcut_index]
        canvas.context_menu.close()
        canvas.park()
        checks.append(
            "actual Canvas owner menu installs registered numeric shortcut path without changing renderer"
        )

        class Settings(bpy.types.PropertyGroup):
            pass

        bpy.utils.register_class(Settings)
        bpy.types.Object.adapter_settings = bpy.props.PointerProperty(type=Settings)
        try:
            nested_owner = obj.adapter_settings
            nested_owner["gain"] = 0.5
            nested = rna_binding(lambda: nested_owner, '["gain"]').context
            choose("NATIVE_DRIVER", nested, replace(target, valid=nested.valid))
            native.add_property_favorite(nested, ctx)
            assert native.property_favorite(nested, ctx)
            native.property_favorite(nested, ctx, remove=True)
            nested_props = dict(
                owner_path=owner_path(nested, ctx),
                key="gain",
                kind="FLOAT",
                value="0.8",
            )
            assert set_value(**nested_props) == {"FINISHED"}
            assert abs(nested_owner["gain"] - 0.8) < 1e-6
        finally:
            del bpy.types.Object.adapter_settings
            bpy.utils.unregister_class(Settings)
        checks.append(
            "nested PropertyGroup clipboard, Favorites and shortcut dispatch retain full owner path"
        )

        # Large integer literal is preserved, cancellation and stale owner never create a key.
        obj["count"] = 2**30 + 3
        count = rna_binding(lambda: obj, '["count"]').context
        count_row = numeric_property_entry(count, ctx, registry).children(target, ctx)[
            0
        ]
        count_row.capture(target, ctx, event("F17"))
        count_props = {
            "owner_path": owner_path(count, ctx),
            "key": count.key,
            "kind": "INT",
            "value": repr(count.read()),
        }
        obj["count"] = 0
        set_value(**count_props)
        assert obj["count"] == 2**30 + 3
        count_action = Action(
            registry.property_idname, count_props, ctx, keymap=registry.keymap
        )
        count_action.remove(target, ctx)
        pending = numeric_property_entry(count, ctx, registry).children(target, ctx)[0]
        locked = replace(target, editable=lambda: False)
        assert not pending.enabled(locked, ctx)
        try:
            pending.capture(locked, ctx, event("F16"))
            raise AssertionError("Disabled capture must be rejected")
        except ReferenceError:
            pass
        before = len(km.keymap_items)
        cancel = Menu(target, (pending,), (0, 0), (0, 0, 900, 1000), context=ctx)
        cancel.choose(0, ctx)
        cancel.choose(1, ctx)
        cancel.event(SimpleNamespace(type="ESC", value="PRESS"), 5, 5, ctx)
        assert len(km.keymap_items) == before
        del obj["count"]
        assert not pending.enabled(target, ctx)
        stale = rows()
        del obj[key]
        assert not any(
            (r.enabled(target, ctx) if callable(r.enabled) else r.enabled)
            for r in stale
            if r.key
            in {
                "COPY_DRIVER",
                "PASTE_DRIVER",
                "NATIVE_DRIVER",
                "FAVORITE",
                "REMOVE_FAVORITE",
                "SHORTCUT",
            }
        )
        checks.append(
            "large integer shortcut values, cancellation, deleted keys and changed owner invalidate without writes"
        )
        # The registered setter rejects stale/retyped keys at dispatch too.
        assert set_value(**count_props) == {"CANCELLED"} and "count" not in obj
        obj["count"] = "new type"
        assert set_value(**count_props) == {"CANCELLED"} and obj["count"] == "new type"
        # A real undo/redo round trip reacquires IDs, never retaining old wrappers.
        obj["undo_gain"] = 0.25
        obj_name = obj.name
        undo_props = dict(
            owner_path="object", key="undo_gain", kind="FLOAT", value="0.75"
        )
        bpy.ops.ed.undo_push(message="Custom property baseline")
        assert set_value("EXEC_DEFAULT", True, **undo_props) == {"FINISHED"}
        assert bpy.ops.ed.undo() == {"FINISHED"}
        assert bpy.data.objects[obj_name]["undo_gain"] == 0.25
        assert bpy.ops.ed.redo() == {"FINISHED"}
        assert bpy.data.objects[obj_name]["undo_gain"] == 0.75
        checks.append(
            "registered setter validates dispatch, refreshes driven values, and supports actual Blender undo/redo"
        )
    registry.close()
    assert registry.operator_class is None and registry.property_operator_class is None
    return checks


def timer():
    try:
        result = {"passed": True, "version": bpy.app.version_string, "checks": run()}
    except Exception:
        result = {"passed": False, "error": traceback.format_exc()}
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    if not result["passed"]:
        print(result["error"])
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
