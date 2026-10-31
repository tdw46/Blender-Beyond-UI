"""Contributed commands use custom RNA actions, never an active native button."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_extensions import collect
from beyond_ui.context_menu import Menu, Target


def run():
    ctx = bpy.context
    owner = ctx.active_object
    other = bpy.data.objects.new("Context receiver", None)
    ctx.collection.objects.link(other)
    other.select_set(True)
    commits, calls = [], []
    binding = rna_binding(
        lambda: owner, "location", index=1, commit=lambda a, b: commits.append((a, b))
    )
    source = binding.context
    target = Target("Y", binding=binding, valid=source.valid)

    class BUI_OT_custom_button(bpy.types.Operator):
        bl_idname = "bui.custom_button"
        bl_label = "Custom button"
        amount: bpy.props.IntProperty()

        @classmethod
        def poll(cls, context):
            return context.button_pointer == owner

        def execute(self, context):
            calls.append((context.button_pointer.as_pointer(), self.amount))
            return {"FINISHED"}

    bpy.utils.register_class(BUI_OT_custom_button)

    class ClipboardContext:
        window_manager = SimpleNamespace(clipboard="")

        def __getattr__(self, name):
            return getattr(ctx, name)

    isolated = ClipboardContext()

    def rows(command, **props):
        def contribution(holder, context):
            holder.layout.operator_context = "EXEC_DEFAULT"
            settings = holder.layout.operator(command)
            for key, value in props.items():
                setattr(settings, key, value)

        return collect(ctx, source, (contribution,))

    def menu(entries, target=target):
        return Menu(target, entries, (0, 0), (0, 0, 600, 700), context=isolated)

    def execute(command, **props):
        m = menu(rows(command, **props))
        assert m.page.available == (True,), (command, m.error)
        m.choose(0, isolated)
        assert m.closed and m.error is None, m.error

    try:
        owner.location = (3, 4, 5)
        execute("ui.reset_default_button", all=False)
        assert tuple(owner.location) == (3, 0, 5)
        execute("ui.reset_default_button")
        assert tuple(owner.location) == (0, 0, 0)
        owner.location = (3, 4, 5)
        other.location = (8, 9, 10)
        execute("ui.copy_to_selected_button", all=False)
        assert tuple(other.location) == (8, 4, 10)
        execute("ui.copy_to_selected_button", all=True)
        assert tuple(other.location) == (3, 4, 5)
        execute("ui.copy_data_path_button")
        assert isolated.window_manager.clipboard == "location[1]"
        execute("ui.copy_data_path_button", full_path=True)
        assert isolated.window_manager.clipboard == source.paths()[1]
        owner.driver_add("location", 1).driver.expression = "4"
        owner.driver_add("location", 2).driver.expression = "5"
        driver_target = Target(
            "driver", binding=binding, valid=source.valid, commit=commits.append
        )
        m = menu(rows("ui.copy_driver_to_selected_button", all=False), driver_target)
        assert m.page.available == (True,), m.error
        m.choose(0, isolated)
        assert m.closed and m.error is None, m.error
        assert (
            other.animation_data.drivers.find("location", index=1).driver.expression
            == "4"
        )
        assert other.animation_data.drivers.find("location", index=2) is None
        m = menu(rows("ui.copy_driver_to_selected_button", all=True), driver_target)
        m.choose(0, isolated)
        assert m.closed and m.error is None, m.error
        assert (
            other.animation_data.drivers.find("location", index=2).driver.expression
            == "5"
        )
        assert not menu(
            rows("ui.copy_driver_to_selected_button"), target
        ).page.available[0]
        execute("bui.custom_button", amount=7)
        assert calls == [(owner.as_pointer(), 7)]
        stale = menu(rows("bui.custom_button", amount=9))
        bpy.utils.unregister_class(BUI_OT_custom_button)
        stale.choose(0, isolated)
        assert len(calls) == 1

        for command, props in (
            ("ui.reset_default_button", {"all": "False"}),
            ("ui.reset_default_button", {"unknown": True}),
            ("anim.keyframe_insert_button", {}),
            ("ui.copy_driver_to_selected_button", {"all": "False"}),
        ):
            m = menu(rows(command, **props))
            assert m.page.available == (False,), command
        locked = Target(
            "locked", binding=binding, valid=source.valid, editable=lambda: False
        )
        assert not menu(rows("ui.reset_default_button"), locked).page.available[0]
        assert menu(rows("ui.copy_data_path_button"), locked).page.available[0]

        def disabled(holder, context):
            child = holder.layout.row()
            child.enabled = False
            child.operator("ui.reset_default_button")

        assert not menu(collect(ctx, source, (disabled,))).page.available[0]

        def reject(a, b):
            raise RuntimeError("host rejected")

        source.commit = reject
        before = tuple(owner.location)
        m = menu(rows("ui.reset_default_button", all=False))
        m.choose(0, isolated)
        assert m.error == "host rejected" and tuple(owner.location) == before
        source.commit = lambda a, b: None
        pending = menu(rows("ui.reset_default_button"))
        bpy.data.objects.remove(owner, do_unlink=True)
        pending.choose(0, isolated)
        assert pending.closed
        return dict(
            passed=True,
            version=bpy.app.version_string,
            checks=[
                "Contributed Reset/Copy Selected respect component and all-array arguments",
                "Contributed driver copying honors single/all channels and requires host undo",
                "Data/full paths use exact clicked owner and isolated clipboard",
                "Python operators ending in _button execute and revoke after unregister",
                "Unknown arguments, native-only actions and inherited disabled states fail closed",
                "Locked controls retain readable paths; rejected reset rolls back",
                "Deleted property owners revoke pending contributed actions",
            ],
        )
    finally:
        if BUI_OT_custom_button.is_registered:
            bpy.utils.unregister_class(BUI_OT_custom_button)
        bpy.data.objects.remove(other, do_unlink=True)


try:
    result = run()
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
