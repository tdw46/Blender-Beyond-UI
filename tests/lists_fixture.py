"""Disposable list data; host owns registration, collection mutations and undo."""

import bpy
from beyond_ui import Layout


class BUI_ListItem(bpy.types.PropertyGroup):
    uid: bpy.props.StringProperty()
    name: bpy.props.StringProperty(name="Name")
    enabled: bpy.props.BoolProperty(default=True)


def register(count=120):
    bpy.utils.register_class(BUI_ListItem)
    bpy.types.Scene.bui_list_items = bpy.props.CollectionProperty(type=BUI_ListItem)
    bpy.types.Scene.bui_list_active = bpy.props.IntProperty(default=0)
    for i in range(count):
        item = bpy.context.scene.bui_list_items.add()
        item.uid = str(i)
        item.name = f"{'Layer' if i % 3 else 'Effect'} {i:03}"


def unregister():
    del bpy.types.Scene.bui_list_items
    del bpy.types.Scene.bui_list_active
    bpy.utils.unregister_class(BUI_ListItem)


def build(context, *, count_views=3):
    commits = []
    ui = Layout(
        context=context,
        commit=lambda a, b: commits.append((a, b)),
        list_identity=lambda data, prop, item: item.uid,
    )
    ui.title(text="Collection Lists")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    for kind in ("DEFAULT", "COMPACT", "GRID")[:count_views]:
        ui.label(text=kind.title())
        ui.template_list(
            "UI_UL_list",
            "fixture-" + kind,
            context.scene,
            "bui_list_items",
            context.scene,
            "bui_list_active",
            rows=4 if kind == "DEFAULT" else 2,
            maxrows=8,
            type=kind,
            columns=4,
        )
    return ui, commits
