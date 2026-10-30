"""Host-owned registered UILists for disposable custom-callback tests."""

import bpy
from beyond_ui import Layout
import lists_fixture as data

draws = filter_draws = filters = 0


class BUI_UL_registered(bpy.types.UIList):
    only_enabled: bpy.props.BoolProperty(name="Enabled Only", default=False)

    def draw_item(
        self,
        context,
        layout,
        owner,
        item,
        icon,
        active_data,
        active_property,
        index=0,
        flt_flag=0,
    ):
        global draws
        draws += 1
        assert self.list_id == "registered"
        if getattr(active_data, active_property) == index:
            layout.prop(item, "name", text="Name")
            layout.prop(item, "enabled", text="Enabled")
            layout.prop(item, "mode", text="Mode")
        else:
            layout.label(text=item.name)

    def draw_filter(self, context, layout):
        global filter_draws
        filter_draws += 1
        layout.prop(self, "filter_name", text="Search")
        row = layout.row()
        row.prop(self, "only_enabled")
        row.prop(self, "use_filter_sort_alpha", text="Alphabetical")
        row = layout.row()
        row.prop(self, "use_filter_invert", text="Invert")
        row.prop(self, "use_filter_sort_reverse", text="Reverse")

    def filter_items(self, context, owner, prop):
        global filters
        filters += 1
        rows = getattr(owner, prop)
        result = bpy.types.UI_UL_list.filter_items_by_name(
            self.filter_name, self.bitflag_filter_item, rows
        )
        result = result or [self.bitflag_filter_item] * len(rows)
        for i, item in enumerate(rows):
            if self.only_enabled and not item.enabled:
                result[i] = 0
            if bpy.app.version >= (4, 5, 0) and self.use_filter_invert:
                result[i] ^= self.bitflag_filter_item
        order = (
            bpy.types.UI_UL_list.sort_items_by_name(rows)
            if self.use_filter_sort_alpha
            else []
        )
        return result, order


class BUI_UL_bad(BUI_UL_registered):
    def draw_item(
        self,
        context,
        layout,
        owner,
        item,
        icon,
        active_data,
        active_property,
        index=0,
        flt_flag=0,
    ):
        layout.label(text="Must not leak")
        layout.template_curveprofile(None, "")


class BUI_UL_invalid_filter(BUI_UL_registered):
    def filter_items(self, context, owner, prop):
        return [1], [0]


classes = (BUI_UL_registered, BUI_UL_bad, BUI_UL_invalid_filter)


def register(count=120):
    data.register(count)
    data.BUI_ListItem.mode = bpy.props.EnumProperty(
        items=[("A", "Alpha", ""), ("B", "Beta", ""), ("C", "Gamma", "")]
    )
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    data.unregister()


def build(context):
    commits = []
    ui = Layout(
        context=context,
        list_identity=lambda owner, prop, item: item.uid,
        commit=lambda a, b: commits.append((a, b)),
    )
    ui.title(text="Registered Collection Lists")
    ui.prop(context.scene.render, "film_transparent", text="Transparent")
    ui.template_list(
        "BUI_UL_registered",
        "registered",
        context.scene,
        "bui_list_items",
        context.scene,
        "bui_list_active",
        rows=5,
        maxrows=10,
    )
    return ui, commits
