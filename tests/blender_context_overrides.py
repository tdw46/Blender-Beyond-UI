"""Real linked overrides and scalar ID-property default transactions."""

import bpy, json, os, sys, tempfile, traceback
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding, Edit
from beyond_ui.context_menu import Target, Menu
from beyond_ui.context_overrides import entries, state
from beyond_ui import Canvas, Layout
from beyond_ui.decorator import Decorator


def run():
    ctx = bpy.context
    commits = []
    target = Target("fixture", commit=commits.append)
    checks = []

    def menu(rows, t=target):
        return Menu(t, rows, (0, 0), (0, 0, 800, 1600), context=ctx)

    def choose(rows, key, t=target, error=None):
        m = menu(rows, t)
        i = next(i for i, row in enumerate(m.page.rows) if row.key == key)
        assert m.page.available[i], (key, m.error)
        m.choose(i, ctx)
        assert m.error == error, (key, m.error)
        return m

    with tempfile.TemporaryDirectory() as folder:
        original = bpy.data.objects.new("linked override fixture", None)
        original.location = (1, 2, 3)
        original["gain"] = 0.25
        original.id_properties_ui("gain").update(default=0.1, min=0.0, max=1.0)
        original.property_overridable_library_set('["gain"]', True)
        path = str(Path(folder) / "library.blend")
        bpy.data.libraries.write(path, {original})
        with bpy.data.libraries.load(path, link=True) as (_, loaded):
            loaded.objects = [original.name]
        linked = loaded.objects[0]
        obj = linked.override_create(remap_local_usages=False)
        ctx.collection.objects.link(obj)
        source = rna_binding(lambda: obj, "location", index=1).context
        assert entries(rna_binding(lambda: linked, "location").context) == ()
        assert entries(rna_binding(lambda: original, "location").context) == ()
        choose(entries(source), "OVERRIDE_ADD_ALL")
        assert state(source)[2] == (-1,)
        obj.location = (10, 20, 30)
        choose(entries(source), "OVERRIDE_REMOVE")
        assert tuple(obj.location) == (10, 2, 30)
        assert state(source)[2] == (0, 2), state(source)
        checks.append(
            "single removal splits generic override and restores only linked component"
        )
        choose(entries(source), "OVERRIDE_ADD_ALL")
        assert state(source)[2] == (-1,)
        choose(entries(source), "OVERRIDE_REMOVE")
        choose(entries(source), "OVERRIDE_ADD")
        assert set(state(source)[2]) == {0, 1, 2}
        choose(entries(source), "OVERRIDE_REMOVE_ALL")
        assert tuple(obj.location) == (1, 2, 3) and not state(source)[2]
        choose(entries(source), "OVERRIDE_ADD_ALL")
        obj.location = (10, 20, 30)

        def reject(action):
            obj.location.x = 77
            raise RuntimeError("reject")

        choose(
            entries(source),
            "OVERRIDE_REMOVE",
            replace(target, commit=reject),
            error="reject",
        )
        assert tuple(obj.location) == (77, 20, 30) and state(source)[2] == (-1,)
        checks.append(
            "rejected removal restores rule and clicked value, preserving sibling edit"
        )
        choose(entries(source), "OVERRIDE_REMOVE_ALL")
        choose(
            entries(source),
            "OVERRIDE_ADD",
            replace(target, commit=reject),
            error="reject",
        )
        assert state(source)[2] == ()
        no_undo = menu(entries(source), Target("no undo"))
        assert not any(no_undo.page.available)
        stale = entries(source)
        obj.override_library.is_system_override = True
        assert entries(source) == ()
        assert not any(menu(stale).page.available)
        obj.override_library.is_system_override = False
        changed = entries(source)
        p = obj.override_library.properties.add("location")
        p.operations.add("DIFF_ADD")
        assert not any(menu(changed).page.available)
        assert entries(source) == ()
        obj.override_library.properties.remove(p)
        checks.append(
            "no undo, system overrides, changed and non-reproducible rules fail closed"
        )
        from beyond_ui.context_extensions import collect

        def contribution(holder, context):
            holder.layout.operator("ui.override_add_button").all = False

        choose(collect(ctx, source, (contribution,)), "ui.override_add_button")
        assert state(source)[2] == (1,)

        def remove_contribution(holder, context):
            holder.layout.operator("ui.override_remove_button").all = False

        choose(
            collect(ctx, source, (remove_contribution,)), "ui.override_remove_button"
        )
        assert not state(source)[2] and obj.location.y == 2
        checks.append(
            "contributed native override commands use captured component without active native button"
        )
        enum_source = rna_binding(lambda: obj, "rotation_mode").context
        choose(entries(enum_source), "OVERRIDE_ADD")
        obj.rotation_mode = "ZYX"
        choose(entries(enum_source), "OVERRIDE_REMOVE")
        assert obj.rotation_mode == linked.rotation_mode
        custom_override = rna_binding(lambda: obj, '["gain"]').context
        choose(entries(custom_override), "OVERRIDE_ADD")
        obj["gain"] = 0.8
        choose(entries(custom_override), "OVERRIDE_REMOVE")
        assert abs(obj["gain"] - 0.25) < 1e-6
        checks.append("custom scalar override restores actual linked ID property")

    obj = bpy.data.objects.new("custom defaults", None)
    ctx.collection.objects.link(obj)
    for key, value in (("gain", 0.75), ('quoted "gain"', 3)):
        obj[key] = value
        obj.id_properties_ui(key).update(
            default=0 if isinstance(value, int) else 0.1, min=0, max=10
        )
        name = "[" + json.dumps(key) + "]"
        binding = rna_binding(
            lambda: obj, name, commit=lambda a, b: commits.append((a, b))
        )
        source = binding.context
        assert obj.path_resolve(source.paths()[0]) == value
        assert eval(source.paths()[1], {"bpy": bpy}) == value
        choose(source.entries(target, ctx), "ASSIGN_DEFAULT")
        assert obj.id_properties_ui(key).as_dict()["default"] == value
        binding.write(2)
        choose(source.entries(target, ctx), "RESET")
        assert obj[key] == value
        edit = Edit(binding)
        edit.update(4)
        edit.finish(cancel=True)
        assert obj[key] == value
        choose(source.entries(target, ctx), "KEY")
        assert Decorator(binding, ctx).state() == "KEYED"
        choose(source.entries(target, ctx), "KEYING_ADD")
        assert any(p.data_path == name for p in ctx.scene.keying_sets_all.active.paths)
        choose(source.entries(target, ctx), "DELETE_KEY")
        choose(source.entries(target, ctx), "DRIVER")
        assert Decorator(binding, ctx).state() == "DRIVEN"
        choose(source.entries(target, ctx), "REMOVE_DRIVER")
    checks.append(
        "integer/float defaults, reset, cancel, escaped paths, keys, drivers and keying sets"
    )
    # Copy values/drivers only to selected owners with matching custom key/type.
    for candidate in ctx.selected_objects:
        candidate.select_set(False)
    receiver = bpy.data.objects.new("custom receiver", None)
    ctx.collection.objects.link(receiver)
    receiver["gain"] = 0.0
    receiver.select_set(True)
    wrong = bpy.data.objects.new("wrong custom type", None)
    ctx.collection.objects.link(wrong)
    wrong["gain"] = 5
    wrong.select_set(True)
    source = rna_binding(lambda: obj, '["gain"]').context
    choose(source.entries(target, ctx), "SELECTED")
    assert receiver["gain"] == obj["gain"] and wrong["gain"] == 5
    curve = obj.driver_add('["gain"]')
    curve.driver.expression = "0.5"
    choose(source.entries(target, ctx), "COPY_DRIVERS_SELECTED")
    assert receiver.animation_data.drivers[0].data_path == '["gain"]'
    assert receiver.animation_data.drivers[0].driver.expression == "0.5"
    obj.driver_remove('["gain"]')
    checks.append(
        "custom values/drivers copy to matching selected keys and skip mismatched types"
    )
    # Nested custom properties resolve through the ID owner, including animation.
    material = bpy.data.materials.new("custom node owner")
    material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeValue")
    node["gain"] = 0.3
    nested = rna_binding(lambda: node, '["gain"]').context
    assert abs(material.node_tree.path_resolve(nested.property_path()) - 0.3) < 1e-6
    choose(nested.entries(target, ctx), "KEY")
    checks.append("nested node ID-property path and keying use owning node tree")
    bpy.types.Object.default_test = bpy.props.FloatProperty(default=0.2)
    obj.default_test = 0.4
    try:
        rna_binding(lambda: obj, '["default_test"]')
        raise AssertionError("Registered RNA storage must not expose custom defaults")
    except TypeError:
        pass
    finally:
        del bpy.types.Object.default_test
    source = rna_binding(lambda: obj, '["gain"]').context
    obj["gain"] = 0.9

    def reject_default(action):
        obj.id_properties_ui("gain").update(description="host retained")
        raise RuntimeError("reject default")

    choose(
        source.entries(target, ctx),
        "ASSIGN_DEFAULT",
        replace(target, commit=reject_default),
        error="reject default",
    )
    ui = obj.id_properties_ui("gain").as_dict()
    assert ui["default"] == 0.75 and ui["description"] == "host retained"
    assert obj["gain"] == 0.9
    assert not next(
        row for row in source.entries(target, ctx) if row.key == "ASSIGN_DEFAULT"
    ).enabled(Target("no undo"), ctx)
    assert not any(
        row.key == "ASSIGN_DEFAULT"
        for row in rna_binding(lambda: obj, "location").context.entries(target, ctx)
    )
    checks.append(
        "default rollback preserves value and unrelated metadata; RNA defaults never mutated"
    )
    canvas = Canvas(menu_commit=commits.append)
    ui = Layout(canvas, context=ctx)
    ui.prop(obj, '["gain"]', text="Gain", slider=True, icon="SETTINGS")
    ui.use_property_split = True
    ui.use_property_decorate = True
    ui.prop(obj, '["quoted \\"gain\\""]', text="Count")
    assert source.valid()
    obj["gain"] = "changed type"
    assert not source.valid()
    del obj["gain"]
    assert not source.valid()
    checks.append(
        "Layout.prop custom numeric controls/decorators share renderer; stale key/type invalidates"
    )
    return checks


try:
    checks = run()
    result = {"passed": True, "version": bpy.app.version_string, "checks": checks}
except Exception:
    result = {"passed": False, "error": traceback.format_exc()}
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
if not result["passed"]:
    raise RuntimeError(result["error"])
