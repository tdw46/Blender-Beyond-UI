"""Copy the style dictionaries and draw body into an add-on using vendored Beyond UI."""
from ._vendor import beyond_ui as bui

FIELD = dict(padding=(3, 8), margin=(2, 0), radius=6)
FOCAL = dict(units="mm", precision=1, value_width=78)
SECTION = dict(gap=8, padding=6)


def draw_camera(layout, camera):
    column = layout.column()
    bui.style(column, SECTION, scope="group")
    column.prop(camera, "lens", text="Focal Length")
    bui.style(column, FIELD, FOCAL)
    column.prop(camera, "type", text="Projection")
    bui.style(column, FIELD)
    # Alternative one-call form; style keywords never reach native prop().
    bui.prop(column, camera, "clip_start", style=dict(units="cm", precision=2))
