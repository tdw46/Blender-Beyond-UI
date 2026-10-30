"""Disposable production-control layouts shared by execution and capture fixtures."""

from beyond_ui import Canvas, Layout


def build(context):
    canvas = Canvas()
    ui = Layout(canvas, context=context)
    ui.title(text="Responsive Layouts")
    split = ui.split(factor=0.4)
    split.column().prop(
        context.scene.render, "resolution_percentage", text="Scale", slider=True
    )
    split.column().prop(context.scene.render, "filter_size", text="Filter", slider=True)
    ui.title(text="Grid Flow")
    grid = ui.grid_flow(columns=3, row_major=True, even_columns=True)
    toggles = []
    for name, label in (
        ("film_transparent", "Transparent"),
        ("use_file_extension", "Extensions"),
        ("use_overwrite", "Overwrite"),
        ("use_placeholder", "Placeholders"),
        ("use_border", "Render Region"),
        ("use_crop_to_border", "Crop Region"),
    ):
        grid.prop(context.scene.render, name, text=label)
        toggles.append(list(canvas.controls.values())[-1])
    ui.title(text="Balanced Columns")
    flow = ui.column_flow(columns=2)
    calls = []
    for i in range(4):
        flow.group.button(f"action:{i}", f"Action {i + 1}", lambda i=i: calls.append(i))
    disabled = ui.row()
    disabled.prop(context.scene.render, "use_stamp", text="Disabled Parent")
    disabled.active = False
    footer = ui.row()
    footer.label(text="Retained BVT controls")
    footer.separator_spacer()
    footer.label(text="Ready")
    return ui, toggles, disabled, calls
