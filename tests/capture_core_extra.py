"""Additional current-source core review states using the production GPU fixture."""

from types import SimpleNamespace as NS
from beyond_ui.context_menu import Entry, default_entries


def capture(canvas, context, clip, clock, render, hold, component, enum_component):
    canvas.cancel()
    canvas.animation.enabled = True
    visited = []
    canvas.context_provider = lambda target, ctx: (
        *default_entries(target, ctx),
        Entry("INSPECT", "Inspect exact control", lambda t, c: visited.append(t.key)),
    )

    def reveal(motion):
        motion.clock = lambda: clock[0]
        motion.clear()
        motion.pulse("reveal", 0.12)

    for frame in range(100):
        clock[0] = 3 + frame / 30
        if frame == 0:
            assert canvas.open_context(hold, *hold.rect[:2], clip, context=context)
            reveal(canvas.context_menu.motion)
        if frame == 23:
            canvas.cancel()
            assert canvas.open_panel(component, clip, context)
            reveal(canvas.overlay["widget"].motion)
        if frame == 45:
            widget = canvas.overlay["widget"]
            field = next(c for c in widget.canvas.controls.values() if c.binding)
            assert widget.canvas.open_context(
                field, *field.rect[:2], widget.clip, context=context
            )
            reveal(widget.canvas.context_menu.motion)
        if frame == 64:
            canvas.cancel()
            assert canvas.open_panel(enum_component, clip, context)
            reveal(canvas.overlay["widget"].motion)
        if frame == 83:
            widget = canvas.overlay["widget"]
            widget.canvas.editor.insert("jpeg")
            widget.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        if frame == 96:
            canvas.cancel()
        render(f"core-{frame:03}")
        canvas.advance_animations()
    theme = context.preferences.themes[0].user_interface
    for name, fill, accent, ink in (
        ("light", (0.8, 0.82, 0.85, 1), (0.12, 0.34, 0.72, 1), (0.06, 0.07, 0.09)),
        ("purple", (0.15, 0.11, 0.19, 1), (0.66, 0.24, 0.78, 1), (0.94, 0.89, 0.98)),
    ):
        ui = NS(wcol_state=theme.wcol_state)
        for role in (
            "wcol_regular",
            "wcol_radio",
            "wcol_tool",
            "wcol_num",
            "wcol_tab",
            "wcol_numslider",
            "wcol_toggle",
        ):
            setattr(
                ui,
                role,
                NS(
                    inner=fill,
                    inner_sel=accent,
                    text=ink,
                    text_sel=(1, 1, 1),
                    item=accent,
                ),
            )
        preferences = NS(themes=[NS(user_interface=ui)])
        render("theme-" + name, preferences=preferences)
        assert canvas.open_context(hold, *hold.rect[:2], clip, context=context)
        canvas.context_menu.motion.clear()
        render("theme-" + name + "-menu", preferences=preferences)
        canvas.cancel()
    # A five-item RNA enum isolates the approved reference's exact content.
    # These are real PropertyPopover controls, not an illustration renderer.
    import bpy
    from beyond_ui import Layout
    from beyond_ui.property_popover import PropertyPopover

    class BUI_ReferenceFormats(bpy.types.PropertyGroup):
        format: bpy.props.EnumProperty(
            items=[
                ("AVIF", "AVIF (.avif)", ""),
                ("JPEG", "JPEG (.jpg)", ""),
                ("EXR", "OpenEXR (.exr)", ""),
                ("PNG", "PNG (.png)", ""),
                ("WEBP", "WebP (.webp)", ""),
            ],
            default="PNG",
        )

    bpy.utils.register_class(BUI_ReferenceFormats)
    bpy.types.Scene.bui_reference_formats = bpy.props.PointerProperty(
        type=BUI_ReferenceFormats
    )
    original = enum_component.options["panel_model"]
    threshold = canvas.menu_search_threshold
    try:
        canvas.menu_search_threshold = 5
        model = PropertyPopover(
            Layout(canvas, context),
            context.scene.bui_reference_formats,
            "format",
            "Format",
        )
        model.control = enum_component
        enum_component.options["panel_model"] = model
        assert canvas.open_panel(enum_component, clip, context), canvas.menu_error
        widget = canvas.overlay["widget"]
        widget.motion.clear()
        for control in widget.canvas.controls.values():
            if control.options.get("search_bar"):
                control.options["placeholder"] = "Search formats…"
        # Reference depicts the resting search, without a caret.
        widget.canvas.cancel()
        render("reference-menu", crop_overlay=True)
        render("reference-in-context")
    finally:
        canvas.cancel()
        canvas.menu_search_threshold = threshold
        enum_component.options["panel_model"] = original
        del bpy.types.Scene.bui_reference_formats
        bpy.utils.unregister_class(BUI_ReferenceFormats)
    from beyond_ui.widgets import DataPicker

    picker = DataPicker(
        [
            (i, label, "object")
            for i, label in enumerate(
                ("Camera", "Cube", "Light", "Target", "Second Target")
            )
        ],
        lambda key: None,
        selected=lambda: 1,
    )
    canvas.open_widget(picker, enum_component, clip)
    assert canvas.overlay["widget"] is picker
    picker.motion.clear()
    render("normalized-picker")
    canvas.cancel()
    from beyond_ui.widgets import ColorPicker, CurveMapping, ColorRamp
    from beyond_ui.bindings import Binding

    for name, factory, initial in (
        ("external-color-fields", ColorPicker, (0.3, 0.5, 0.7, 1.0)),
        ("external-curve-fields", CurveMapping, ((0.0, 0.0), (0.5, 0.5), (1.0, 1.0))),
        (
            "external-ramp-fields",
            ColorRamp,
            ((0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (1.0, 1.0, 1.0, 1.0))),
        ),
    ):
        state = [initial]
        widget = factory(
            Binding(lambda: state[0], lambda value: state.__setitem__(0, value))
        )
        canvas.open_widget(widget, enum_component, clip)
        widget.motion.clear()
        render(name, crop_overlay=True)
        canvas.cancel()
    return dict(
        frames=100,
        sequence=[
            "Host-contributed operator menu",
            "Component popup",
            "Exact component context menu",
            "Enum search popup",
            "Search filtering",
            "Dismissal",
        ],
        generated_reference_acceptance=False,
    )
