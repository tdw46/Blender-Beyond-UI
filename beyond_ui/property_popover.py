"""Expanded property popups using the shared retained Canvas popup host."""

from types import SimpleNamespace
from .menu_metrics import Metrics as menu_metrics
from .operator_enum import context_key
from .popover import PanelPopover, guard_controls
from .context_menu import Entry, default_entries
from .bindings import Binding
from .menu_search import Search


class PropertyPopover:
    direction = "VERTICAL"
    cls = SimpleNamespace(bl_ui_units_x=16)

    def __init__(self, layout, data, name, label):
        self.layout, self.context = layout, layout.context
        self.binding = layout._binding(data, name)
        self.name, self.label = name, label
        meta = data.bl_rna.properties[name]
        if meta.type == "COLLECTION":
            raise ValueError("Component popups require a drawable RNA property")
        self.schema = (meta.type, getattr(meta, "array_length", 0))

    def menu_theme(self, parent):
        # Enum choices use compact menu rhythm; editable component forms use
        # ordinary host field heights and spacing, like the approved form sheet.
        return menu_metrics.theme(parent) if self.schema[0] == "ENUM" else parent

    def check(self, context, scope=None, *, poll=True):
        if not self.binding.valid():
            raise ReferenceError("Component property owner changed")
        meta = self.binding.context.owner().bl_rna.properties[self.name]
        if (meta.type, getattr(meta, "array_length", 0)) != self.schema:
            raise ReferenceError("Component property shape changed")
        if scope is not None and context_key(context) != scope:
            raise ReferenceError("Component popup context changed")

    def available(self, context, scope=None, *, poll=True):
        try:
            self.check(context, scope)
            return True
        except (ReferenceError, RuntimeError, ValueError, AttributeError, KeyError):
            return False

    def refresh_poll(self, context):
        # No operator poll or RNA collection scan is needed for this opener.
        pass

    def context_rows(self, target, context):
        provider = self.layout.canvas.context_provider
        return (
            Entry(
                "OPEN_COMPONENTS",
                "Edit " + self.label,
                lambda t, c: self.layout.canvas.open_panel(
                    self.control, self.layout.canvas._event_clip, c
                ),
                enabled=lambda t, c: self.available(c),
            ),
            *default_entries(target, context),
            *(provider(target, context) if provider else ()),
        )

    def build(self, parent, owner, context):
        from .canvas import Canvas
        from .layout import Layout

        scope = context_key(context)
        self.check(context, scope)
        depth = getattr(parent, "_popover_depth", 0)
        if depth >= 3:
            raise ValueError("Popover nesting exceeds three levels")
        child = Canvas(
            self.menu_theme(parent.theme),
            icon_renderer=parent.icon_renderer,
            context_provider=parent.context_provider,
            menu_commit=parent.menu_commit,
            shortcut_registry=parent.shortcut_registry,
            shortcut_namespace=f"{parent.shortcut_namespace}:components:{id(self)}",
            menu_search_threshold=parent.menu_search_threshold,
        )
        child._popover_depth = depth + 1
        child._scoped_shortcuts = {}
        child.wide_numeric_motion_scale = parent.wide_numeric_motion_scale
        child.bind_animation(
            (*parent._animation_parents, parent.animation, owner.motion.settings),
            lambda: parent._animation_wake() if parent._animation_wake else None,
        )
        child.bind_context_tooltips(parent._tooltip_wake)
        child.set_text_measure(parent.text_measure, parent._text_measure_key)
        ui = Layout(
            child,
            context,
            resolve=self.layout.resolve,
            commit=self.layout.commit,
            state=self.layout.state,
            source=self.layout.source,
            pointer_sources=self.layout.pointer_sources,
            id_actions=self.layout.id_actions,
            list_identity=self.layout.list_identity,
        )
        ui._is_popover = True
        try:
            title = ui.title(text=self.label, translate=False)
            title.options.update(
                height=menu_metrics.TITLE_HEIGHT, text_inset=menu_metrics.TITLE_INSET
            )
            ui.group.label(
                ui._key("title-gap"),
                "",
                height=menu_metrics.TITLE_GAP if self.schema[0] == "ENUM" else 3.5,
            )
            data = self.binding.context.owner()
            meta = data.bl_rna.properties[self.name]
            if meta.type == "ENUM":
                field = ui._enum_field(ui._binding(data, self.name))
                items = field.snapshot()
                search = None
                if (
                    sum(bool(i.identifier) for i in items)
                    >= parent.menu_search_threshold
                ):
                    search = Search(())
                    query = Binding(
                        lambda: search.text.text, lambda value: filter_rows(value)
                    )
                    ui.group.text(
                        ui._key("component-search"),
                        "",
                        query,
                        search_bar=True,
                        placeholder="Search options…",
                        activate_init=True,
                        height=menu_metrics.SEARCH_HEIGHT,
                        context_menu=lambda t, c: (
                            Entry(
                                "CLEAR_SEARCH",
                                "Clear Search",
                                lambda t, c: query.write(""),
                                enabled=bool(query.read()),
                            ),
                        ),
                    )
                    ui.group.label(
                        ui._key("search-gap"), "", height=menu_metrics.HEADER_GAP
                    )
                start = len(child.children)
                for item in items:
                    if item.identifier:
                        ui._enum_button(
                            data, self.name, item, translate=False, modifier_select=True
                        )
                    elif item.name:
                        ui.title(text=item.name, translate=False)
                    else:
                        ui.separator()
                if search is not None:
                    rows = tuple(child.children[start:])
                    # Reuse shared token/group matching and retained controls.
                    search = Search(
                        tuple(
                            Entry(
                                c.key,
                                c.label,
                                heading=c.options.get("text_role") == "title",
                            )
                            for c in rows
                        )
                    )
                    prefix = tuple(child.children[:start])
                    empty = ui.group.label(
                        ui._key("empty-components"),
                        "No matching components",
                        enabled=False,
                    )
                    child.children.remove(empty)

                    def filter_rows(value):
                        search.text.text = str(value)
                        keys = {entry.key for entry in search.filtered()}
                        matches = [c for c in rows if c.key in keys]
                        child.children[:] = [*prefix, *(matches or [empty])]
                        child.controls = {c.key: c for c in child.children}
                        child.invalidate()
                        child.arrange(popup.width)
                        popup.scroll = 0
                        overlay = parent.overlay
                        if overlay and overlay.get("widget") is popup:
                            clip = overlay["clip"]
                            width, height = popup.dimensions(
                                child.theme.font_size, clip[2], clip[3]
                            )
                            x, y, _, _ = overlay["rect"]
                            overlay["rect"] = (
                                x,
                                max(clip[1], min(y, clip[1] + clip[3] - height)),
                                width,
                                height,
                            )
            elif getattr(meta, "is_array", False) and meta.subtype not in {
                "COLOR",
                "COLOR_GAMMA",
            }:
                for i in range(meta.array_length):
                    ui.prop(
                        data,
                        self.name,
                        index=i,
                        text=f"{meta.name} {i + 1}",
                        translate=False,
                        icon=owner.options.get("icon", "NONE"),
                    )
            else:
                ui.prop(data, self.name, expand=True)
            if len(child.controls) > 4096:
                raise ValueError("Component popup exceeds 4096 controls")
            guard_controls(
                self,
                child,
                tuple(child.controls.values()),
                context,
                scope,
                owner_valid=lambda: child.visible
                and parent.controls.get(owner.key) is owner
                and owner.enabled
                and getattr((parent.overlay or {}).get("widget"), "canvas", None)
                is child,
            )
            child.controls = {c.key: c for c in child.children}
            popup = PanelPopover(self, parent, owner, child, scope)
            if meta.type == "ENUM":
                popup.preferred_width = menu_metrics.WIDTH
            return popup
        except Exception:
            child.park()
            raise
