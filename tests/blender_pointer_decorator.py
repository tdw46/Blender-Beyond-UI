"""Disposable public-RNA pointer policies, selection transactions and decorators."""

import bpy, json, os, sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, Layout, PointerItems, UnsupportedControl
from beyond_ui.widgets.context import target
from beyond_ui.decorator import channel_collections


class TestPointers(bpy.types.PropertyGroup):
    target: bpy.props.PointerProperty(
        type=bpy.types.Object, poll=lambda owner, item: item.type == "MESH"
    )


def ev(kind, **kw):
    return NS(type=kind, value="PRESS", **kw)


def run():
    ctx = bpy.context
    scene = ctx.scene
    obj = ctx.object
    bpy.utils.register_class(TestPointers)
    bpy.types.Scene.beyond_pointers = bpy.props.PointerProperty(type=TestPointers)
    checks = []
    try:
        commits = []
        canvas = Canvas(menu_commit=commits.append)
        ui = Layout(canvas, ctx, commit=lambda a, b: commits.append((a, b)))
        camera = ui.prop(scene, "camera", text="Camera")
        custom = ui.prop(scene.beyond_pointers, "target", text="Target")
        parent = ui.prop(obj, "parent", text="Parent")
        canvas.arrange(560)
        clip = (0, 0, 560, 700)

        def open_field(c):
            a, b, w, h = c.rect
            canvas.event(ev("LEFTMOUSE"), a + 20, b + 10, clip, context=ctx)
            assert canvas.overlay is not None, canvas.menu_error
            return canvas.overlay["widget"]

        widget = open_field(camera)
        assert all(
            v[0] == 0 or bpy.data.objects[v[1]].type == "CAMERA" for v in widget.items
        )
        old = scene.camera
        widget.select(0)
        assert scene.camera is None and canvas.overlay is None
        widget = open_field(camera)
        old.name = "Renamed Camera"
        widget.select(old.as_pointer())
        assert scene.camera == old and len(commits) == 2
        widget = open_field(custom)
        assert all(
            v[0] == 0 or bpy.data.objects[v[1]].type == "MESH" for v in widget.items
        )
        widget.select(obj.as_pointer())
        assert scene.beyond_pointers.target == obj
        checks.append(
            "Scene camera and registered Python PointerProperty polls filter candidates; clear, rename-safe assignment and one host commit"
        )
        widget = open_field(custom)
        assert canvas.open_context(custom, 20, 20, clip, context=ctx)
        assert (
            canvas.context_menu.target.binding.context.owner() == scene.beyond_pointers
        )
        canvas.close_context()
        # Candidate row context owns that row, not the currently selected pointer.
        key = next(k for k, label, icon in widget.items if k)
        hit = target(widget, custom.key, 40, 150)
        assert hit.part[0] == "row" and hit.binding is None and callable(hit.payload)
        canvas.cancel()

        def reject(a, b):
            raise RuntimeError("Host rejected pointer")

        custom.binding.commit = reject
        widget = open_field(custom)
        widget.select(0)
        assert (
            scene.beyond_pointers.target == obj
            and canvas.menu_error == "Host rejected pointer"
        )
        canvas.cancel()
        custom.binding.commit = lambda a, b: None
        widget = open_field(custom)
        scene.beyond_pointers.target = None
        widget.select(obj.as_pointer())
        assert scene.beyond_pointers.target is None
        canvas.cancel()
        temporary = bpy.data.objects.new(
            "Delete candidate", bpy.data.meshes.new("Fixture mesh")
        )
        widget = open_field(custom)
        key = temporary.as_pointer()
        bpy.data.objects.remove(temporary)
        assert not widget.valid(key)
        canvas.cancel()
        child = bpy.data.objects.new("Descendant", None)
        child.parent = obj
        widget = open_field(parent)
        assert obj.as_pointer() not in [
            i[0] for i in widget.items
        ] and child.as_pointer() not in [i[0] for i in widget.items]
        canvas.cancel()
        checks.append(
            "Exact property/row context ownership, failed commit rollback, stale value/deleted candidate rejection and parent-cycle exclusion"
        )
        try:
            ui.prop(obj, "data")
        except UnsupportedControl:
            pass
        else:
            raise AssertionError("Unknown native pointer poll silently admitted")
        explicit = Layout(
            context=ctx,
            pointer_sources=lambda o, p: PointerItems(
                lambda: bpy.data.meshes, lambda o, c: True
            ),
        )
        assert explicit.prop(obj, "data").kind == "pointer"
        # Object.data has generic ID metadata: explicit policy must support this target.
        checks.append(
            "Unexposed native polls fail closed; consumers can provide explicit candidate/poll policy"
        )
        allowed = [True]
        candidates = [old]
        guarded = Layout(
            Canvas(),
            ctx,
            pointer_sources=lambda o, p: PointerItems(
                lambda: candidates, lambda o, c: allowed[0]
            ),
        )
        guarded_control = guarded.prop(obj, "parent")
        field = guarded_control.options["pointer_field"]
        popup = field.picker(guarded.canvas, guarded_control)
        allowed[0] = False
        popup.select(old.as_pointer())
        assert obj.parent is None and "eligible" in guarded.canvas.menu_error
        allowed[0] = True
        popup = field.picker(guarded.canvas, guarded_control)
        candidates.clear()
        popup.select(old.as_pointer())
        assert obj.parent is None and "eligible" in guarded.canvas.menu_error
        readonly_ui = Layout(
            context=ctx,
            pointer_sources=lambda o, p: PointerItems(lambda: bpy.data.libraries),
        )
        readonly = readonly_ui.prop(obj, "library")
        assert (
            not readonly.enabled and readonly.options["pointer_field"].label() == "None"
        )
        readonly_ui.canvas.arrange(560)
        assert readonly_ui.canvas.open_context(readonly, 10, 10, clip, context=ctx)
        assert readonly_ui.canvas.context_menu.target.valid()
        assert not readonly_ui.canvas.context_menu.target.editable()
        readonly_ui.canvas.close_context()
        checks.append(
            "Commit-time poll/membership changes rejected; read-only ID pointers remain visible, disabled and inspectable by context menu"
        )
        obj.animation_data_clear()
        deco = ui.prop_decorator(obj, "location", index=1)
        canvas.arrange(560)
        model = deco.options["decorator"]
        assert model.state() == "EMPTY"

        def click():
            a, b, w, h = deco.rect
            canvas.event(ev("LEFTMOUSE"), a + 5, b + 5, clip, context=ctx)

        click()
        assert model.state() == "KEYED", (model.state(), canvas.menu_error)
        collections, _ = channel_collections(obj)
        assert [(f.data_path, f.array_index) for c in collections for f in c] == [
            ("location", 1)
        ]
        obj.location[1] += 1
        assert model.state() == "CHANGED"
        click()
        assert model.state() == "EMPTY", (model.state(), canvas.menu_error)
        click()
        scene.frame_set(scene.frame_current + 1)
        assert model.state() == "ANIMATED"
        obj.driver_add("location", 1)
        assert model.state() == "DRIVEN"
        click()
        assert canvas.context_menu is not None
        assert canvas.context_menu.target.binding.context.index == 1
        canvas.close_context()
        obj.driver_remove("location", 1)
        canvas.invalidate()
        assert model.state() == "ANIMATED"
        obj.animation_data_clear()
        assert model.state() == "EMPTY"
        checks.append(
            "Decorator empty/keyed/changed/animated/driven states; exact component insert/delete; driver context and action replacement"
        )
        split = Layout(Canvas(menu_commit=lambda action: None), ctx)
        split.use_property_split = True
        value = split.prop(obj, "location", index=0)
        split.canvas.arrange(560)
        d = next(c for c in split.canvas.controls.values() if c.kind == "decorator")
        assert d.rect[2] == 32 and value.rect[2] > 450
        assert value.motion.strength == 0.15
        split.use_property_decorate = False
        count = len(split.canvas.controls)
        split.prop(obj, "location", index=2)
        assert len(split.canvas.controls) == count + 1
        disabled = Layout(context=ctx).prop_decorator(obj, "location", index=0)
        assert not disabled.enabled
        blank = ui.prop_decorator(scene, "camera")
        assert blank.options["decorator"] is None and not blank.enabled
        checks.append(
            "Automatic split-layout decoration, fixed compact width, preserved wide-field 15% motion, opt-out and disabled/no-undo placeholders"
        )
        state = ctx.preferences.themes[0].user_interface.wcol_state
        from beyond_ui.gpu.style import animation_palette

        assert animation_palette(ctx.preferences)["KEYED"][:3] == tuple(state.inner_key)
        checks.append(
            "Animation-state colors come directly from active theme widget-state roles"
        )
    finally:
        del bpy.types.Scene.beyond_pointers
        bpy.utils.unregister_class(TestPointers)
    result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("POINTER_DECORATOR", result)


run()
