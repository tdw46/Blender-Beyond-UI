"""Copied into a disposable add-on; its native authoring remains unchanged."""

import bpy

calls = []


class ROUTE_OT_dialog(bpy.types.Operator):
    bl_idname = "route.dialog"
    bl_label = "Apply Output Changes"
    bl_options = {"REGISTER", "UNDO"}
    value: bpy.props.IntProperty(name="Value", default=3)
    enabled: bpy.props.BoolProperty(name="Enabled", default=False)

    def invoke(self, context, event):
        self.value = 7
        self.transient = "kept"
        return context.window_manager.invoke_props_dialog(
            self, width=340, confirm_text="Apply"
        )

    def draw(self, context):
        self.layout.prop(self, "value")
        self.layout.prop(self, "enabled")
        if self.enabled:
            self.layout.label(text="Extra options")

    def check(self, context):
        return True

    def execute(self, context):
        assert self.transient == "kept"
        context.scene.render.resolution_percentage = self.value
        calls.append(("execute", self.value, self.enabled))
        return {"FINISHED"}

    def cancel(self, context):
        calls.append(("cancel", self.value))


class ROUTE_OT_action(bpy.types.Operator):
    bl_idname = "route.action"
    bl_label = "Menu Action"

    def execute(self, context):
        calls.append(("menu",))
        return {"FINISHED"}


class ROUTE_MT_menu(bpy.types.Menu):
    bl_label = "Direct Menu"

    def draw(self, context):
        self.layout.operator("route.action")
        self.layout.prop(context.scene.render, "film_transparent")


class ROUTE_MT_pie(bpy.types.Menu):
    bl_label = "Direct Pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("route.action")
        pie.operator("route.action", text="Second")


class ROUTE_OT_menu(bpy.types.Operator):
    bl_idname = "route.menu"
    bl_label = "Open Menu"

    def execute(self, context):
        return bpy.ops.wm.call_menu(name="ROUTE_MT_menu")


class ROUTE_OT_pie(bpy.types.Operator):
    bl_idname = "route.pie"
    bl_label = "Open Pie"

    def invoke(self, context, event):
        return bpy.ops.wm.call_menu_pie(name="ROUTE_MT_pie")


class ROUTE_OT_popup(bpy.types.Operator):
    bl_idname = "route.popup"
    bl_label = "Callback Menu"

    def execute(self, context):
        def draw(menu, ctx):
            menu.layout.operator("route.action")

        context.window_manager.popup_menu(draw, title="Callback Menu", icon="INFO")
        return {"FINISHED"}


classes = (
    ROUTE_OT_dialog,
    ROUTE_OT_action,
    ROUTE_MT_menu,
    ROUTE_MT_pie,
    ROUTE_OT_menu,
    ROUTE_OT_pie,
    ROUTE_OT_popup,
)


class PopupFields:
    bl_label = "Apply Output Changes"
    bl_options = {"REGISTER", "UNDO"}
    value: bpy.props.IntProperty(name="Value", default=3)
    enabled: bpy.props.BoolProperty(name="Enabled", default=False)
    draw = ROUTE_OT_dialog.draw
    check = ROUTE_OT_dialog.check
    execute = ROUTE_OT_dialog.execute
    cancel = ROUTE_OT_dialog.cancel


class ROUTE_OT_plain(PopupFields, bpy.types.Operator):
    bl_idname = "route.plain"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=340)


class ROUTE_OT_confirm(PopupFields, bpy.types.Operator):
    bl_idname = "route.confirm"

    def invoke(self, context, event):
        self.transient = "kept"
        return context.window_manager.invoke_confirm(
            self, event, title="Confirm Action", message="Keep the original instance.",
            confirm_text="Apply", icon="QUESTION"
        )


class ROUTE_OT_search(bpy.types.Operator):
    bl_idname = "route.search"
    bl_label = "Choose Format"
    bl_options = {"REGISTER", "UNDO"}
    bl_property = "format"
    format: bpy.props.EnumProperty(items=[("PNG", "PNG", ""), ("JPEG", "JPEG", ""), ("EXR", "OpenEXR", "")])

    def invoke(self, context, event):
        self.transient = "kept"
        assert context.window_manager.invoke_search_popup(self) is None
        return {"RUNNING_MODAL"}

    def execute(self, context):
        assert self.transient == "kept"
        calls.append(("search", self.format))
        context.scene.render.image_settings.file_format = self.format
        return {"FINISHED"}

    def cancel(self, context):
        calls.append(("search-cancel",))


class ROUTE_OT_callback_pie(bpy.types.Operator):
    bl_idname = "route.callback_pie"
    bl_label = "Callback Pie"

    def invoke(self, context, event):
        def draw(menu, context):
            pie = menu.layout.menu_pie()
            pie.operator("route.action")
            pie.operator("route.action", text="Second")

        context.window_manager.popup_menu_pie(event, draw, title="Actions", icon="INFO")
        return {"FINISHED"}


classes += (ROUTE_OT_plain, ROUTE_OT_confirm, ROUTE_OT_search, ROUTE_OT_callback_pie)
register_classes, unregister_classes = bpy.utils.register_classes_factory(classes)
keymaps = []


def register():
    register_classes()
    config = bpy.context.window_manager.keyconfigs.addon
    if config:
        km = config.keymaps.new(name="3D View", space_type="VIEW_3D")
        for kind, name, key in (("wm.call_menu", "ROUTE_MT_menu", "F6"), ("wm.call_menu_pie", "ROUTE_MT_pie", "F7"), ("wm.call_menu", "VIEW3D_MT_view", "F8")):
            item = km.keymap_items.new(kind, key, "PRESS", ctrl=True, shift=True)
            item.properties.name = name
            keymaps.append((km, item))


def unregister():
    for km, item in keymaps:
        km.keymap_items.remove(item)
    keymaps.clear()
    unregister_classes()


from ._vendor.beyond_ui import integrate

integrate(globals())
