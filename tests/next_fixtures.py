"""Deterministic reference states. Colors are authored data, not sampled textures."""

from beyond_ui.bindings import Binding
from beyond_ui.widgets import Palette, PaletteSource, MatrixView, Progress
from beyond_ui.gpu.skin import rgba

COLORS = (
    "F26662",
    "F2A158",
    "F5D15F",
    "5AC791",
    "13C1F3",
    "2B8EF8",
    "CD68C4",
    "DF81AD",
    "C8A17D",
    "88CCB4",
    "89DCEE",
    "8CB0EF",
    "4F5760",
    "717982",
    "98A0AB",
    "B8BFC8",
    "D8DEE7",
    "F0F2F4",
)


def widgets():
    values = [rgba(c) for c in COLORS]
    active = [4]

    def add():
        values.append(values[active[0]])
        active[0] = len(values) - 1

    def remove():
        if values:
            values.pop(active[0])
            active[0] = min(active[0], len(values) - 1)

    palette = Palette(
        PaletteSource(
            lambda: len(values),
            lambda i: values[i],
            lambda: active[0],
            lambda i: active.__setitem__(0, i),
            add=add,
            remove=remove,
        ),
        linear=False,
    )
    matrix = MatrixView(
        Binding(
            lambda: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), lambda v: None
        )
    )
    return [
        ("palette", "Palette", palette),
        ("matrix", "Matrix", matrix),
        (
            "progress-bar",
            "Progress Bar",
            Progress(0.65, text="Preparing assets", detail="Step 13 of 20"),
        ),
        (
            "progress-ring",
            "Progress Ring",
            Progress(0.65, type="RING", text="Preparing assets"),
        ),
    ]
