"""Real RNA transactions, custom template ownership and operator admission."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from beyond_ui import Canvas, Layout, PointerItems, UnsupportedControl
from beyond_ui.bindings import Edit
from id_templates_fixture import register, unregister, build, calls, BUI_OT_id_new


def reject(action, error=ReferenceError):
    try:
        action()
    except error:
        return
    raise AssertionError("Expected rejected operation")


def run():
    checks = []
    try:
        slots = register()
        commits = []
        ui, picker, name, fake = build(
            bpy.context, commit=lambda a, b: commits.append((a, b))
        )
        canvas = ui.canvas
        canvas.arrange(560)
        model = picker.options["id_template"]
        material = slots.material
        assert model.users() == 2
        edit = Edit(name.binding)
        edit.update("Renamed Surface")
        edit.finish()
        assert material.name == "Renamed Surface" and len(commits) == 1
        edit = Edit(fake.binding)
        edit.update(True)
        edit.finish()
        assert material.use_fake_user and model.users() == 2
        edit = Edit(name.binding)
        slots.material = bpy.data.materials["Accent Surface"]
        reject(lambda: edit.update("Wrong owner"))
        edit.finish(cancel=True)
        assert slots.material.name == "Accent Surface"
        slots.material = material
        clip = (0, 0, 560, 600)
        assert canvas.open_context(name, 10, 10, clip, context=bpy.context)
        menu = canvas.context_menu
        assert menu.target.binding.context.owner() == material
        slots.material = None
        assert not menu.target.valid()
        canvas.close_context()
        slots.material = material
        checks.append(
            "Name and Fake User edits commit once; selection snapshots prevent deferred writes and menus targeting a replacement ID"
        )

        bpy.context.preferences.filepaths.show_hidden_files_datablocks = False
        widget = model.picker(canvas, picker)
        assert ".Hidden Surface" not in [v[1] for v in widget.filtered]
        widget.query = "."
        widget._filter()
        assert ".Hidden Surface" in [v[1] for v in widget.filtered]
        bpy.context.preferences.filepaths.show_hidden_files_datablocks = True
        assert ".Hidden Surface" in [
            v[1] for v in model.picker(canvas, picker).filtered
        ]
        material.name = "Renamed after opening"
        widget.select(material.as_pointer())
        assert slots.material == material
        stale = model.picker(canvas, picker)
        temporary = bpy.data.materials["Accent Surface"]
        key = temporary.as_pointer()
        bpy.data.materials.remove(temporary)
        assert not stale.valid(key)
        checks.append(
            "Search respects dot-prefixed hidden IDs; rename preserves identity and deleted candidates are rejected"
        )

        token = model.token()
        model.duplicate(token)
        copy = slots.material
        assert copy != material and not copy.use_fake_user and slots.other == material
        assert len(commits) == 3, commits
        reject(lambda: model.clear(token))
        before_count = len(bpy.data.materials)
        original_commit = model.field.binding.commit

        def fail(a, b):
            raise RuntimeError("Host rejected")

        model.field.binding.commit = fail
        reject(lambda: model.duplicate(model.token()), RuntimeError)
        assert slots.material == copy and len(bpy.data.materials) == before_count
        model.field.binding.commit = original_commit
        model.clear(model.token())
        assert slots.material is None
        checks.append(
            "Single-user copy preserves other users, clears fake user, commits once and removes unowned copies on host rejection; stale unlink is rejected"
        )

        # A native operator needs the owning extension dispatcher, never a stray active button.
        native = Layout(context=bpy.context)
        native.template_ID(slots, "material", new="material.new")
        native_model = next(
            c.options["id_template"]
            for c in native.canvas.controls.values()
            if c.kind == "pointer"
        )
        assert not native_model.operator_available("new")
        requests = []
        dispatched = Layout(context=bpy.context, id_actions=requests.append)
        dispatched.template_ID(
            slots,
            "material",
            new="material.new",
            open="material.new",
            unlink="material.new",
        )
        routed = next(
            c.options["id_template"]
            for c in dispatched.canvas.controls.values()
            if c.kind == "pointer"
        )
        routed.invoke("new", routed.token())
        request = requests[-1]
        assert request.valid() and request.owner == slots
        dispatched.enabled = False
        assert not request.valid()
        reject(lambda: request.assign(material))
        dispatched.enabled = True
        request.assign(material)
        reject(lambda: request.assign(copy))
        assert slots.material == material
        for operation in ("open", "unlink"):
            routed.invoke(operation, routed.token())
            assert requests[-1].operation == operation
            assert requests[-1].owner == slots and requests[-1].selected == material
        temporary_scene = bpy.data.scenes.new("Deleted ID template owner")
        owned = Layout(context=bpy.context, id_actions=requests.append)
        owned.template_ID(temporary_scene.bui_ids, "material", unlink="material.new")
        bpy.data.scenes.remove(temporary_scene)
        assert all(not c.enabled for c in owned.canvas.controls.values()), [
            (c.kind, c.label, c.enabled) for c in owned.canvas.controls.values()
        ]
        checks.append(
            "Removed owning IDs disable every template control before dereferencing embedded RNA"
        )
        model.invoke("new", model.token())
        assert slots.material.name.startswith("Created Material") and "INVOKED" in calls
        assert calls[-1] == (slots.as_pointer(), "material", material), calls
        bpy.utils.unregister_class(BUI_OT_id_new)
        reject(lambda: model.invoke("new", model.token()))
        checks.append(
            "Python New operator receives exact ID/pointer/property context and invokes; built-in operators require host dispatcher; delayed host assignment and unregistered operators fail closed"
        )

        # Deleted tabs stay inert, and selecting a tab rechecks source membership and poll.
        tabs = [c for c in canvas.controls.values() if ":id-tab:" in c.key]
        removed = next(c for c in tabs if c.label == "Accent Surface")
        assert not removed.enabled
        assert not removed.options["selected"]()
        tab = next(c for c in tabs if c.label == "Glass Surface")
        tab.action()
        assert slots.material == material
        assert canvas.open_context(tab, 10, 10, clip, context=bpy.context)
        menu = canvas.context_menu
        slots.material = copy
        assert not menu.target.valid()
        canvas.cancel()
        checks.append(
            "Tabs follow live names and selections; removed data and stale context actions cannot mutate a different ID"
        )

        extra = bpy.data.objects.new(
            "Outside scene camera", bpy.data.cameras.new("Outside scene camera")
        )
        available = Layout(context=bpy.context)
        available.template_ID(bpy.context.scene, "camera", filter="AVAILABLE")
        ctl = next(c for c in available.canvas.controls.values() if c.kind == "pointer")
        m = ctl.options["id_template"]
        assert extra.as_pointer() not in [
            i[0] for i in m.picker(available.canvas, ctl).items
        ]
        reject(
            lambda: Layout(context=bpy.context).template_ID(
                slots, "material", live_icon=True
            ),
            UnsupportedControl,
        )
        reject(
            lambda: Layout(context=bpy.context).template_ID_tabs(
                slots, "material", menu="UNKNOWN"
            ),
            UnsupportedControl,
        )
        checks.append(
            "AVAILABLE excludes objects outside the scene; unsupported preview icons and custom registered tab menus remain explicit"
        )
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("ID_TEMPLATES", result, flush=True)
    bpy.app.timers.register(
        lambda: bpy.ops.wm.quit_blender() and None, first_interval=0.2
    )


bpy.app.timers.register(run, first_interval=1)
