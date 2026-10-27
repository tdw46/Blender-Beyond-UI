"""Run in Blender's Text Editor or --python, after making the repo importable.

For vendoring, change imports to .vendor.beyond_ui and call register/unregister
from your extension lifecycle. Scene data and preferences are never changed.
"""

import bpy
from bpy.app.handlers import persistent
from beyond_ui import Canvas, NativeLayout as Layout
from beyond_ui.bindings import Binding
from beyond_ui.hosts.panel import PanelHost

_host = None
_canvases = {}
_states = {}
_running = set()
_generation = 0


def build_canvas(key):
    state = _states.setdefault(
        key, {"enabled": True, "strength": 0.5, "name": "Beyond UI", "mode": "A"}
    )

    def binding(name):
        return Binding(lambda: state[name], lambda value: state.update({name: value}))

    canvas = Canvas()
    canvas.title("title", "Custom Effect Layers components")
    canvas.toggle("enabled", "Enabled", binding("enabled"))
    canvas.number(
        "strength",
        "Strength",
        binding("strength"),
        min=0,
        max=1,
        hard_min=0,
        hard_max=1,
    )
    canvas.text("name", "Name", binding("name"))
    canvas.enum(
        "mode", "Mode", binding("mode"), items=(("A", "First"), ("B", "Second"))
    )
    row = canvas.row()
    row.button("reset", "Reset", lambda: state.update(strength=0.5))
    row.button("toggle", "Toggle", lambda: state.update(enabled=not state["enabled"]))
    canvas.label("hint", "Drag numbers; double-click for exact entry")
    return canvas


class BEYONDUIDEMO_OT_input(bpy.types.Operator):
    bl_idname = "beyonduidemo.input"
    bl_label = "Enable Custom UI Input"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        key = context.window.as_pointer()
        if key in _running:
            return {"CANCELLED"}
        self.owner = key
        self.generation = _generation
        _running.add(key)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if _host is None or _host.closed or self.generation != _generation:
            _running.discard(self.owner)
            return {"CANCELLED"}
        return {"RUNNING_MODAL"} if _host.event(context, event) else {"PASS_THROUGH"}


class BEYONDUIDEMO_PT_panel(bpy.types.Panel):
    bl_idname = "BEYONDUIDEMO_PT_panel"
    bl_label = "Beyond UI"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Beyond UI"

    def draw(self, context):
        ui = Layout(self.layout)
        ui.label(text="Native API and custom canvas")
        ui.prop(context.scene.render, "resolution_percentage", text="Native control")
        key = _host._key(context)
        if _host.bridge is not None:
            input_row = ui.row()
            input_row.enabled = context.window.as_pointer() not in _running
            input_row.operator("beyonduidemo.input")
            canvas = _canvases.get(key)
            if canvas is None:
                canvas = _canvases[key] = build_canvas(key)
            _host.draw(ui, context, canvas)
        else:
            ui.label(text=_host.reason, icon="INFO")
            ui.prop(context.scene.render, "film_transparent")


@persistent
def invalidate(*args):
    if _host is not None:
        _host.invalidate()
    _canvases.clear()


CLASSES = (BEYONDUIDEMO_OT_input, BEYONDUIDEMO_PT_panel)


def register():
    global _host, _generation
    if _host is not None:
        return
    _generation += 1
    _host = PanelHost(__name__)
    _host.start()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    for handlers in (
        bpy.app.handlers.load_pre,
        bpy.app.handlers.undo_pre,
        bpy.app.handlers.redo_pre,
    ):
        handlers.append(invalidate)


def unregister():
    global _host, _generation
    _generation += 1
    if _host is not None:
        _host.close()
        _host = None
    for handlers in (
        bpy.app.handlers.load_pre,
        bpy.app.handlers.undo_pre,
        bpy.app.handlers.redo_pre,
    ):
        if invalidate in handlers:
            handlers.remove(invalidate)
    for cls in reversed(CLASSES):
        if getattr(cls, "is_registered", False):
            bpy.utils.unregister_class(cls)
    _canvases.clear()
    _states.clear()
    _running.clear()


if __name__ == "__main__":
    register()
