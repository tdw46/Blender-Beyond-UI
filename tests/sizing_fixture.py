"""Existing BVT controls composed with explicit custom layout sizing."""

from beyond_ui import Layout


def build(context):
    commits = []
    ui = Layout(context=context, commit=lambda a, b: commits.append((a, b)))
    ui.title(text="Relative Widths")
    row = ui.row()
    left, right = row.column(), row.column()
    right.scale_x = 2
    left.prop(context.scene.render, "resolution_percentage", text="Scale", slider=True)
    right.prop(context.scene.render, "filter_size", text="Filter", slider=True)
    ui.title(text="Taller Rows · Same Typography")
    tall = ui.row()
    tall.scale_y = 1.5
    tall.prop(context.scene.render, "film_transparent", text="Transparent")
    tall.prop(context.scene.render, "use_file_extension", text="Extensions")
    toggles = [c for c in ui.canvas.controls.values() if c.kind == "toggle"]
    ui.title(text="Fixed Width and Height")
    fixed_row = ui.row()
    fixed = fixed_row.column()
    fixed.ui_units_x, fixed.ui_units_y = 8, 2.5
    fixed.prop(context.scene.render.image_settings, "file_format", text="Format")
    fixed.prop(context.scene.render, "filepath", text="Output")
    flex = fixed_row.column()
    flex.label(text="Remaining width")
    flex.label(text="Host logical units")
    ui.title(text="Proportional Compound Control")
    compact = ui.column()
    compact.ui_units_y = 8
    compact.template_color_picker(context.scene.world, "color")
    return (
        ui,
        toggles,
        dict(tall=tall, fixed=fixed, right=right, compact=compact),
        commits,
    )
