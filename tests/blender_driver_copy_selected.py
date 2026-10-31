"""Driver-copy fidelity, evaluation, exact channels and transaction rollback."""

import bpy, json, os, sys, traceback
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Target, Menu
from beyond_ui.context_drivers import plan, copy_selected


def run():
    ctx = bpy.context
    commits = []

    def obj(name):
        value = bpy.data.objects.new(name, None)
        ctx.collection.objects.link(value)
        return value

    source, a, b, input_id = [obj(n) for n in ("source", "A", "B", "input")]
    input_id["amount"] = 3.0
    curve = source.driver_add("location", 1)
    curve.driver.expression = "amount * 2"
    variable = curve.driver.variables.new()
    variable.name, variable.type = "amount", "SINGLE_PROP"
    variable.targets[0].id = input_id
    variable.targets[0].data_path = '["amount"]'
    source.driver_add("location", 2).driver.expression = "7"
    a.driver_add("location", 0).driver.expression = "42"
    old = a.driver_add("location", 1)
    old.driver.expression = "9"
    old.modifiers.new("NOISE").strength = 0.75
    a.keyframe_insert(data_path="location", index=2, frame=1)
    b.location.x = 19
    selection = NS(selected_objects=[source, a, b])
    binding = rna_binding(lambda: source, "location", index=1)
    target = Target(
        "driver", binding=binding, valid=binding.context.valid, commit=commits.append
    )
    prop = binding.context
    objects_before = len(bpy.data.objects)
    copy_selected(prop, target, selection)
    assert len(bpy.data.objects) == objects_before
    assert commits == ["COPY_DRIVERS_SELECTED"]
    for owner in (a, b):
        driver = owner.animation_data.drivers.find("location", index=1)
        assert driver.driver.expression == "amount * 2"
        assert driver.driver.variables[0].targets[0].id == input_id
        assert driver.driver.variables[0].targets[0].data_path == '["amount"]'
        assert len(driver.modifiers) == len(curve.modifiers)
    assert a.animation_data.drivers.find("location", index=0).driver.expression == "42"
    assert b.location.x == 19
    ctx.view_layer.update()
    depsgraph = ctx.evaluated_depsgraph_get()
    assert abs(b.evaluated_get(depsgraph).location.y - 6) < 1e-6, (
        "New driver must evaluate"
    )
    input_id["amount"] = 4.0
    input_id.update_tag()
    ctx.view_layer.update()
    assert abs(b.evaluated_get(depsgraph).location.y - 8) < 1e-6

    # Whole-array copy skips animated Z on A, but copies it to B.
    prop.execute("COPY_DRIVERS_SELECTED_ALL", target, selection)
    assert a.animation_data.drivers.find("location", index=2) is None
    assert b.animation_data.drivers.find("location", index=2).driver.expression == "7"
    assert a.animation_data.action is not None

    # Reject all destinations atomically, preserving unrelated host-side changes.
    old = a.animation_data.drivers.find("location", index=1)
    old.driver.expression = "11"
    old.modifiers.new("NOISE").strength = 0.25
    b.animation_data_clear()
    before = len(bpy.data.objects)

    def reject(action):
        a.animation_data.drivers.find("location", index=0).driver.expression = "44"
        b.location.x = 29
        raise RuntimeError("host rejected")

    target = replace(target, commit=reject)
    try:
        copy_selected(prop, target, selection)
    except RuntimeError as error:
        assert str(error) == "host rejected"
    else:
        raise AssertionError("Expected rejected commit")
    restored = a.animation_data.drivers.find("location", index=1)
    assert restored.driver.expression == "11"
    assert (
        restored.modifiers[-1].type == "NOISE"
        and restored.modifiers[-1].strength == 0.25
    )
    assert a.animation_data.drivers.find("location", index=0).driver.expression == "44"
    assert b.animation_data is None and b.location.x == 29
    assert len(bpy.data.objects) == before

    no_undo = Target("no undo", binding=binding)
    assert not plan(prop, no_undo, selection)
    target = replace(target, commit=commits.append)
    selection.selected_objects = []
    assert not plan(prop, target, selection)
    selection.selected_objects = [source, a]
    for o in ctx.selected_objects:
        o.select_set(False)
    source.select_set(True)
    a.select_set(True)
    ctx.view_layer.objects.active = source
    menu = Menu(
        target, prop.entries(target, ctx), (0, 0), (0, 0, 800, 1200), context=ctx
    )
    index = next(
        i for i, e in enumerate(menu.page.rows) if e.key == "COPY_DRIVERS_SELECTED"
    )
    source.driver_remove("location", 1)
    count = len(commits)
    menu.choose(index, ctx)
    assert not menu.closed and len(commits) == count
    assert a.animation_data.drivers.find("location", index=1).driver.expression == "11"

    # Same-ID node owners exercise path substitution without changing variable IDs.
    tree = bpy.data.node_groups.new("nodes", "ShaderNodeTree")
    n1, n2 = [tree.nodes.new("ShaderNodeValue") for _ in range(2)]
    nc = n1.driver_add("location", 0)
    nc.driver.expression = "5"
    nb = rna_binding(lambda: n1, "location", index=0)
    nt = Target("node", binding=nb, commit=commits.append)
    copy_selected(nb.context, nt, NS(selected_nodes=[n1, n2]))
    assert (
        tree.animation_data.drivers.find(n1.path_from_id("location"), index=0)
        is not None
    )
    assert (
        tree.animation_data.drivers.find(
            n2.path_from_id("location"), index=0
        ).driver.expression
        == "5"
    )
    return dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Single/all copies retain complete drivers and original variable target IDs",
            "New driver dependencies evaluate and react to input changes",
            "Existing drivers are replaced; keyed destinations and sibling channels survive",
            "Rejected host commit restores drivers/modifiers and removes new empty AnimData",
            "Unrelated host edits survive rollback; temporary staging is always removed",
            "Missing undo, empty selection and stale source channels fail closed",
            "Same-ID nested node paths copy without replacing the source channel",
        ],
    )


try:
    result = run()
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
