"""Exact-build context strings and dynamic enum callback qualification."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.hosts.menu_context import scope, api
from beyond_ui.context_enums import items


def run():
    checks = []
    ctx = bpy.context
    area = next(a for a in ctx.screen.areas if a.type == "VIEW_3D")
    with ctx.temp_override(area=area):
        assert getattr(ctx, "beyond_string", None) is None
        with scope(ctx, {"beyond_string": "Outer Δ", "unrelated_string": "Retained"}):
            assert ctx.beyond_string == "Outer Δ", repr(ctx.beyond_string)
            with scope(ctx, {"beyond_string": "Inner"}):
                assert (
                    ctx.beyond_string == "Inner" and ctx.unrelated_string == "Retained"
                )
            assert ctx.beyond_string == "Outer Δ"
            try:
                with scope(ctx, {"beyond_string": "Throws"}):
                    raise ValueError("fixture")
            except ValueError:
                pass
            assert ctx.beyond_string == "Outer Δ"
        assert (
            getattr(ctx, "beyond_string", None) is None
            and api().beyond_context_active() == 0
        )
        checks.append(
            "native string scope preserves Unicode and inherited keys; nested/exception exit restores context and releases stores"
        )
        from beyond_ui.context_extensions import collect
        from beyond_ui.context_menu import Menu, Target
        from beyond_ui import Layout

        observed = []
        operator_choices = [("A", "Alpha", "")]

        def dynamic_operator(self, context):
            # Blender may deliberately omit context for operator enum callbacks.
            if context is not None:
                assert context.beyond_string == "Scoped Δ"
            return [("B", "Beta", "")] if self.amount == 7 else operator_choices

        class BEYONDUI_OT_string_scope(bpy.types.Operator):
            bl_idname = "beyondui.string_scope"
            bl_label = "String scope"
            amount: bpy.props.IntProperty()
            choice: bpy.props.EnumProperty(items=dynamic_operator)

            @classmethod
            def poll(cls, context):
                return getattr(context, "beyond_string", None) == "Scoped Δ"

            def execute(self, context):
                observed.append((context.beyond_string, self.choice))
                return {"FINISHED"}

        bpy.utils.register_class(BEYONDUI_OT_string_scope)
        try:

            def contribution(holder, context):
                holder.layout.context_string_set("beyond_string", "Scoped Δ")
                holder.layout.operator_context = "EXEC_DEFAULT"
                settings = holder.layout.operator_menu_enum(
                    "beyondui.string_scope", "choice"
                )
                settings.amount = 7

            before_configs = len(ctx.window_manager.keyconfigs)
            ctx.preferences.is_dirty = False
            rows = collect(ctx, None, (contribution,))
            menu = Menu(Target("string"), rows, (10, 10), (0, 0, 640, 560), context=ctx)
            assert menu.page.available == (True,)
            menu.choose(0, ctx)
            assert menu.page.rows[1].label == "Beta"
            menu.choose(1, ctx)
            assert observed == [("Scoped Δ", "B")], (observed, menu.error)
            assert (
                len(ctx.window_manager.keyconfigs) == before_configs
                and not ctx.preferences.is_dirty
            )
            assert (
                getattr(ctx, "beyond_string", None) is None
                and api().beyond_context_active() == 0
            )
            ui = Layout(context=ctx)
            ui.operator_context = "EXEC_DEFAULT"
            ui.context_string_set("beyond_string", "Scoped Δ")
            ui.operator("beyondui.string_scope")
            next(iter(ui.canvas.controls.values())).action()
            assert observed[-1] == ("Scoped Δ", "A")

            def direct_contribution(holder, context):
                holder.layout.context_string_set("beyond_string", "Scoped Δ")
                holder.layout.operator_context = "EXEC_DEFAULT"
                holder.layout.operator_enum("beyondui.string_scope", "choice")

            direct = collect(ctx, None, (direct_contribution,))
            direct_menu = Menu(
                Target("direct"), direct, (10, 10), (0, 0, 640, 560), context=ctx
            )
            assert direct_menu.page.rows[0].label == "Alpha"
            direct_menu.choose(0, ctx)
            assert observed[-1] == ("Scoped Δ", "A") and not direct_menu.error
            checks.append(
                "contributed and authored operators retain native string scope; dynamic operator enums see snapshotted properties; scratch config cleanup preserves preferences"
            )
        finally:
            bpy.utils.unregister_class(BEYONDUI_OT_string_scope)
        choices = [("A", "Alpha", "First"), ("B", "Beta", "Second")]

        def dynamic(self, context):
            assert context is not None and context.area == area
            return choices

        class BEYONDUI_PG_dynamic(bpy.types.PropertyGroup):
            choice: bpy.props.EnumProperty(items=dynamic)

        bpy.utils.register_class(BEYONDUI_PG_dynamic)
        bpy.types.Scene.beyond_dynamic = bpy.props.PointerProperty(
            type=BEYONDUI_PG_dynamic
        )
        try:
            group = ctx.scene.beyond_dynamic
            actual = items(group, "choice", ctx)
            assert [(i.identifier, i.name) for i in actual] == [
                ("A", "Alpha"),
                ("B", "Beta"),
            ], actual
            choices[:] = [("B", "Beta", "Second"), ("C", "Gamma", "Third")]
            for _ in range(30):
                assert [i.identifier for i in items(group, "choice", ctx)] == ["B", "C"]
            checks.append(
                "dynamic Python enum callbacks receive exact context and updated items; repeated native temporary arrays released"
            )
            from beyond_ui.context_fields import property_row

            target = Target("dynamic", commit=lambda action: None)
            menu = Menu(
                target,
                (property_row(group, "choice"),),
                (10, 10),
                (0, 0, 640, 560),
                context=ctx,
            )
            menu.choose(0, ctx)
            assert [r.label for r in menu.page.rows[1:]] == ["Beta", "Gamma"]
            choices[:] = [("B", "Beta", "Second")]
            menu.choose(2, ctx)
            assert menu.error and group.choice != "C"
            authored = Layout(context=ctx)
            authored.prop(group, "choice")
            control = next(iter(authored.canvas.controls.values()))
            assert control.options["items"] == (("B", "Beta"),)
            checks.append(
                "dynamic field menus reject vanished choices; custom Layout.prop uses current callback items"
            )
        finally:
            del bpy.types.Scene.beyond_dynamic
            bpy.utils.unregister_class(BEYONDUI_PG_dynamic)
    result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
    print("BEYOND_UI_RESULT=" + json.dumps(result))


def timer():
    try:
        run()
    except Exception:
        traceback.print_exc()
    finally:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(timer, first_interval=1)
