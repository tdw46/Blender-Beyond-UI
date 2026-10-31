"""Genuine custom Property RNA contexts, callbacks, commands and inline menus."""

import bpy, json, os, sys, traceback
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target
from beyond_ui.context_extensions import collect
from beyond_ui.hosts import menu_context


def run():
    ctx = bpy.context
    obj = ctx.active_object
    checks = []
    commits = []
    calls = []
    key = 'gain "quoted" 雪'
    path = "[" + json.dumps(key, ensure_ascii=False) + "]"
    obj[key] = 0.75
    obj.id_properties_ui(key).update(
        default=0.25, min=0, max=2, description="custom gain"
    )
    obj["second"] = 0.8
    obj.id_properties_ui("second").update(default=0.2, min=0, max=2)
    source = rna_binding(
        lambda: obj, path, commit=lambda a, b: commits.append("RESET")
    ).context
    target = Target("custom", valid=source.valid, commit=commits.append)
    previous = getattr(ctx, "button_prop", None)

    class BUI_OT_custom_contribution(bpy.types.Operator):
        bl_idname = "bui.custom_contribution"
        bl_label = "Contributed custom action"
        bl_options = {"UNDO"}
        amount: bpy.props.FloatProperty()

        @classmethod
        def poll(cls, context):
            return (
                context.button_pointer == obj
                and context.button_prop.identifier == key
                and context.button_prop.type == "FLOAT"
            )

        def execute(self, context):
            calls.append(
                (
                    context.button_pointer.as_pointer(),
                    context.button_prop.identifier,
                    self.amount,
                )
            )
            context.button_pointer[context.button_prop.identifier] = self.amount
            context.button_pointer.id_data.update_tag()
            return {"FINISHED"}

    class BUI_MT_custom_contribution(bpy.types.Menu):
        bl_label = "Nested custom actions"

        def draw(self, context):
            assert isinstance(context.button_prop, bpy.types.FloatProperty)
            self.layout.operator("bui.custom_contribution").amount = 0.6
            self.layout.prop(context.button_pointer, '["second"]', text="Second")

    bpy.utils.register_class(BUI_OT_custom_contribution)
    bpy.utils.register_class(BUI_MT_custom_contribution)

    def callback(holder, context):
        prop = context.button_prop
        assert isinstance(prop, bpy.types.FloatProperty)
        assert prop.identifier == key and prop.description == "custom gain"
        assert context.button_pointer == obj
        holder.layout.operator_context = "EXEC_DEFAULT"
        holder.layout.operator("ui.reset_default_button").all = False
        holder.layout.operator("ui.assign_default_button")
        holder.layout.operator("ui.copy_data_path_button").full_path = True
        holder.layout.operator("bui.custom_contribution").amount = 0.5
        row = holder.layout.row()
        row.enabled = False
        row.operator("bui.custom_contribution").amount = 1.5
        holder.layout.menu("BUI_MT_custom_contribution")
        holder.layout.prop(obj, path, text="Gain")
        holder.layout.operator(
            "anim.keyframe_insert_button"
        )  # unmapped native button remains off

    def menu(rows, t=target):
        return Menu(t, rows, (0, 0), (0, 0, 900, 1400), context=ctx)

    def choose(rows, key, t=target, error=None):
        m = menu(rows, t)
        i = next(i for i, r in enumerate(m.page.rows) if r.key == key)
        assert m.page.available[i], (key, m.error)
        m.choose(i, ctx)
        assert m.error == error, (key, m.error)
        return m

    try:
        # Cross-property nested callbacks must not inherit an outer button_prop.
        other = rna_binding(lambda: obj, '["second"]').context

        nested_checks = []

        def outer(holder, context):
            before = context.button_prop.as_pointer()

            def inner(inner_holder, current):
                assert current.button_prop.identifier == "second"
                assert current.button_pointer == obj
                inner_holder.layout.label(text="nested")

            assert collect(context, other, (inner,))[0].label == "nested"
            assert context.button_prop.as_pointer() == before
            nested_checks.append(True)

        collect(ctx, source, (outer,))
        assert nested_checks == [True]
        obj["integer"] = 4
        integer = rna_binding(lambda: obj, '["integer"]').context

        def integer_callback(holder, context):
            assert isinstance(context.button_prop, bpy.types.IntProperty)
            assert context.button_prop.identifier == "integer"
            holder.layout.label(text="Integer verified")

        assert collect(ctx, integer, (integer_callback,))[0].label == "Integer verified"
        rows = collect(ctx, source, (callback,))
        assert menu_context.api().beyond_context_active() == 0
        assert getattr(ctx, "button_prop", None) == previous
        choose(rows, "ui.reset_default_button")
        assert obj[key] == 0.25
        obj[key] = 0.9
        choose(rows, "ui.assign_default_button")
        assert obj.id_properties_ui(key).as_dict()["default"] == 0.9
        obj[key] = 0.3

        def reject(action):
            raise RuntimeError("reject")

        choose(
            rows,
            "ui.assign_default_button",
            replace(target, commit=reject),
            error="reject",
        )
        assert obj.id_properties_ui(key).as_dict()["default"] == 0.9
        choose(rows, "bui.custom_contribution")
        assert obj[key] == 0.5 and calls[-1][1] == key
        m = menu(rows)
        assert not m.page.available[4] and not m.page.available[-1]
        assert not any(
            r.key == "ui.assign_default_button" and r.enabled(Target("no undo"), ctx)
            for r in rows
        )
        checks.append(
            "real FloatProperty/IntProperty and nested context restoration verified; owner/identifier/description reaches callbacks and operators; mapped reset/default commands and rollback work"
        )
        # Nested and inline contributed fields retain the same owner contract.
        m = choose(rows, "BUI_MT_custom_contribution")
        i = next(
            i for i, r in enumerate(m.page.rows) if r.key == "bui.custom_contribution"
        )
        m.choose(i, ctx)
        assert abs(obj[key] - 0.6) < 1e-6
        field = next(r for r in rows if r.key == path)
        field.field.apply("1.25", obj[key], target, ctx)
        assert obj[key] == 1.25
        try:
            field.field.apply("1.5", obj[key], replace(target, commit=reject), ctx)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected rollback")
        assert obj[key] == 1.25
        second = choose(rows, "BUI_MT_custom_contribution")
        i = next(i for i, r in enumerate(second.page.rows) if r.key == '["second"]')
        assert second.open_row_context(i, ctx)
        i = next(i for i, r in enumerate(second.page.rows) if r.key == "RESET")
        second.choose(i, ctx)
        assert abs(obj["second"] - 0.2) < 1e-6 and obj[key] == 1.25
        checks.append(
            "nested menus, custom inline edit/rollback and right-click subfield Reset target exact contributed property"
        )

        def broken(holder, context):
            raise RuntimeError("intentional contribution failure")

        assert len(collect(ctx, source, (broken, callback))) == len(rows)
        assert menu_context.api().beyond_context_active() == 0
        # Real public append route, not only a direct collector call.
        bpy.types.UI_MT_button_context_menu.append(callback)
        try:
            assert any(
                r.key == "bui.custom_contribution" for r in source.entries(target, ctx)
            )
        finally:
            bpy.types.UI_MT_button_context_menu.remove(callback)
        # Unsupported build/API routes must advertise a disabled row, not break built-ins.
        bpy.types.UI_MT_button_context_menu.append(callback)
        original = menu_context.custom_property
        try:

            def unavailable(*args):
                raise RuntimeError("unqualified fixture")

            menu_context.custom_property = unavailable
            current = source.entries(target, ctx)
            assert any(
                r.key == "EXTENSIONS_UNAVAILABLE" and r.enabled is False
                for r in current
            )
            assert any(r.key == "RESET" for r in current)
        finally:
            menu_context.custom_property = original
            bpy.types.UI_MT_button_context_menu.remove(callback)
        checks.append(
            "public appended callbacks integrate; failing callbacks isolate; unsupported adapters keep base menus with explicit unavailable row"
        )
        # Refresh metadata each time; never keep a dangling custom-property pointer.
        pending = menu(rows)
        del obj[key]
        pending.choose(3, ctx)
        assert pending.closed and len(calls) == 2
        assert menu_context.api().beyond_context_active() == 0
        obj[key] = 0.25
        obj.id_properties_ui(key).update(description="custom gain", min=0, max=2)
        source = rna_binding(lambda: obj, path).context
        rows = collect(ctx, source, (callback,))
        bpy.utils.unregister_class(BUI_OT_custom_contribution)
        m = menu(rows, Target("replaced", valid=source.valid))
        assert not m.page.available[3]
        checks.append(
            "deleted custom property and unregistered operator revoke pending actions without retaining native scopes"
        )
    finally:
        if BUI_OT_custom_contribution.is_registered:
            bpy.utils.unregister_class(BUI_OT_custom_contribution)
        bpy.utils.unregister_class(BUI_MT_custom_contribution)
    assert (
        getattr(ctx, "button_prop", None) == previous
        and menu_context.api().beyond_context_active() == 0
    )
    return checks


try:
    result = {"passed": True, "version": bpy.app.version_string, "checks": run()}
except Exception:
    result = {"passed": False, "error": traceback.format_exc()}
    print(result["error"])
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
if not result["passed"]:
    raise RuntimeError(result["error"])
